from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from core.expansion import expand_candidates_existing_project
from core.exporter import export_premiere_xml_existing_project
from core.manual_review import generate_manual_review_existing_project
from core.media import scan_existing_project
from core.moment import find_best_moments_existing_project
from core.people_composition import analyze_people_composition_existing_project
from core.project import ProjectManager, STTProject
from core.reporting import generate_report_existing_project
from core.review import generate_preview_review_existing_project
from core.shot_detection import detect_shots_existing_project
from core.story import build_story_timeline_existing_project
from core.vision import analyze_vision_existing_project


@dataclass
class OneClickPipelineConfig:
    # Existing project default:
    # run_scan/detect/analyze = False so test does not waste time on already processed DB.
    run_scan: bool = False
    run_detect_shots: bool = False
    run_analyze_vision: bool = False
    run_report: bool = True

    # Main AI cut stages.
    run_expand_candidates: bool = True
    run_best_moments: bool = True
    run_people_composition: bool = True
    run_story_timeline: bool = True
    run_premiere_xml: bool = True
    run_preview_review: bool = True
    run_manual_review: bool = True

    # Inputs.
    source_folder: str | None = None

    # Settings.
    segment_seconds: float = 3.0
    target_duration_seconds: float = 60.0
    top_candidates: int = 120
    min_ai_score: float = 30.0
    max_candidates_per_video: int = 6
    max_story_segments_per_video: int = 1
    best_moment_seconds: float = 2.2
    best_moment_sample_step: float = 0.33

    sequence_fps: int = 25
    sequence_width: int = 3840
    sequence_height: int = 2160


class OneClickPipelineRunner:
    # Build 016.
    # Runs the practical STT AI Editor pipeline with one command.
    # For an already processed project, it starts at expansion to avoid re-scanning/re-analyzing.

    def __init__(
        self,
        project_root: str | Path,
        config: OneClickPipelineConfig | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.config = config or OneClickPipelineConfig()
        self.project: STTProject = ProjectManager().open_project(self.project_root)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.project.paths.exports_dir / f"pipeline_run_{stamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.log_path = self.run_dir / "pipeline_log.txt"
        self.result_json = self.run_dir / "pipeline_result.json"

        self.results: dict[str, Any] = {
            "project_root": str(self.project_root),
            "run_dir": str(self.run_dir),
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "config": asdict(self.config),
            "steps": {},
        }

    def run(self) -> dict[str, Any]:
        self._log("STT AI Editor - One Click Pipeline")
        self._log("=" * 60)
        self._log(f"Project: {self.project.name}")
        self._log(f"Project root: {self.project_root}")
        self._log(f"Run dir: {self.run_dir}")
        self._log("")

        try:
            if self.config.run_scan:
                self._step(
                    "scan",
                    lambda: scan_existing_project(
                        project_root=self.project_root,
                        source_folder=Path(self.config.source_folder) if self.config.source_folder else None,
                    ),
                )
            else:
                self._skip("scan")

            if self.config.run_detect_shots:
                self._step(
                    "detect_shots",
                    lambda: detect_shots_existing_project(
                        project_root=self.project_root,
                        segment_seconds=self.config.segment_seconds,
                        reset_existing=False,
                    ),
                )
            else:
                self._skip("detect_shots")

            if self.config.run_analyze_vision:
                self._step(
                    "analyze_vision",
                    lambda: analyze_vision_existing_project(
                        project_root=self.project_root,
                        limit=None,
                        only_pending=True,
                    ),
                )
            else:
                self._skip("analyze_vision")

            if self.config.run_report:
                self._step(
                    "report",
                    lambda: generate_report_existing_project(
                        project_root=self.project_root,
                        limit=200,
                        min_keep_score=45.0,
                    ),
                )
            else:
                self._skip("report")

            expanded: dict[str, str] | None = None
            if self.config.run_expand_candidates:
                expanded = self._step(
                    "expand_candidates",
                    lambda: expand_candidates_existing_project(
                        project_root=self.project_root,
                        top_candidates=self.config.top_candidates,
                        min_ai_score=self.config.min_ai_score,
                        max_segments_per_video=self.config.max_candidates_per_video,
                    ),
                )
            else:
                self._skip("expand_candidates")

            current_json: Path | None = None
            if expanded and expanded.get("roughcut_plan_json"):
                current_json = Path(expanded["roughcut_plan_json"])

            best: dict[str, str] | None = None
            if self.config.run_best_moments:
                best = self._step(
                    "best_moments",
                    lambda: find_best_moments_existing_project(
                        project_root=self.project_root,
                        roughcut_json=current_json,
                        refined_segment_seconds=self.config.best_moment_seconds,
                        sample_step_seconds=self.config.best_moment_sample_step,
                    ),
                )
                if best and best.get("refined_json"):
                    current_json = Path(best["refined_json"])
            else:
                self._skip("best_moments")

            people: dict[str, str] | None = None
            if self.config.run_people_composition:
                people = self._step(
                    "people_composition",
                    lambda: analyze_people_composition_existing_project(
                        project_root=self.project_root,
                        input_json=current_json,
                    ),
                )
                if people and people.get("people_json"):
                    current_json = Path(people["people_json"])
            else:
                self._skip("people_composition")

            story: dict[str, str] | None = None
            if self.config.run_story_timeline:
                story = self._step(
                    "story_timeline",
                    lambda: build_story_timeline_existing_project(
                        project_root=self.project_root,
                        input_json=current_json,
                        target_duration_seconds=self.config.target_duration_seconds,
                        max_segments_per_video=self.config.max_story_segments_per_video,
                    ),
                )
                if story and story.get("story_json"):
                    current_json = Path(story["story_json"])
            else:
                self._skip("story_timeline")

            xml: dict[str, str] | None = None
            if self.config.run_premiere_xml:
                if current_json is None:
                    raise RuntimeError("No current_json available for Premiere XML export.")

                xml = self._step(
                    "premiere_xml",
                    lambda: export_premiere_xml_existing_project(
                        project_root=self.project_root,
                        roughcut_json=current_json,
                        sequence_fps=self.config.sequence_fps,
                        sequence_width=self.config.sequence_width,
                        sequence_height=self.config.sequence_height,
                    ),
                )
            else:
                self._skip("premiere_xml")

            review: dict[str, str] | None = None
            if self.config.run_preview_review:
                if current_json is None:
                    raise RuntimeError("No current_json available for preview review.")

                review = self._step(
                    "preview_review",
                    lambda: generate_preview_review_existing_project(
                        project_root=self.project_root,
                        roughcut_json=current_json,
                    ),
                )
            else:
                self._skip("preview_review")

            manual_review: dict[str, str] | None = None
            if self.config.run_manual_review:
                if current_json is None:
                    raise RuntimeError("No current_json available for manual review.")

                manual_review = self._step(
                    "manual_review",
                    lambda: generate_manual_review_existing_project(
                        project_root=self.project_root,
                        input_json=current_json,
                    ),
                )
            else:
                self._skip("manual_review")

            self.results["finished_at"] = datetime.now().isoformat(timespec="seconds")
            self.results["status"] = "success"
            self.results["final_json"] = str(current_json) if current_json else ""
            self.results["premiere_xml"] = xml.get("xml", "") if isinstance(xml, dict) else ""
            self.results["review_html"] = review.get("html", "") if isinstance(review, dict) else ""
            self.results["manual_review_html"] = manual_review.get("html", "") if isinstance(manual_review, dict) else ""

            self._save_results()

            self._log("")
            self._log("PIPELINE COMPLETE")
            self._log(f"Final JSON: {self.results['final_json']}")
            self._log(f"Premiere XML: {self.results['premiere_xml']}")
            self._log(f"Review HTML: {self.results['review_html']}")
            self._log(f"Manual Review HTML: {self.results['manual_review_html']}")
            self._log(f"Pipeline log: {self.log_path}")
            self._log(f"Pipeline result: {self.result_json}")
            self._log("-" * 60)

            return self.results

        except Exception as exc:
            self.results["finished_at"] = datetime.now().isoformat(timespec="seconds")
            self.results["status"] = "error"
            self.results["error"] = repr(exc)
            self._save_results()
            self._log("")
            self._log("PIPELINE ERROR")
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

    def _skip(self, name: str) -> None:
        self.results["steps"][name] = {"status": "skipped"}
        self._log(f"[SKIP] {name}")

    def _log(self, text: str) -> None:
        print(text)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(text + "\n")

    def _save_results(self) -> None:
        self.result_json.write_text(
            json.dumps(self.results, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )


def run_one_click_pipeline_existing_project(
    project_root: str | Path,
    source_folder: str | Path | None = None,
    run_from_scratch: bool = False,
    target_duration_seconds: float = 60.0,
    top_candidates: int = 120,
) -> dict[str, Any]:
    config = OneClickPipelineConfig(
        source_folder=str(source_folder) if source_folder else None,
        run_scan=run_from_scratch,
        run_detect_shots=run_from_scratch,
        run_analyze_vision=run_from_scratch,
        target_duration_seconds=target_duration_seconds,
        top_candidates=top_candidates,
    )

    runner = OneClickPipelineRunner(project_root=project_root, config=config)
    return runner.run()
