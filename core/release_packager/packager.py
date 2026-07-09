
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
APP_NAME = "STT AI Editor"
RELEASE_VERSION = "0.53"


@dataclass
class ReleasePackagerConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    repo_root: str | None = None
    version: str = RELEASE_VERSION
    build_first: bool = False
    run_doctor: bool = True
    open_folder: bool = True


class STTReleasePackager:
    # Module 053.
    #
    # Creates a clean release package from dist/STT AI Editor.
    #
    # It can optionally:
    # - run build_exe.py first
    # - run Module 052 doctor before packaging
    # - copy dist app folder to releases/STT_AI_Editor_v...
    # - create zip release package
    # - write install/readme files
    #
    # Do not commit dist/build/releases. This is for local distribution only.

    def __init__(
        self,
        project_root: str | Path = DEFAULT_PROJECT_ROOT,
        repo_root: str | Path | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.repo_root = Path(repo_root) if repo_root else self.detect_repo_root()
        self.dist_app_dir = self.repo_root / "dist" / APP_NAME
        self.exe_path = self.dist_app_dir / f"{APP_NAME}.exe"
        self.releases_dir = self.repo_root / "releases"

    @staticmethod
    def detect_repo_root() -> Path:
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            if (parent / "scripts").exists() and (parent / "core").exists():
                return parent
        return Path.cwd()

    def package(
        self,
        version: str = RELEASE_VERSION,
        build_first: bool = False,
        run_doctor: bool = True,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        started = datetime.now()
        stamp = started.strftime("%Y%m%d_%H%M%S")
        release_name = f"STT_AI_Editor_v{version}_{stamp}"
        release_dir = self.releases_dir / release_name
        app_release_dir = release_dir / APP_NAME
        package_zip = self.releases_dir / f"{release_name}.zip"

        self.releases_dir.mkdir(parents=True, exist_ok=True)
        release_dir.mkdir(parents=True, exist_ok=True)

        state: dict[str, Any] = {
            "ok": False,
            "module": "053_release_packager",
            "version": version,
            "created_at": started.isoformat(timespec="seconds"),
            "project_root": str(self.project_root),
            "repo_root": str(self.repo_root),
            "dist_app_dir": str(self.dist_app_dir),
            "exe_path": str(self.exe_path),
            "release_dir": str(release_dir),
            "app_release_dir": str(app_release_dir),
            "zip": str(package_zip),
            "build_first": build_first,
            "run_doctor": run_doctor,
            "steps": [],
            "errors": [],
            "doctor_result": None,
            "git_status": None,
        }

        def step(name: str, func) -> Any:
            item = {
                "name": name,
                "ok": False,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "finished_at": None,
                "result": None,
                "error": None,
            }
            state["steps"].append(item)
            try:
                result = func()
                item["ok"] = True
                item["result"] = result
                return result
            except Exception as exc:
                item["error"] = repr(exc)
                state["errors"].append({"step": name, "error": repr(exc)})
                raise
            finally:
                item["finished_at"] = datetime.now().isoformat(timespec="seconds")
                self.write_json(release_dir / "release_packager_state.json", state)

        try:
            if run_doctor:
                state["doctor_result"] = step("doctor_check", self.run_doctor_check)

            if build_first:
                step("build_exe", self.run_build_exe)

            step("verify_dist", self.verify_dist)

            if app_release_dir.exists():
                shutil.rmtree(app_release_dir, ignore_errors=True)

            step("copy_app_folder", lambda: self.copy_app_folder(app_release_dir))
            step("write_release_files", lambda: self.write_release_files(release_dir, app_release_dir, version))
            state["git_status"] = step("git_status", self.git_status)
            step("zip_release", lambda: self.zip_release(release_dir, package_zip))

            state["ok"] = True

        except Exception:
            state["ok"] = False

        state["finished_at"] = datetime.now().isoformat(timespec="seconds")
        state["duration_seconds"] = round((datetime.now() - started).total_seconds(), 3)

        self.write_json(release_dir / "release_manifest.json", state)
        (release_dir / "RELEASE_SUMMARY.txt").write_text(self.render_text(state), encoding="utf-8")
        (release_dir / "RELEASE_SUMMARY.html").write_text(self.render_html(state), encoding="utf-8")

        if open_folder:
            try:
                os.startfile(release_dir)
            except Exception:
                pass

        return {
            "ok": state["ok"],
            "version": version,
            "release_dir": str(release_dir),
            "app_release_dir": str(app_release_dir),
            "zip": str(package_zip) if package_zip.exists() else None,
            "exe": str(app_release_dir / f"{APP_NAME}.exe"),
            "errors": state["errors"],
            "doctor_ready": (state.get("doctor_result") or {}).get("ready_for_pipeline"),
            "git_status_clean_hint": self.git_clean_hint(state.get("git_status")),
        }

    @staticmethod
    def write_json(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def run_doctor_check(self) -> dict[str, Any]:
        try:
            from core.prewedding_doctor import check_prewedding_pipeline
            return check_prewedding_pipeline(
                project_root=self.project_root,
                repo_root=self.repo_root,
                open_folder=False,
            )
        except Exception as exc:
            return {
                "ok": False,
                "error": repr(exc),
                "note": "Doctor failed or Module 052 not installed. Packaging can still continue if dist exists.",
            }

    def run_build_exe(self) -> dict[str, Any]:
        build_script = self.repo_root / "scripts" / "build_exe.py"
        if not build_script.exists():
            raise FileNotFoundError(f"Missing build script: {build_script}")

        cmd = [sys.executable, str(build_script)]
        proc = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            shell=False,
        )

        return {
            "cmd": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
            "exe_exists": self.exe_path.exists(),
        }

    def verify_dist(self) -> dict[str, Any]:
        if not self.dist_app_dir.exists():
            raise FileNotFoundError(
                f"Không thấy app folder: {self.dist_app_dir}\n"
                "Hãy chạy trước: python scripts/build_exe.py\n"
                "Hoặc chạy package với --build-first"
            )

        if not self.exe_path.exists():
            raise FileNotFoundError(
                f"Không thấy EXE: {self.exe_path}\n"
                "Hãy chạy trước: python scripts/build_exe.py"
            )

        files = [p for p in self.dist_app_dir.rglob("*") if p.is_file()]
        size = sum(p.stat().st_size for p in files)

        return {
            "dist_app_dir": str(self.dist_app_dir),
            "exe_path": str(self.exe_path),
            "files": len(files),
            "size_bytes": size,
            "size_gb": round(size / (1024 ** 3), 3),
        }

    def copy_app_folder(self, app_release_dir: Path) -> dict[str, Any]:
        shutil.copytree(self.dist_app_dir, app_release_dir)
        files = [p for p in app_release_dir.rglob("*") if p.is_file()]
        size = sum(p.stat().st_size for p in files)

        return {
            "app_release_dir": str(app_release_dir),
            "files": len(files),
            "size_bytes": size,
            "size_gb": round(size / (1024 ** 3), 3),
        }

    def write_release_files(self, release_dir: Path, app_release_dir: Path, version: str) -> dict[str, Any]:
        exe = app_release_dir / f"{APP_NAME}.exe"

        readme = release_dir / "README_INSTALL.txt"
        readme.write_text(
            "\n".join([
                "STT AI Editor - Release Package",
                "=" * 72,
                "",
                f"Version: {version}",
                f"Created: {datetime.now().isoformat(timespec='seconds')}",
                "",
                "CÁCH CHẠY:",
                "",
                "1. Mở folder:",
                str(app_release_dir),
                "",
                "2. Chạy file:",
                str(exe),
                "",
                "LƯU Ý:",
                "- Copy nguyên folder 'STT AI Editor', không copy riêng file .exe.",
                "- Nếu Windows hỏi bảo mật, chọn More info > Run anyway.",
                "- Không xoá folder _internal.",
                "- Project mặc định: D:\\STT Projects\\Wedding_Test_001",
                "",
                "PREWEDDING:",
                "- Trong app dùng Run Full Prewedding Pipeline.",
                "- Sau đó qua Premiere panel > Refresh Latest XML > Import Latest XML.",
                "",
            ]),
            encoding="utf-8",
        )

        run_bat = release_dir / "Run_STT_AI_Editor.bat"
        run_bat.write_text(
            f'@echo off\ncd /d "{app_release_dir}"\nstart "" "{exe}"\n',
            encoding="utf-8",
        )

        open_app_bat = release_dir / "Open_App_Folder.bat"
        open_app_bat.write_text(
            f'@echo off\nstart "" "{app_release_dir}"\n',
            encoding="utf-8",
        )

        return {
            "readme": str(readme),
            "run_bat": str(run_bat),
            "open_app_bat": str(open_app_bat),
        }

    def git_status(self) -> dict[str, Any]:
        git_dir = self.repo_root / ".git"
        if not git_dir.exists():
            return {
                "ok": False,
                "error": "Not a git repo",
            }

        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            shell=False,
        )

        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "short": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "clean": proc.returncode == 0 and not proc.stdout.strip(),
            "note": "Không commit dist/build/releases/*.spec.",
        }

    @staticmethod
    def git_clean_hint(git_status: Any) -> str:
        if not isinstance(git_status, dict):
            return "unknown"
        if git_status.get("clean"):
            return "git clean"
        short = str(git_status.get("short") or "").strip()
        if not short:
            return "git status unavailable"
        return "git has changes - nhớ không commit dist/build/releases/*.spec"

    @staticmethod
    def zip_release(release_dir: Path, package_zip: Path) -> dict[str, Any]:
        if package_zip.exists():
            package_zip.unlink()

        with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for p in release_dir.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(release_dir.parent))

        return {
            "zip": str(package_zip),
            "size_bytes": package_zip.stat().st_size,
            "size_gb": round(package_zip.stat().st_size / (1024 ** 3), 3),
        }

    @staticmethod
    def render_text(state: dict[str, Any]) -> str:
        lines = [
            "STT AI Editor - Release Package Summary",
            "=" * 72,
            f"OK: {state.get('ok')}",
            f"Version: {state.get('version')}",
            f"Release dir: {state.get('release_dir')}",
            f"ZIP: {state.get('zip')}",
            "",
            "Steps:",
        ]

        for step in state.get("steps", []):
            status = "OK" if step.get("ok") else "ERROR"
            lines.append(f"- {status} | {step.get('name')}")

        if state.get("errors"):
            lines += ["", "Errors:"]
            for err in state.get("errors", []):
                lines.append(f"- {err.get('step')}: {err.get('error')}")

        lines += [
            "",
            "Git status:",
            str((state.get("git_status") or {}).get("short") or "clean/none"),
            "",
            "Important:",
            "- Không commit dist/",
            "- Không commit build/",
            "- Không commit releases/",
            "- Không commit *.spec",
        ]

        return "\n".join(lines)

    @staticmethod
    def render_html(state: dict[str, Any]) -> str:
        import html

        ok = html.escape(str(state.get("ok")))
        version = html.escape(str(state.get("version")))
        release_dir = html.escape(str(state.get("release_dir")))
        zip_path = html.escape(str(state.get("zip")))
        git_short = html.escape(str((state.get("git_status") or {}).get("short") or "clean/none"))

        step_rows = []
        for step in state.get("steps", []):
            status = "OK" if step.get("ok") else "ERROR"
            step_rows.append(
                "<tr>"
                f"<td>{html.escape(status)}</td>"
                f"<td>{html.escape(str(step.get('name')))}</td>"
                f"<td>{html.escape(str(step.get('error') or ''))}</td>"
                "</tr>"
            )

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT AI Editor Release Package</title>
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
  <div class="badge">Module 053</div>
  <h1>STT AI Editor Release Package</h1>
  <p>OK: <b>{ok}</b></p>
  <p>Version: <b>{version}</b></p>
  <h2>Release folder</h2>
  <code>{release_dir}</code>
  <h2>ZIP</h2>
  <code>{zip_path}</code>
  <h2>Steps</h2>
  <table>
    <tr><th>Status</th><th>Step</th><th>Error</th></tr>
    {''.join(step_rows)}
  </table>
  <h2>Git status</h2>
  <code>{git_short}</code>
  <p>Không commit dist/, build/, releases/, *.spec.</p>
</div>
</body>
</html>
'''


def create_release_package(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    repo_root: str | Path | None = None,
    version: str = RELEASE_VERSION,
    build_first: bool = False,
    run_doctor: bool = True,
    open_folder: bool = True,
) -> dict[str, Any]:
    return STTReleasePackager(project_root=project_root, repo_root=repo_root).package(
        version=version,
        build_first=build_first,
        run_doctor=run_doctor,
        open_folder=open_folder,
    )
