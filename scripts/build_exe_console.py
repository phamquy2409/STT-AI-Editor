from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "STT AI Editor Console"


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

    print("Installing PyInstaller...")
    run([sys.executable, "-m", "pip", "install", "pyinstaller"], cwd=repo_root)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    entry = repo_root / "scripts" / "run_gui.py"

    ensure_pyinstaller(repo_root)

    for folder in [repo_root / "build", repo_root / "dist"]:
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--console",
        "--name",
        APP_NAME,
        "--collect-all",
        "PySide6",
        "--hidden-import",
        "cv2",
        "--hidden-import",
        "numpy",
        "--hidden-import",
        "sqlalchemy",
        "--hidden-import",
        "ffmpeg",
        "--hidden-import",
        "core.gui",
        "--hidden-import",
        "core.pipeline_v2",
        "--hidden-import",
        "core.manual_live",
        "--hidden-import",
        "core.feedback_learning",
        "--hidden-import",
        "core.xml_options",
        str(entry),
    ]

    run(cmd, cwd=repo_root)

    exe_path = repo_root / "dist" / APP_NAME / f"{APP_NAME}.exe"
    print()
    print("Console EXE:")
    print(exe_path)


if __name__ == "__main__":
    main()
