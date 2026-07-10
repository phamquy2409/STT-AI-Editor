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
        'core.manual_live',
        'core.manual_live.live_review_server',
        'core.gui.exe_live_patch',
        'core.gui.production_patch',
        'core.gui.premiere_bridge_patch',
        'core.gui.premiere_xml_validator_patch',
        'core.gui.premiere_jsx_helper_patch',
        'core.gui.premiere_script_installer_patch',
        'core.gui.premiere_panel_patch',
        'core.gui.premiere_pointer_patch',
        'core.gui.premiere_panel_sync_patch',
        'core.gui.style_profile_patch',
        'core.gui.ai_style_memory_patch',
        'core.gui.ai_shot_scorer_patch',
        'core.gui.prewedding_selector_patch',
        'core.gui.prewedding_roughcut_patch',
        'core.gui.prewedding_refiner_patch',
        'core.gui.prewedding_xml_patch',
        'core.gui.prewedding_pipeline_patch',
        'core.gui.prewedding_doctor_patch',
        'core.gui.release_packager_patch',
        'core.gui.project_command_center_patch',
        'core.gui.music_placeholder_patch',
        'core.gui.pipeline_snapshot_patch',
        'core.gui.prewedding_batch_plan_patch',
        'core.gui.premiere_relink_helper_patch',
        'core.gui.music_beat_plan_patch',
        'core.gui.review_package_patch',
        'core.gui.workflow_templates_patch',
        'core.gui.master_dashboard_patch',
        'core.gui.music_candidate_library_patch',
        'core.gui.sfx_placeholder_manager_patch',
        'core.gui.audio_cue_planner_patch',
        'core.gui.final_replace_checker_patch',
        'core.gui.source_media_audit_patch',
        'core.gui.timeline_qc_patch',
        'core.gui.delivery_handoff_patch',
        'core.gui.production_launcher_patch',
        'core.gui.client_feedback_collector_patch',
        'core.gui.client_select_sync_patch',
        'core.gui.delivery_checklist_patch',
        'core.gui.export_version_namer_patch',
        'core.gui.archive_cleaner_plan_patch',
        'core.gui.backup_verify_patch',
        'core.gui.project_version_tracker_patch',
        'core.gui.smart_folder_organizer_patch',
        'core.gui.app_log_collector_patch',
        'core.gui.final_production_dashboard_patch',
        'core.prewedding_pipeline',
        'core.prewedding_pipeline.runner',
        'core.prewedding_doctor',
        'core.prewedding_doctor.doctor',
        'core.release_packager',
        'core.release_packager.packager',
        'core.project_command_center',
        'core.project_command_center.center',
        'core.music_placeholder',
        'core.music_placeholder.manager',
        'core.pipeline_snapshot',
        'core.pipeline_snapshot.snapshot',
        'core.prewedding_batch',
        'core.prewedding_batch.batch',
        'core.premiere_relink_helper',
        'core.premiere_relink_helper.relink',
        'core.music_beat_plan',
        'core.music_beat_plan.beat_plan',
        'core.review_package',
        'core.review_package.package',
        'core.workflow_templates',
        'core.workflow_templates.templates',
        'core.master_dashboard',
        'core.master_dashboard.dashboard',
        'core.music_library',
        'core.music_library.library',
        'core.sfx_placeholder',
        'core.sfx_placeholder.manager',
        'core.audio_cue_planner',
        'core.audio_cue_planner.planner',
        'core.final_replace_checker',
        'core.final_replace_checker.checker',
        'core.source_media_audit',
        'core.source_media_audit.audit',
        'core.timeline_qc',
        'core.timeline_qc.qc',
        'core.delivery_handoff',
        'core.delivery_handoff.handoff',
        'core.production_launcher',
        'core.production_launcher.launcher',
        'core.client_feedback',
        'core.client_feedback.collector',
        'core.client_select_sync',
        'core.client_select_sync.sync',
        'core.delivery_checklist',
        'core.delivery_checklist.checklist',
        'core.export_version_namer',
        'core.export_version_namer.namer',
        'core.archive_cleaner_plan',
        'core.archive_cleaner_plan.cleaner',
        'core.backup_verify',
        'core.backup_verify.verify',
        'core.project_version_tracker',
        'core.project_version_tracker.tracker',
        'core.smart_folder_organizer',
        'core.smart_folder_organizer.organizer',
        'core.app_log_collector',
        'core.app_log_collector.collector',
        'core.final_production_dashboard',
        'core.final_production_dashboard.dashboard',
        'core.gui.local_command_server_patch',
        'core.local_command_server',
        'core.local_command_server.server',
        'core.gui.premiere_panel_run_buttons_patch',
        'core.premiere_panel_run_buttons',
        'core.premiere_panel_run_buttons.panel',
        'core.gui.panel_command_bridge_patch',
        'core.panel_command_bridge',
        'core.panel_command_bridge.bridge',
        'core.gui.auto_xml_refresh_patch',
        'core.auto_xml_refresh',
        'core.auto_xml_refresh.refresh',
        'core.gui.auto_import_helper_patch',
        'core.auto_import_helper',
        'core.auto_import_helper.helper',
        'core.gui.panel_progress_status_patch',
        'core.panel_progress_status',
        'core.panel_progress_status.status',
        'core.gui.panel_source_folder_patch',
        'core.panel_source_folder',
        'core.panel_source_folder.source',
        'core.gui.panel_pipeline_presets_patch',
        'core.panel_pipeline_presets',
        'core.panel_pipeline_presets.presets',
        'core.gui.panel_error_reporter_patch',
        'core.panel_error_reporter',
        'core.panel_error_reporter.reporter',
        'core.gui.background_app_start_helper_patch',
        'core.background_app_start_helper',
        'core.background_app_start_helper.starter',
        'core.gui.compact_scroll_patch'
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
