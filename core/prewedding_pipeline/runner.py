
from __future__ import annotations

import json
import os
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"

PIPELINE_INTENTS = [
    "prewedding_reel_30s",
    "prewedding_reel_60s",
    "prewedding_cinematic",
    "prewedding_fashion",
    "prewedding_location_film",
]


@dataclass
class PreweddingPipelineConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    intent: str = "prewedding_reel_60s"
    preset: str | None = None
    target_duration: float | None = None
    open_folder: bool = True
    stop_on_error: bool = True


class PreweddingOneClickPipeline:
    # Module 051: run 046 -> 047 -> 048 -> 050 -> 049 in one command.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()
        self.project_pipeline_path = self.project_root / "stt_prewedding_pipeline_v1.json"
        self.appdata_pipeline_path = self.appdata_dir / "stt_prewedding_pipeline_v1.json"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    @staticmethod
    def default_xml_preset(intent: str) -> str:
        if "reel" in intent or "fashion" in intent:
            return "vertical_1080_25p"
        return "fhd_1080_25p"

    def run(
        self,
        intent: str = "prewedding_reel_60s",
        preset: str | None = None,
        target_duration: float | None = None,
        open_folder: bool = True,
        stop_on_error: bool = True,
    ) -> dict[str, Any]:
        if intent not in PIPELINE_INTENTS:
            raise ValueError(f"Unknown intent: {intent}. Available: {', '.join(PIPELINE_INTENTS)}")

        self.project_root.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.appdata_dir.mkdir(parents=True, exist_ok=True)

        preset = preset or self.default_xml_preset(intent)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = self.exports_dir / f"prewedding_pipeline_v1_{intent}_{stamp}"
        report_dir.mkdir(parents=True, exist_ok=True)

        state: dict[str, Any] = {
            "ok": False,
            "module": "051_prewedding_one_click_pipeline",
            "version": "0.51",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(self.project_root),
            "intent": intent,
            "preset": preset,
            "target_duration": target_duration,
            "report_dir": str(report_dir),
            "steps": [],
            "outputs": {},
            "errors": [],
            "summary": {},
            "next_steps": [
                "Premiere panel STT AI Editor > Refresh Latest XML > Import Latest XML.",
                "Review hook đầu, crop dọc, beat cut và relink source nếu Premiere hỏi.",
            ],
        }

        def save_state() -> None:
            state["updated_at"] = datetime.now().isoformat(timespec="seconds")
            text = json.dumps(state, ensure_ascii=False, indent=2)
            self.project_pipeline_path.write_text(text, encoding="utf-8")
            self.appdata_pipeline_path.write_text(text, encoding="utf-8")
            (report_dir / "stt_prewedding_pipeline_v1.json").write_text(text, encoding="utf-8")

        save_state()

        steps = [
            ("046_ai_shot_scorer", "046 AI Shot Scorer", lambda: self.step_score(intent)),
            ("047_prewedding_selector", "047 Prewedding Selector", lambda: self.step_select(intent, target_duration)),
            ("048_prewedding_roughcut", "048 Prewedding Roughcut", lambda: self.step_roughcut(intent, target_duration)),
            ("050_prewedding_refiner", "050 Prewedding Smart Refiner", lambda: self.step_refine(intent, target_duration)),
            ("049_prewedding_xml", "049 Prewedding XML Export", lambda: self.step_xml(preset)),
        ]

        for name, label, func in steps:
            if stop_on_error and state["errors"]:
                break
            self.run_step(state, name, label, func, save_state)

        state["ok"] = len(state["errors"]) == 0 and len(state["steps"]) == len(steps)
        state["summary"] = self.build_summary(state)

        summary_txt = report_dir / "PREWEDDING_PIPELINE_SUMMARY.txt"
        summary_html = report_dir / "PREWEDDING_PIPELINE_SUMMARY.html"
        summary_txt.write_text(self.render_text(state), encoding="utf-8")
        summary_html.write_text(self.render_html(state), encoding="utf-8")
        (report_dir / "Open_Report_Folder.bat").write_text(f'@echo off\nstart "" "{report_dir}"\n', encoding="utf-8")

        state["outputs"]["pipeline_json"] = str(self.project_pipeline_path)
        state["outputs"]["appdata_pipeline_json"] = str(self.appdata_pipeline_path)
        state["outputs"]["summary_txt"] = str(summary_txt)
        state["outputs"]["summary_html"] = str(summary_html)
        save_state()

        if open_folder:
            try:
                os.startfile(report_dir)
            except Exception:
                pass

        return {
            "ok": state["ok"],
            "intent": intent,
            "preset": preset,
            "report_dir": str(report_dir),
            "steps_total": len(state["steps"]),
            "steps_ok": sum(1 for x in state["steps"] if x.get("ok")),
            "errors": state["errors"],
            "outputs": state["outputs"],
            "xml": state["outputs"].get("xml"),
            "summary_html": str(summary_html),
        }

    def run_step(self, state: dict[str, Any], name: str, label: str, func, save_state) -> None:
        step = {
            "name": name,
            "label": label,
            "ok": False,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": None,
            "result": None,
            "error": None,
        }
        state["steps"].append(step)
        save_state()

        try:
            result = func()
            step["ok"] = True
            step["result"] = result
            self.collect_outputs(state, name, result)
        except Exception as exc:
            err = {
                "step": name,
                "label": label,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            step["ok"] = False
            step["error"] = err
            state["errors"].append(err)
        finally:
            step["finished_at"] = datetime.now().isoformat(timespec="seconds")
            save_state()

    def step_score(self, intent: str) -> dict[str, Any]:
        from core.ai_shot_scorer import run_ai_shot_scorer
        return run_ai_shot_scorer(self.project_root, intent=intent, top_n=180, open_folder=False)

    def step_select(self, intent: str, target_duration: float | None) -> dict[str, Any]:
        from core.prewedding_selector import build_prewedding_selection
        return build_prewedding_selection(self.project_root, intent=intent, target_duration=target_duration, open_folder=False)

    def step_roughcut(self, intent: str, target_duration: float | None) -> dict[str, Any]:
        from core.prewedding_roughcut import build_prewedding_roughcut
        return build_prewedding_roughcut(
            self.project_root,
            intent=intent,
            target_duration=target_duration,
            write_selection_compat=True,
            open_folder=False,
        )

    def step_refine(self, intent: str, target_duration: float | None) -> dict[str, Any]:
        from core.prewedding_refiner import refine_prewedding_roughcut
        return refine_prewedding_roughcut(
            self.project_root,
            intent=intent,
            target_duration=target_duration,
            write_selection_compat=True,
            open_folder=False,
        )

    def step_xml(self, preset: str) -> dict[str, Any]:
        from core.prewedding_xml import export_prewedding_xml
        return export_prewedding_xml(self.project_root, preset=preset, open_folder=False)

    @staticmethod
    def collect_outputs(state: dict[str, Any], name: str, result: Any) -> None:
        if not isinstance(result, dict):
            return
        outputs = state.setdefault("outputs", {})
        outputs[f"{name}_result"] = result

        for key in [
            "report_dir", "report_html", "summary_html", "project_selection",
            "project_roughcut", "project_refined", "xml", "project_xml",
            "timeline_csv", "selected_csv", "refined_json", "roughcut_json", "manifest",
        ]:
            value = result.get(key)
            if value:
                outputs[f"{name}_{key}"] = value

        if name == "049_prewedding_xml" and result.get("xml"):
            outputs["xml"] = result.get("xml")
            outputs["xml_report_dir"] = result.get("report_dir")

    @staticmethod
    def build_summary(state: dict[str, Any]) -> dict[str, Any]:
        steps = state.get("steps", [])
        return {
            "ok": state.get("ok"),
            "intent": state.get("intent"),
            "preset": state.get("preset"),
            "steps_total": len(steps),
            "steps_ok": sum(1 for x in steps if x.get("ok")),
            "steps_failed": [x.get("name") for x in steps if not x.get("ok")],
            "xml": state.get("outputs", {}).get("xml"),
            "ready_for_premiere": bool(state.get("outputs", {}).get("xml")) and len(state.get("errors", [])) == 0,
            "error_count": len(state.get("errors", [])),
        }

    @staticmethod
    def render_text(state: dict[str, Any]) -> str:
        lines = [
            "STT AI Editor - Prewedding One-Click Pipeline",
            "=" * 72,
            f"OK: {state.get('ok')}",
            f"Intent: {state.get('intent')}",
            f"Preset: {state.get('preset')}",
            f"Project: {state.get('project_root')}",
            "",
            "Steps:",
        ]
        for step in state.get("steps", []):
            status = "OK" if step.get("ok") else "ERROR"
            lines.append(f"- {status} | {step.get('label')}")

        if state.get("errors"):
            lines += ["", "Errors:"]
            for err in state.get("errors", []):
                lines.append(f"- {err.get('label')}: {err.get('error')}")

        outputs = state.get("outputs", {})
        lines += [
            "",
            "Key outputs:",
            f"- XML: {outputs.get('xml')}",
            f"- Pipeline JSON: {outputs.get('pipeline_json')}",
            "",
            "Premiere:",
            "- STT AI Editor panel > Refresh Latest XML > Import Latest XML",
            "- Hoặc Premiere > File > Import > chọn XML",
        ]
        return "\n".join(lines)

    @staticmethod
    def render_html(state: dict[str, Any]) -> str:
        import html

        ok = html.escape(str(state.get("ok")))
        intent = html.escape(str(state.get("intent")))
        preset = html.escape(str(state.get("preset")))
        project = html.escape(str(state.get("project_root")))
        xml = html.escape(str(state.get("outputs", {}).get("xml", "")))

        step_rows = []
        for step in state.get("steps", []):
            status = "OK" if step.get("ok") else "ERROR"
            step_rows.append(
                "<tr>"
                f"<td>{html.escape(status)}</td>"
                f"<td>{html.escape(str(step.get('label')))}</td>"
                f"<td>{html.escape(str(step.get('started_at')))}</td>"
                f"<td>{html.escape(str(step.get('finished_at')))}</td>"
                "</tr>"
            )

        error_rows = []
        for err in state.get("errors", []):
            error_rows.append(
                "<tr>"
                f"<td>{html.escape(str(err.get('label')))}</td>"
                f"<td>{html.escape(str(err.get('error')))}</td>"
                "</tr>"
            )
        if not error_rows:
            error_rows.append("<tr><td colspan='2'>No errors</td></tr>")

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT Prewedding One-Click Pipeline</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 1200px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; border: 1px solid #666; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
th, td {{ border-bottom: 1px solid #333; padding: 8px; vertical-align: top; text-align: left; }}
code {{ display:block; background:#000; padding:12px; border-radius:10px; overflow-wrap:anywhere; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">Module 051</div>
  <h1>Prewedding One-Click Pipeline</h1>
  <p>Status: <b>{ok}</b></p>
  <p>Intent: <b>{intent}</b> | Preset: <b>{preset}</b></p>
  <p>Project: {project}</p>
  <h2>XML ready for Premiere</h2>
  <code>{xml}</code>
  <h2>Steps</h2>
  <table>
    <tr><th>Status</th><th>Step</th><th>Started</th><th>Finished</th></tr>
    {''.join(step_rows)}
  </table>
  <h2>Errors</h2>
  <table>
    <tr><th>Step</th><th>Error</th></tr>
    {''.join(error_rows)}
  </table>
  <h2>Import Premiere</h2>
  <ol>
    <li>Premiere panel STT AI Editor &gt; Refresh Latest XML &gt; Import Latest XML</li>
    <li>Hoặc Premiere &gt; File &gt; Import &gt; chọn XML</li>
  </ol>
</div>
</body>
</html>
'''


def run_prewedding_pipeline(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    intent: str = "prewedding_reel_60s",
    preset: str | None = None,
    target_duration: float | None = None,
    open_folder: bool = True,
    stop_on_error: bool = True,
) -> dict[str, Any]:
    return PreweddingOneClickPipeline(project_root).run(
        intent=intent,
        preset=preset,
        target_duration=target_duration,
        open_folder=open_folder,
        stop_on_error=stop_on_error,
    )
