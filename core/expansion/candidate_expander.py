from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project import ProjectManager, STTProject


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


@dataclass
class CandidateExpansionConfig:
    top_candidates: int = 120
    min_ai_score: float = 30.0
    max_segments_per_video: int = 6
    output_prefix: str = "expanded_candidates"


class FullSourceCandidateExpander:
    # Build 012.
    # Reads ALL analyzed shot_segments from SQLite, ranks them,
    # and creates a larger candidate pool instead of only using the old 23-shot roughcut.

    def __init__(
        self,
        project: STTProject,
        config: CandidateExpansionConfig | None = None,
    ) -> None:
        self.project = project
        self.config = config or CandidateExpansionConfig()
        self.db_path = self._get_database_path(project)

    def expand(self) -> dict[str, str]:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        all_csv = output_dir / "all_ranked_segments.csv"
        candidates_json = output_dir / "expanded_candidates.json"
        candidates_csv = output_dir / "expanded_candidates.csv"
        roughcut_plan_json = output_dir / "roughcut_plan.json"
        summary_txt = output_dir / "expanded_candidates_summary.txt"

        print("STT AI Full Source Candidate Expansion")
        print(f"Project: {self.project.name}")
        print(f"Database: {self.db_path}")
        print(f"Top candidates: {self.config.top_candidates}")
        print(f"Min AI score: {self.config.min_ai_score}")
        print(f"Max segments/video: {self.config.max_segments_per_video}")
        print(f"Output: {output_dir}")
        print("-" * 60)

        rows = self._load_all_segments()
        ranked = self._rank_rows(rows)
        selected = self._select_candidates(ranked)
        self._retimeline(selected)

        self._write_csv(all_csv, ranked)
        candidates_json.write_text(
            json.dumps(selected, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        roughcut_plan_json.write_text(
            json.dumps(selected, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._write_csv(candidates_csv, selected)
        self._write_summary(summary_txt, rows, ranked, selected)

        print("EXPANSION COMPLETE")
        print(f"Total DB segments: {len(rows)}")
        print(f"Ranked segments: {len(ranked)}")
        print(f"Selected candidates: {len(selected)}")
        print(f"Roughcut plan: {roughcut_plan_json}")
        print("-" * 60)

        return {
            "output_dir": str(output_dir),
            "all_ranked_csv": str(all_csv),
            "expanded_candidates_json": str(candidates_json),
            "expanded_candidates_csv": str(candidates_csv),
            "roughcut_plan_json": str(roughcut_plan_json),
            "summary": str(summary_txt),
        }

    @staticmethod
    def _get_database_path(project: STTProject) -> Path:
        paths = project.paths

        for attr in ("database_path", "database_file", "db_path"):
            if hasattr(paths, attr):
                value = getattr(paths, attr)
                if value:
                    return Path(value)

        return Path(project.root) / "database" / "stt_ai.db"

    def _load_all_segments(self) -> list[dict[str, Any]]:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            tables = self._get_tables(conn)
            video_table = self._find_table(tables, ["video"])
            segment_table = self._find_table(tables, ["shot", "segment"])

            if not video_table:
                video_table = "video_files"

            if not segment_table:
                segment_table = "shot_segments"

            video_cols = self._get_columns(conn, video_table)
            segment_cols = self._get_columns(conn, segment_table)

            video_pk = self._first_existing(video_cols, ["id", "video_id"])
            segment_video_fk = self._first_existing(segment_cols, ["video_id", "video_file_id"])

            if not video_pk or not segment_video_fk:
                raise RuntimeError(
                    f"Cannot find video join columns. Video table={video_table}, segment table={segment_table}"
                )

            select_parts = []
            for col in segment_cols:
                select_parts.append(f's."{col}" AS "s__{col}"')
            for col in video_cols:
                select_parts.append(f'v."{col}" AS "v__{col}"')

            sql = (
                f"SELECT {', '.join(select_parts)} "
                f'FROM "{segment_table}" s '
                f'JOIN "{video_table}" v ON s."{segment_video_fk}" = v."{video_pk}"'
            )

            raw_rows = [dict(row) for row in conn.execute(sql).fetchall()]

        rows: list[dict[str, Any]] = []

        for raw in raw_rows:
            row = self._normalize_row(raw, segment_cols, video_cols)
            if row:
                rows.append(row)

        return rows

    @staticmethod
    def _get_tables(conn: sqlite3.Connection) -> list[str]:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return [str(r[0]) for r in rows]

    @staticmethod
    def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
        rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        return [str(r[1]) for r in rows]

    @staticmethod
    def _find_table(tables: list[str], keywords: list[str]) -> str | None:
        for table in tables:
            low = table.lower()
            if all(k in low for k in keywords):
                return table

        for table in tables:
            low = table.lower()
            if any(k in low for k in keywords):
                return table

        return None

    @staticmethod
    def _first_existing(cols: list[str], names: list[str]) -> str | None:
        low_map = {c.lower(): c for c in cols}
        for name in names:
            if name.lower() in low_map:
                return low_map[name.lower()]
        return None

    def _normalize_row(
        self,
        raw: dict[str, Any],
        segment_cols: list[str],
        video_cols: list[str],
    ) -> dict[str, Any] | None:
        def s(name_options: list[str], default: Any = None) -> Any:
            return self._get_prefixed(raw, "s__", segment_cols, name_options, default)

        def v(name_options: list[str], default: Any = None) -> Any:
            return self._get_prefixed(raw, "v__", video_cols, name_options, default)

        video_path = v(["file_path", "path", "absolute_path", "source_path", "filepath"])
        if not video_path:
            return None

        video_path = str(video_path)
        video_filename = v(["filename", "file_name", "name"], Path(video_path).name)

        start = self._to_float(s(["start_seconds", "start_time", "start"], 0.0), 0.0)
        end = self._to_float(s(["end_seconds", "end_time", "end"], start), start)
        duration = self._to_float(s(["duration_seconds", "duration"], end - start), end - start)

        if end <= start and duration > 0:
            end = start + duration

        duration = max(0.0, end - start)

        if duration <= 0:
            return None

        sharpness = self._to_float(s(["blur_score", "sharpness_score"], 0.0), 0.0)
        stability = self._to_float(s(["shake_score", "stability_score"], 0.0), 0.0)
        exposure = self._to_float(s(["exposure_score"], 0.0), 0.0)
        motion = self._to_float(s(["motion_score"], 0.0), 0.0)
        beauty = self._to_float(s(["beauty_score"], 0.0), 0.0)
        ai_keep = self._to_float(s(["ai_keep_score", "keep_score"], 0.0), 0.0)

        if ai_keep <= 0:
            ai_keep = self._technical_score(sharpness, stability, exposure, motion, beauty)

        row = {
            "order": 0,
            "video_id": v(["id", "video_id"], ""),
            "segment_id": s(["id", "segment_id"], ""),
            "segment_index": s(["segment_index", "index"], 0),
            "video_path": video_path,
            "video_filename": str(video_filename),
            "source_start_seconds": round(start, 3),
            "source_end_seconds": round(end, 3),
            "duration_seconds": round(duration, 3),
            "timeline_start_seconds": 0.0,
            "timeline_end_seconds": 0.0,
            "sharpness_score": round(sharpness, 2),
            "stability_score": round(stability, 2),
            "exposure_score": round(exposure, 2),
            "motion_score": round(motion, 2),
            "beauty_score": round(beauty, 2),
            "ai_keep_score": round(ai_keep, 2),
            "expansion_source": "full_database",
        }

        row["expansion_score"] = round(
            self._expansion_score(
                ai_keep=ai_keep,
                sharpness=sharpness,
                stability=stability,
                exposure=exposure,
                motion=motion,
                beauty=beauty,
                duration=duration,
            ),
            2,
        )

        return row

    @staticmethod
    def _get_prefixed(
        raw: dict[str, Any],
        prefix: str,
        cols: list[str],
        name_options: list[str],
        default: Any = None,
    ) -> Any:
        low_map = {c.lower(): c for c in cols}

        for name in name_options:
            col = low_map.get(name.lower())
            if col is not None:
                return raw.get(prefix + col, default)

        # fallback: contains match
        for name in name_options:
            name_low = name.lower()
            for col in cols:
                if name_low in col.lower():
                    return raw.get(prefix + col, default)

        return default

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _technical_score(
        sharpness: float,
        stability: float,
        exposure: float,
        motion: float,
        beauty: float,
    ) -> float:
        return clamp(
            sharpness * 0.30
            + stability * 0.22
            + exposure * 0.18
            + beauty * 0.20
            + motion * 0.10
        )

    @staticmethod
    def _expansion_score(
        ai_keep: float,
        sharpness: float,
        stability: float,
        exposure: float,
        motion: float,
        beauty: float,
        duration: float,
    ) -> float:
        duration_score = 100.0
        if duration < 1.2:
            duration_score = 45.0
        elif duration < 2.0:
            duration_score = 75.0

        return clamp(
            ai_keep * 0.52
            + beauty * 0.18
            + sharpness * 0.12
            + stability * 0.08
            + exposure * 0.06
            + duration_score * 0.04
            - max(0.0, motion - 95.0) * 0.25
        )

    @staticmethod
    def _rank_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ranked = sorted(
            rows,
            key=lambda r: (
                float(r.get("expansion_score", 0.0)),
                float(r.get("ai_keep_score", 0.0)),
                float(r.get("beauty_score", 0.0)),
            ),
            reverse=True,
        )

        for idx, row in enumerate(ranked, start=1):
            row["rank_all_segments"] = idx

        return ranked

    def _select_candidates(self, ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        per_video: dict[str, int] = {}

        for row in ranked:
            score = float(row.get("expansion_score", row.get("ai_keep_score", 0.0)))
            if score < self.config.min_ai_score:
                continue

            video_path = str(row.get("video_path", ""))
            used = per_video.get(video_path, 0)
            if used >= self.config.max_segments_per_video:
                continue

            selected.append(dict(row))
            per_video[video_path] = used + 1

            if len(selected) >= self.config.top_candidates:
                return selected

        if len(selected) < self.config.top_candidates:
            already = {
                (
                    str(r.get("video_path", "")),
                    float(r.get("source_start_seconds", 0.0)),
                    float(r.get("source_end_seconds", 0.0)),
                )
                for r in selected
            }

            for row in ranked:
                identity = (
                    str(row.get("video_path", "")),
                    float(row.get("source_start_seconds", 0.0)),
                    float(row.get("source_end_seconds", 0.0)),
                )

                if identity in already:
                    continue

                selected.append(dict(row))
                already.add(identity)

                if len(selected) >= self.config.top_candidates:
                    break

        return selected

    @staticmethod
    def _retimeline(rows: list[dict[str, Any]]) -> None:
        cursor = 0.0

        for index, row in enumerate(rows, start=1):
            duration = float(row.get("duration_seconds", 0.0))

            row["order"] = index
            row["timeline_start_seconds"] = round(cursor, 3)
            row["timeline_end_seconds"] = round(cursor + duration, 3)

            cursor += duration

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return

        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_summary(path: Path, all_rows: list[dict], ranked: list[dict], selected: list[dict]) -> None:
        avg_selected = 0.0
        if selected:
            avg_selected = sum(float(r.get("expansion_score", 0.0)) for r in selected) / len(selected)

        lines = [
            "STT AI Editor - Full Source Candidate Expansion Summary",
            "=" * 65,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"Total DB segments: {len(all_rows)}",
            f"Ranked segments: {len(ranked)}",
            f"Selected candidates: {len(selected)}",
            f"Average selected expansion score: {avg_selected:.2f}",
            "",
            "Top selected candidates:",
        ]

        for row in selected[:50]:
            lines.append(
                f"#{int(row.get('order', 0)):03d} "
                f"{row.get('video_filename')} "
                f"{float(row.get('source_start_seconds', 0.0)):.2f}-"
                f"{float(row.get('source_end_seconds', 0.0)):.2f}s "
                f"expansion={float(row.get('expansion_score', 0.0)):.1f} "
                f"ai={float(row.get('ai_keep_score', 0.0)):.1f} "
                f"rank_all={int(row.get('rank_all_segments', 0))}"
            )

        path.write_text("\n".join(lines), encoding="utf-8")


def expand_candidates_existing_project(
    project_root: str | Path,
    top_candidates: int = 120,
    min_ai_score: float = 30.0,
    max_segments_per_video: int = 6,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    expander = FullSourceCandidateExpander(
        project=project,
        config=CandidateExpansionConfig(
            top_candidates=top_candidates,
            min_ai_score=min_ai_score,
            max_segments_per_video=max_segments_per_video,
        ),
    )

    return expander.expand()
