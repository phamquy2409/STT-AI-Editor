
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "STT AI Editor"


def run(cmd: list[str], cwd: Path) -> None:
    print()
    print("RUN:")
    print(" ".join(cmd))
    print("-" * 80)
    subprocess.run(cmd, cwd=str(cwd), check=True)


def ensure_pyinstaller(repo_root: Path) -> None:
    try:
        import PyInstaller  # noqa: F401
        print("PyInstaller found.")
        return
    except Exception:
        pass

    print("PyInstaller is not installed.")
    print("Installing PyInstaller into current venv...")
    run([sys.executable, "-m", "pip", "install", "pyinstaller"], cwd=repo_root)


def add_data_arg(src: Path, dst: str) -> str:
    return f"{src}{os.pathsep}{dst}"


def build_exe(clean: bool = True) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    entry = repo_root / "scripts" / "run_gui.py"
    live_script = repo_root / "scripts" / "run_live_manual_review.py"

    if not entry.exists():
        raise FileNotFoundError(f"Missing GUI entry: {entry}")

    if not live_script.exists():
        raise FileNotFoundError(f"Missing live review script: {live_script}")

    ensure_pyinstaller(repo_root)

    if clean:
        for folder in [repo_root / "build", repo_root / "dist"]:
            if folder.exists():
                print(f"Removing: {folder}")
                shutil.rmtree(folder, ignore_errors=True)

        for spec in repo_root.glob("*.spec"):
            if spec.name.startswith("STT AI Editor"):
                print(f"Removing spec: {spec}")
                spec.unlink(missing_ok=True)

    hidden_imports = [
        "cv2",
        "numpy",
        "sqlalchemy",
        "ffmpeg",
        "core.gui",
        "core.gui.exe_live_patch",
        "core.gui.production_patch",
        "core.gui.premiere_bridge_patch",
        "core.gui.premiere_xml_validator_patch",
        "core.project",
        "core.pipeline",
        "core.pipeline_v2",
        "core.wedding_scene",
        "core.story_v2",
        "core.duplicate_remover",
        "core.feedback_learning",
        "core.xml_options",
        "core.manual_review",
        "core.manual_live",
        "core.manual_live.live_review_server",
        "core.manual_export",
        "core.exporter",
        "core.review",
        "core.project_presets",
        "core.export_cleaner",
        "core.app_health",
        "core.app_health.health",
        "core.premiere_bridge",
        "core.premiere_bridge.bridge",
        "core.premiere_bridge.validator",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        APP_NAME,
        "--add-data",
        add_data_arg(live_script, "scripts"),
        "--collect-all",
        "PySide6",
    ]

    for item in hidden_imports:
        cmd += ["--hidden-import", item]

    cmd.append(str(entry))

    run(cmd, cwd=repo_root)

    exe_path = repo_root / "dist" / APP_NAME / f"{APP_NAME}.exe"
    bundled_live_script = repo_root / "dist" / APP_NAME / "_internal" / "scripts" / "run_live_manual_review.py"

    print()
    print("=" * 80)
    print("BUILD FINISHED")
    print("=" * 80)

    if exe_path.exists():
        print("EXE:")
        print(exe_path)
        print()

        if bundled_live_script.exists():
            print("Live Review script bundled OK:")
            print(bundled_live_script)
        else:
            print("WARNING: Live Review script missing, but Module 034C can run live server in-process:")
            print(bundled_live_script)

        print()
        print("Run test:")
        print(f'& "{exe_path}"')
        print()
        print("Folder to copy to another Windows PC:")
        print(exe_path.parent)
        os.startfile(exe_path.parent)
    else:
        print("Build finished but EXE was not found at expected path:")
        print(exe_path)


def main() -> None:
    clean = "--no-clean" not in sys.argv
    build_exe(clean=clean)


if __name__ == "__main__":
    main()
