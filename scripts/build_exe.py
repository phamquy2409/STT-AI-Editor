from __future__ import annotations
import os, shutil, subprocess, sys
from pathlib import Path
APP_NAME = "STT AI Editor"
def run(cmd: list[str], cwd: Path) -> None:
    print(); print("RUN:"); print(" ".join(cmd)); print("-"*80); subprocess.run(cmd, cwd=str(cwd), check=True)
def ensure_pyinstaller(repo_root: Path) -> None:
    try:
        import PyInstaller  # noqa
        return
    except Exception:
        run([sys.executable, "-m", "pip", "install", "pyinstaller"], cwd=repo_root)
def add_data_arg(src: Path, dst: str) -> str:
    return f"{src}{os.pathsep}{dst}"
def build_exe(clean: bool = True) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    entry = repo_root / "scripts" / "run_gui.py"
    live_script = repo_root / "scripts" / "run_live_manual_review.py"
    if clean:
        for folder in [repo_root / "build", repo_root / "dist"]:
            if folder.exists(): shutil.rmtree(folder, ignore_errors=True)
        for spec in repo_root.glob("*.spec"):
            if spec.name.startswith("STT AI Editor"): spec.unlink(missing_ok=True)
    ensure_pyinstaller(repo_root)
    hidden_imports = [
        'cv2',
        'numpy',
        'sqlalchemy',
        'ffmpeg',
        'core.gui',
        'core.gui.prewedding_pipeline_patch',
        'core.prewedding_pipeline',
        'core.prewedding_pipeline.runner',
        'core.gui.prewedding_doctor_patch',
        'core.prewedding_doctor',
        'core.prewedding_doctor.doctor',
        'core.gui.release_packager_patch',
        'core.release_packager',
        'core.release_packager.packager',
        'core.gui.music_placeholder_patch',
        'core.music_placeholder',
        'core.music_placeholder.manager',
        'core.gui.music_candidate_library_patch',
        'core.music_library',
        'core.music_library.library',
        'core.gui.sfx_placeholder_manager_patch',
        'core.sfx_placeholder',
        'core.sfx_placeholder.manager',
        'core.gui.audio_cue_planner_patch',
        'core.audio_cue_planner',
        'core.audio_cue_planner.planner',
        'core.gui.final_replace_checker_patch',
        'core.final_replace_checker',
        'core.final_replace_checker.checker',
        'core.gui.source_media_audit_patch',
        'core.source_media_audit',
        'core.source_media_audit.audit',
        'core.gui.timeline_qc_patch',
        'core.timeline_qc',
        'core.timeline_qc.qc',
        'core.gui.delivery_handoff_patch',
        'core.delivery_handoff',
        'core.delivery_handoff.handoff',
        'core.gui.production_launcher_patch',
        'core.production_launcher',
        'core.production_launcher.launcher',
        'core.gui.compact_scroll_patch',
        'core.manual_live',
        'core.manual_live.live_review_server',
        'core.gui.client_feedback_collector_patch',
        'core.client_feedback',
        'core.client_feedback.collector',
        'core.gui.client_select_sync_patch',
        'core.client_select_sync',
        'core.client_select_sync.sync',
        'core.gui.delivery_checklist_patch',
        'core.delivery_checklist',
        'core.delivery_checklist.checklist',
        'core.gui.export_version_namer_patch',
        'core.export_version_namer',
        'core.export_version_namer.namer',
        'core.gui.archive_cleaner_plan_patch',
        'core.archive_cleaner_plan',
        'core.archive_cleaner_plan.cleaner',
        'core.gui.backup_verify_patch',
        'core.backup_verify',
        'core.backup_verify.verify',
        'core.gui.project_version_tracker_patch',
        'core.project_version_tracker',
        'core.project_version_tracker.tracker',
        'core.gui.smart_folder_organizer_patch',
        'core.smart_folder_organizer',
        'core.smart_folder_organizer.organizer',
        'core.gui.app_log_collector_patch',
        'core.app_log_collector',
        'core.app_log_collector.collector',
        'core.gui.final_production_dashboard_patch',
        'core.final_production_dashboard',
        'core.final_production_dashboard.dashboard'
    ]
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed", "--name", APP_NAME, "--add-data", add_data_arg(live_script, "scripts"), "--collect-all", "PySide6"]
    for item in hidden_imports:
        cmd += ["--hidden-import", item]
    cmd.append(str(entry))
    run(cmd, cwd=repo_root)
    exe_path = repo_root / "dist" / APP_NAME / f"{APP_NAME}.exe"
    print("EXE:", exe_path)
    if exe_path.exists(): os.startfile(exe_path.parent)
def main() -> None:
    build_exe(clean="--no-clean" not in sys.argv)
if __name__ == "__main__":
    main()
