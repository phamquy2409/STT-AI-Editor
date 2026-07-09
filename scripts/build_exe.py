
from __future__ import annotations
import os, shutil, subprocess, sys
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
        import PyInstaller  # noqa
        print("PyInstaller found.")
        return
    except Exception:
        pass
    print("PyInstaller is not installed.")
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
                shutil.rmtree(folder, ignore_errors=True)
        for spec in repo_root.glob("*.spec"):
            if spec.name.startswith("STT AI Editor"):
                spec.unlink(missing_ok=True)

    hidden_imports = [
        "cv2", "numpy", "sqlalchemy", "ffmpeg",
        "core.gui",
        "core.gui.music_placeholder_patch",
        "core.music_placeholder", "core.music_placeholder.manager",
        "core.gui.project_command_center_patch", "core.project_command_center", "core.project_command_center.center",
        "core.gui.pipeline_snapshot_patch", "core.pipeline_snapshot", "core.pipeline_snapshot.snapshot",
        "core.gui.prewedding_batch_plan_patch", "core.prewedding_batch", "core.prewedding_batch.batch",
        "core.gui.premiere_relink_helper_patch", "core.premiere_relink_helper", "core.premiere_relink_helper.relink",
        "core.gui.music_beat_plan_patch", "core.music_beat_plan", "core.music_beat_plan.beat_plan",
        "core.gui.review_package_patch", "core.review_package", "core.review_package.package",
        "core.gui.workflow_templates_patch", "core.workflow_templates", "core.workflow_templates.templates",
        "core.gui.master_dashboard_patch", "core.master_dashboard", "core.master_dashboard.dashboard",
        "core.gui.prewedding_pipeline_patch", "core.prewedding_pipeline", "core.prewedding_pipeline.runner",
        "core.gui.prewedding_doctor_patch", "core.prewedding_doctor", "core.prewedding_doctor.doctor",
        "core.gui.release_packager_patch", "core.release_packager", "core.release_packager.packager",
        "core.gui.prewedding_xml_patch", "core.prewedding_xml", "core.prewedding_xml.exporter",
        "core.gui.prewedding_refiner_patch", "core.prewedding_refiner", "core.prewedding_refiner.refiner",
        "core.gui.prewedding_roughcut_patch", "core.prewedding_roughcut", "core.prewedding_roughcut.builder",
        "core.gui.prewedding_selector_patch", "core.prewedding_selector", "core.prewedding_selector.selector",
        "core.gui.ai_shot_scorer_patch", "core.ai_shot_scorer", "core.ai_shot_scorer.scorer",
        "core.gui.exe_live_patch", "core.gui.production_patch", "core.gui.compact_scroll_patch",
        "core.manual_live", "core.manual_live.live_review_server",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", APP_NAME,
        "--add-data", add_data_arg(live_script, "scripts"),
        "--collect-all", "PySide6",
    ]
    for item in hidden_imports:
        cmd += ["--hidden-import", item]
    cmd.append(str(entry))
    run(cmd, cwd=repo_root)

    exe_path = repo_root / "dist" / APP_NAME / f"{APP_NAME}.exe"
    print()
    print("=" * 80)
    print("BUILD FINISHED")
    print("=" * 80)
    print("EXE:", exe_path)
    if exe_path.exists():
        os.startfile(exe_path.parent)

def main() -> None:
    build_exe(clean="--no-clean" not in sys.argv)

if __name__ == "__main__":
    main()
