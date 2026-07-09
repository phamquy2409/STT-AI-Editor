
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


COMMANDS = [
    ("Check Prewedding Pipeline", "01_Check_Prewedding_Pipeline.bat", "python scripts/check_prewedding_pipeline.py", "Kiểm tra đủ module/file/XML trước khi chạy."),
    ("Run Full Prewedding Reel 60s", "02_Run_Full_Prewedding_Reel_60s.bat", "python scripts/run_prewedding_pipeline.py --intent prewedding_reel_60s", "Luồng chính prewedding reel 60s."),
    ("Run Full Prewedding Reel 30s", "03_Run_Full_Prewedding_Reel_30s.bat", "python scripts/run_prewedding_pipeline.py --intent prewedding_reel_30s", "Luồng prewedding reel 30s."),
    ("Run Full Prewedding Cinematic", "04_Run_Full_Prewedding_Cinematic.bat", "python scripts/run_prewedding_pipeline.py --intent prewedding_cinematic", "Luồng prewedding cinematic ngang."),
    ("Create Master Dashboard", "05_Create_Master_Dashboard.bat", "python scripts/create_master_dashboard.py", "Tạo dashboard tổng."),
    ("Create Review Package", "06_Create_Review_Package.bat", "python scripts/create_review_package.py", "Xuất gói review clip/timeline."),
    ("Create Premiere Relink Report", "07_Create_Premiere_Relink_Report.bat", "python scripts/create_premiere_relink_report.py", "Xuất danh sách source để relink trong Premiere."),
    ("Create Music Beat Plan", "08_Create_Music_Beat_Plan.bat", "python scripts/create_music_beat_plan.py", "Xuất beat marker/cut plan."),
    ("Create Pipeline Snapshot", "09_Create_Pipeline_Snapshot.bat", "python scripts/create_pipeline_snapshot.py", "Backup nhanh file quan trọng."),
    ("Build EXE", "10_Build_EXE.bat", "python scripts/build_exe.py", "Build app Windows."),
    ("Package Release", "11_Package_Release.bat", "python scripts/package_release.py", "Đóng gói release sau khi build EXE."),
]


def create_project_command_center(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    repo_root: str | Path | None = None,
    open_folder: bool = True,
) -> dict[str, Any]:
    project_root = Path(project_root)
    repo_root = Path(repo_root) if repo_root else detect_repo_root()

    exports = project_root / "exports"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = exports / f"project_command_center_{stamp}"
    bat_dir = output_dir / "bat_shortcuts"
    bat_dir.mkdir(parents=True, exist_ok=True)

    commands = []
    for name, bat_name, command, note in COMMANDS:
        bat_path = bat_dir / bat_name
        bat_path.write_text(make_bat(repo_root, project_root, command), encoding="utf-8")
        commands.append({
            "name": name,
            "bat": bat_name,
            "bat_path": str(bat_path),
            "command": command,
            "note": note,
        })

    utility_files = create_utility_bats(output_dir, repo_root, project_root)
    latest_xml = find_latest_xml(project_root)
    latest_report = find_latest_report(project_root)

    manifest = {
        "ok": True,
        "module": "061_project_command_center",
        "version": "0.61",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "repo_root": str(repo_root),
        "output_dir": str(output_dir),
        "bat_dir": str(bat_dir),
        "latest_xml": str(latest_xml) if latest_xml else None,
        "latest_report": str(latest_report) if latest_report else None,
        "commands": commands,
        "utility_files": utility_files,
    }

    manifest_path = output_dir / "project_command_center_manifest.json"
    html_path = output_dir / "PROJECT_COMMAND_CENTER.html"
    txt_path = output_dir / "PROJECT_COMMAND_CENTER.txt"

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_html(manifest), encoding="utf-8")
    txt_path.write_text(render_text(manifest), encoding="utf-8")

    if open_folder:
        try:
            os.startfile(html_path)
        except Exception:
            try:
                os.startfile(output_dir)
            except Exception:
                pass

    return {
        "ok": True,
        "output_dir": str(output_dir),
        "report_dir": str(output_dir),
        "html": str(html_path),
        "txt": str(txt_path),
        "bat_dir": str(bat_dir),
        "command_count": len(commands),
        "latest_xml": str(latest_xml) if latest_xml else None,
    }


def detect_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "scripts").exists() and (parent / "core").exists():
            return parent
    return Path.cwd()


def make_bat(repo_root: Path, project_root: Path, command: str) -> str:
    final_command = command
    if "--project" not in final_command and command.startswith("python scripts/"):
        final_command = f'{command} --project "{project_root}"'

    return "\n".join([
        "@echo off",
        "chcp 65001 >nul",
        f'cd /d "{repo_root}"',
        "echo.",
        f"echo RUN: {final_command}",
        "echo.",
        final_command,
        "echo.",
        "pause",
        "",
    ])


def create_utility_bats(output_dir: Path, repo_root: Path, project_root: Path) -> list[dict[str, str]]:
    utilities = []
    data = [
        ("Open_Project_Folder.bat", f'start "" "{project_root}"'),
        ("Open_Exports_Folder.bat", f'start "" "{project_root / "exports"}"'),
        ("Open_Repo_Folder.bat", f'start "" "{repo_root}"'),
        ("Open_Dist_Folder.bat", f'start "" "{repo_root / "dist"}"'),
        ("Open_Releases_Folder.bat", f'start "" "{repo_root / "releases"}"'),
    ]

    latest_xml = find_latest_xml(project_root)
    if latest_xml:
        data.append(("Open_Latest_XML_Folder.bat", f'start "" "{latest_xml.parent}"'))

    for filename, command in data:
        path = output_dir / filename
        path.write_text("@echo off\n" + command + "\n", encoding="utf-8")
        utilities.append({"name": filename, "path": str(path), "command": command})

    return utilities


def find_latest_xml(project_root: Path) -> Path | None:
    candidates = []
    direct = project_root / "stt_prewedding_premiere_import.xml"
    if direct.exists():
        candidates.append(direct)

    exports = project_root / "exports"
    if exports.exists():
        candidates.extend([p for p in exports.glob("**/*.xml") if p.is_file() and "_archive" not in p.parts])

    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def find_latest_report(project_root: Path) -> Path | None:
    exports = project_root / "exports"
    if not exports.exists():
        return None
    htmls = [p for p in exports.glob("**/*.html") if p.is_file() and "_archive" not in p.parts]
    if not htmls:
        return None
    return sorted(htmls, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def render_text(manifest: dict[str, Any]) -> str:
    lines = [
        "STT AI Editor - Project Command Center",
        "=" * 72,
        f"Project: {manifest['project_root']}",
        f"Repo: {manifest['repo_root']}",
        f"Output: {manifest['output_dir']}",
        f"Latest XML: {manifest.get('latest_xml')}",
        "",
        "BAT shortcuts:",
    ]

    for item in manifest["commands"]:
        lines.append(f"- {item['name']}: {item['bat_path']}")

    lines += ["", "Open folder shortcuts:"]
    for item in manifest["utility_files"]:
        lines.append(f"- {item['name']}: {item['path']}")

    return "\n".join(lines)


def render_html(manifest: dict[str, Any]) -> str:
    import html

    project = html.escape(str(manifest["project_root"]))
    repo = html.escape(str(manifest["repo_root"]))
    output = html.escape(str(manifest["output_dir"]))
    latest_xml = html.escape(str(manifest.get("latest_xml") or ""))

    rows = []
    for item in manifest["commands"]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(item['name'])}</td>"
            f"<td>{html.escape(item['note'])}</td>"
            f"<td><code>{html.escape(item['command'])}</code></td>"
            f"<td><code>{html.escape(item['bat_path'])}</code></td>"
            "</tr>"
        )

    utility_rows = []
    for item in manifest["utility_files"]:
        utility_rows.append(
            "<tr>"
            f"<td>{html.escape(item['name'])}</td>"
            f"<td><code>{html.escape(item['path'])}</code></td>"
            "</tr>"
        )

    return (
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        "<title>STT Project Command Center</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:32px;line-height:1.55}"
        ".card{max-width:1500px;background:#181818;border:1px solid #333;border-radius:16px;padding:24px;margin-bottom:18px}"
        ".badge{display:inline-block;border:1px solid #666;border-radius:999px;padding:5px 9px;font-weight:700}"
        "table{border-collapse:collapse;width:100%;margin-top:12px}"
        "th,td{border-bottom:1px solid #333;padding:8px;vertical-align:top;text-align:left}"
        "code{background:#000;padding:4px 8px;border-radius:8px;overflow-wrap:anywhere}"
        "</style></head><body>"
        "<div class='card'>"
        "<div class='badge'>Module 061</div>"
        "<h1>STT Project Command Center</h1>"
        f"<p>Project: <code>{project}</code></p>"
        f"<p>Repo: <code>{repo}</code></p>"
        f"<p>Output: <code>{output}</code></p>"
        f"<p>Latest XML: <code>{latest_xml}</code></p>"
        "</div>"
        "<div class='card'><h2>Main Commands</h2><table>"
        "<tr><th>Name</th><th>Note</th><th>Command</th><th>BAT file</th></tr>"
        + "".join(rows) +
        "</table></div>"
        "<div class='card'><h2>Open Folder Shortcuts</h2><table>"
        "<tr><th>Name</th><th>Path</th></tr>"
        + "".join(utility_rows) +
        "</table></div>"
        "</body></html>"
    )
