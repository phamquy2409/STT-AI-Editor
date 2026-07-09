from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
    "releases",
}

EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tmp",
    ".log",
}


def should_skip(path: Path, repo_root: Path) -> bool:
    rel = path.relative_to(repo_root)

    for part in rel.parts:
        if part in EXCLUDE_DIR_NAMES:
            return True

    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True

    return False


def git_commit_hash(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo_root), text=True)
        return out.strip()
    except Exception:
        return "no-git"


def git_status(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(["git", "status", "--short"], cwd=str(repo_root), text=True)
        return out.strip()
    except Exception as exc:
        return f"git status error: {exc!r}"


def copy_project_settings(project_root: Path, staging: Path) -> list[str]:
    copied: list[str] = []
    dst = staging / "project_settings"
    dst.mkdir(parents=True, exist_ok=True)

    names = [
        "project.json",
        "manual_selection.json",
        "stt_feedback_profile.json",
        "stt_xml_export_settings.json",
        "stt_workflow_preset.json",
    ]

    for name in names:
        src = project_root / name
        if src.exists() and src.is_file():
            shutil.copy2(src, dst / name)
            copied.append(str(src))

    return copied


def create_stable_backup() -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    commit = git_commit_hash(repo_root)

    releases_dir = repo_root / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)

    staging = releases_dir / f"STT_AI_Editor_stable_{stamp}"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    code_dst = staging / "source_code"
    code_dst.mkdir(parents=True, exist_ok=True)

    copied_files = 0

    for path in repo_root.rglob("*"):
        if path.is_dir():
            continue

        if should_skip(path, repo_root):
            continue

        rel = path.relative_to(repo_root)
        dst = code_dst / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        copied_files += 1

    project_copied = copy_project_settings(project_root, staging)

    exe_folder = repo_root / "dist" / "STT AI Editor"
    exe_copied = False

    if exe_folder.exists():
        exe_dst = staging / "windows_exe_onedir"
        shutil.copytree(exe_folder, exe_dst, dirs_exist_ok=True)
        exe_copied = True

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "repo_root": str(repo_root),
        "project_root": str(project_root),
        "git_commit": commit,
        "git_status": git_status(repo_root),
        "copied_source_files": copied_files,
        "project_settings_copied": project_copied,
        "exe_folder_copied": exe_copied,
        "note": "This backup excludes .git, .venv, build, dist source folder, releases, cache files. It does not include source wedding videos.",
    }

    manifest_path = staging / "STABLE_BACKUP_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = staging / "README_RESTORE.txt"
    readme.write_text(
        "\n".join(
            [
                "STT AI Editor - Stable Backup",
                "=" * 70,
                "",
                "This backup contains:",
                "- source_code: code snapshot",
                "- project_settings: project/profile/settings json files",
                "- windows_exe_onedir: EXE folder if it existed at backup time",
                "",
                "Restore source code:",
                "1. Copy source_code contents back into D:\\Projects\\STT-AI-Editor",
                "2. Create/activate .venv",
                "3. pip install required packages",
                "4. python scripts/run_gui.py",
                "",
                "Run EXE:",
                "Open windows_exe_onedir\\STT AI Editor.exe",
                "",
                "Important:",
                "Do not restore over a newer repo unless you intentionally want to roll back.",
            ]
        ),
        encoding="utf-8",
    )

    zip_path = releases_dir / f"STT_AI_Editor_stable_{stamp}_{commit}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in staging.rglob("*"):
            if file.is_file():
                z.write(file, file.relative_to(staging.parent))

    result = {
        "staging_dir": str(staging),
        "zip": str(zip_path),
        "manifest": str(manifest_path),
        "copied_source_files": copied_files,
        "exe_folder_copied": exe_copied,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    os.startfile(releases_dir)
    return result


def main() -> None:
    create_stable_backup()


if __name__ == "__main__":
    main()
