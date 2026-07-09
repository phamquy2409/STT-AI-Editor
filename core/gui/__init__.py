from .simple_gui import STTAIEditorWindow, run_gui

try:
    from .exe_live_patch import apply_live_server_patch
    apply_live_server_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI exe_live_patch skipped: {exc!r}")

try:
    from .production_patch import apply_production_gui_patch
    apply_production_gui_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI production_patch skipped: {exc!r}")

try:
    from .prewedding_pipeline_patch import apply_prewedding_pipeline_patch
    apply_prewedding_pipeline_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding_pipeline_patch skipped: {exc!r}")

try:
    from .prewedding_doctor_patch import apply_prewedding_doctor_patch
    apply_prewedding_doctor_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding_doctor_patch skipped: {exc!r}")

try:
    from .release_packager_patch import apply_release_packager_patch
    apply_release_packager_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI release_packager_patch skipped: {exc!r}")

try:
    from .project_command_center_patch import apply_project_command_center_patch
    apply_project_command_center_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI project_command_center_patch skipped: {exc!r}")

try:
    from .music_placeholder_patch import apply_music_placeholder_patch
    apply_music_placeholder_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI music_placeholder_patch skipped: {exc!r}")

try:
    from .pipeline_snapshot_patch import apply_pipeline_snapshot_patch
    apply_pipeline_snapshot_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI pipeline_snapshot_patch skipped: {exc!r}")

try:
    from .prewedding_batch_plan_patch import apply_prewedding_batch_plan_patch
    apply_prewedding_batch_plan_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding_batch_plan_patch skipped: {exc!r}")

try:
    from .premiere_relink_helper_patch import apply_premiere_relink_helper_patch
    apply_premiere_relink_helper_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere_relink_helper_patch skipped: {exc!r}")

try:
    from .music_beat_plan_patch import apply_music_beat_plan_patch
    apply_music_beat_plan_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI music_beat_plan_patch skipped: {exc!r}")

try:
    from .review_package_patch import apply_review_package_patch
    apply_review_package_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI review_package_patch skipped: {exc!r}")

try:
    from .workflow_templates_patch import apply_workflow_templates_patch
    apply_workflow_templates_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI workflow_templates_patch skipped: {exc!r}")

try:
    from .master_dashboard_patch import apply_master_dashboard_patch
    apply_master_dashboard_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI master_dashboard_patch skipped: {exc!r}")

try:
    from .music_candidate_library_patch import apply_music_candidate_library_patch
    apply_music_candidate_library_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI music_candidate_library_patch skipped: {exc!r}")

try:
    from .sfx_placeholder_manager_patch import apply_sfx_placeholder_manager_patch
    apply_sfx_placeholder_manager_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI sfx_placeholder_manager_patch skipped: {exc!r}")

try:
    from .audio_cue_planner_patch import apply_audio_cue_planner_patch
    apply_audio_cue_planner_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI audio_cue_planner_patch skipped: {exc!r}")

try:
    from .final_replace_checker_patch import apply_final_replace_checker_patch
    apply_final_replace_checker_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI final_replace_checker_patch skipped: {exc!r}")

try:
    from .source_media_audit_patch import apply_source_media_audit_patch
    apply_source_media_audit_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI source_media_audit_patch skipped: {exc!r}")

try:
    from .timeline_qc_patch import apply_timeline_qc_patch
    apply_timeline_qc_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI timeline_qc_patch skipped: {exc!r}")

try:
    from .delivery_handoff_patch import apply_delivery_handoff_patch
    apply_delivery_handoff_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI delivery_handoff_patch skipped: {exc!r}")

try:
    from .production_launcher_patch import apply_production_launcher_patch
    apply_production_launcher_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI production_launcher_patch skipped: {exc!r}")

try:
    from .client_feedback_collector_patch import apply_client_feedback_collector_patch
    apply_client_feedback_collector_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI client_feedback_collector_patch skipped: {exc!r}")

try:
    from .client_select_sync_patch import apply_client_select_sync_patch
    apply_client_select_sync_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI client_select_sync_patch skipped: {exc!r}")

try:
    from .delivery_checklist_patch import apply_delivery_checklist_patch
    apply_delivery_checklist_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI delivery_checklist_patch skipped: {exc!r}")

try:
    from .export_version_namer_patch import apply_export_version_namer_patch
    apply_export_version_namer_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI export_version_namer_patch skipped: {exc!r}")

try:
    from .archive_cleaner_plan_patch import apply_archive_cleaner_plan_patch
    apply_archive_cleaner_plan_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI archive_cleaner_plan_patch skipped: {exc!r}")

try:
    from .backup_verify_patch import apply_backup_verify_patch
    apply_backup_verify_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI backup_verify_patch skipped: {exc!r}")

try:
    from .project_version_tracker_patch import apply_project_version_tracker_patch
    apply_project_version_tracker_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI project_version_tracker_patch skipped: {exc!r}")

try:
    from .smart_folder_organizer_patch import apply_smart_folder_organizer_patch
    apply_smart_folder_organizer_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI smart_folder_organizer_patch skipped: {exc!r}")

try:
    from .app_log_collector_patch import apply_app_log_collector_patch
    apply_app_log_collector_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI app_log_collector_patch skipped: {exc!r}")

try:
    from .final_production_dashboard_patch import apply_final_production_dashboard_patch
    apply_final_production_dashboard_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI final_production_dashboard_patch skipped: {exc!r}")

try:
    from .compact_scroll_patch import apply_compact_scroll_patch
    apply_compact_scroll_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI compact_scroll_patch skipped: {exc!r}")

__all__ = ["STTAIEditorWindow", "run_gui"]
