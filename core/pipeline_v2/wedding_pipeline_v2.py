from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.duplicate_remover import remove_duplicate_shots_existing_project
from core.exporter import export_premiere_xml_existing_project
from core.manual_review import generate_manual_review_existing_project
from core.review import generate_preview_review_existing_project
from core.story_v2 import build_story_timeline_v2_existing_project
from core.wedding_scene import classify_wedding_scenes_existing_project


@dataclass
class WeddingPipelineV2Config:
    target_duration_seconds: float = 60.0
    max_segments_per_video: int = 1
    sequence_fps: int = 25
    sequence_width: int = 3840
    sequence_height: int = 2160


class WeddingPipelineV2Runner:
    # Build 024.
    # Runs the new smarter wedding pipeline after Module 021/022/023:
    #
    # 1. classify wedding scenes
    # 2. build story timeline v2 from wedding_scene labels
    # 3. remove duplicate / repeated shots
    # 4. export Premiere XML
    # 5. generate review.html
    # 6. generate manual_review.html
    #
    # It does not scan/detect/analyze again.

    def __init__(
        self,
        project_root: str | Path,
        config: WeddingPipelineV2Config | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.config = config or WeddingPipelineV2Config()

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.project_root / "exports" / f"wedding_pipeline_v2_{stamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.log_path = self.run_dir / "wedding_pipeline_v2_log.txt"
        self.result_json = self.run_dir / "wedding_pipeline_v2_result.json"

        self.results: dict[str, Any] = {
            "project_root": str(self.project_root),
            "run_dir": str(self.run_dir),
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "config": asdict(self.config),
            "steps": {},
        }

    def run(self) -> dict[str, Any]:
        self._log("STT AI Editor - Wedding Pipeline V2")
        self._log("=" * 70)
        self._log(f"Project root: {self.project_root}")
        self._log(f"Run dir: {self.run_dir}")
        self._log("")

        try:
            scene = self._step(
                "wedding_scene_classifier",
                lambda: classify_wedding_scenes_existing_project(
                    project_root=self.project_root,
                    input_json=None,
                ),
            )

            story = self._step(
                "story_timeline_v2",
                lambda: build_story_timeline_v2_existing_project(
                    project_root=self.project_root,
                    input_json=Path(scene["scene_json"]),
                    target_duration_seconds=self.config.target_duration_seconds,
                    max_segments_per_video=self.config.max_segments_per_video,
                ),
            )

            dedupe = self._step(
                "duplicate_shot_remover",
                lambda: remove_duplicate_shots_existing_project(
                    project_root=self.project_root,
                    input_json=Path(story["story_json"]),
                    fill_pool_json=Path(scene["scene_json"]),
                    target_duration_seconds=self.config.target_duration_seconds,
                ),
            )

            final_json = Path(dedupe["no_duplicates_json"])

            xml = self._step(
                "premiere_xml",
                lambda: export_premiere_xml_existing_project(
                    project_root=self.project_root,
                    roughcut_json=final_json,
                    sequence_fps=self.config.sequence_fps,
                    sequence_width=self.config.sequence_width,
                    sequence_height=self.config.sequence_height,
                ),
            )

            review = self._step(
                "preview_review",
                lambda: generate_preview_review_existing_project(
                    project_root=self.project_root,
                    roughcut_json=final_json,
                ),
            )

            manual = self._step(
                "manual_review",
                lambda: generate_manual_review_existing_project(
                    project_root=self.project_root,
                    input_json=final_json,
                ),
            )

            self.results["finished_at"] = datetime.now().isoformat(timespec="seconds")
            self.results["status"] = "success"
            self.results["scene_json"] = scene.get("scene_json", "")
            self.results["story_json"] = story.get("story_json", "")
            self.results["final_json"] = str(final_json)
            self.results["premiere_xml"] = xml.get("xml", "")
            self.results["review_html"] = review.get("html", "")
            self.results["manual_review_html"] = manual.get("html", "")

            self._save_results()

            self._log("")
            self._log("WEDDING PIPELINE V2 COMPLETE")
            self._log(f"Final JSON: {self.results['final_json']}")
            self._log(f"Premiere XML: {self.results['premiere_xml']}")
            self._log(f"Review HTML: {self.results['review_html']}")
            self._log(f"Manual Review HTML: {self.results['manual_review_html']}")
            self._log(f"Pipeline log: {self.log_path}")
            self._log(f"Pipeline result: {self.result_json}")
            self._log("-" * 70)

            return self.results

        except Exception as exc:
            self.results["finished_at"] = datetime.now().isoformat(timespec="seconds")
            self.results["status"] = "error"
            self.results["error"] = repr(exc)
            self._save_results()
            self._log("")
            self._log("WEDDING PIPELINE V2 ERROR")
            self._log(repr(exc))
            self._log(f"Pipeline log: {self.log_path}")
            self._log(f"Pipeline result: {self.result_json}")
            raise

    def _step(self, name: str, func):
        self._log("")
        self._log(f"[START] {name}")
        start = time.time()

        result = func()

        elapsed = time.time() - start
        self.results["steps"][name] = {
            "status": "done",
            "seconds": round(elapsed, 2),
            "result": result,
        }

        self._save_results()
        self._log(f"[DONE] {name} - {elapsed:.2f}s")
        return result

    def _log(self, text: str) -> None:
        print(text)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(text + "\n")

    def _save_results(self) -> None:
        self.result_json.write_text(
            json.dumps(self.results, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )


def run_wedding_pipeline_v2_existing_project(
    project_root: str | Path,
    target_duration_seconds: float = 60.0,
    max_segments_per_video: int = 1,
) -> dict[str, Any]:
    runner = WeddingPipelineV2Runner(
        project_root=project_root,
        config=WeddingPipelineV2Config(
            target_duration_seconds=target_duration_seconds,
            max_segments_per_video=max_segments_per_video,
        ),
    )
    return runner.run()
