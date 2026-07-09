
from .simple_gui import STTAIEditorWindow, run_gui

try:
    from .exe_live_patch import apply_live_server_patch
    apply_live_server_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI live server patch skipped: {exc!r}")

try:
    from .production_patch import apply_production_gui_patch
    apply_production_gui_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI production patch skipped: {exc!r}")

try:
    from .premiere_bridge_patch import apply_premiere_bridge_patch
    apply_premiere_bridge_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere bridge patch skipped: {exc!r}")

try:
    from .premiere_xml_validator_patch import apply_premiere_xml_validator_patch
    apply_premiere_xml_validator_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere XML validator patch skipped: {exc!r}")

try:
    from .premiere_jsx_helper_patch import apply_premiere_jsx_helper_patch
    apply_premiere_jsx_helper_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere JSX helper patch skipped: {exc!r}")

try:
    from .premiere_script_installer_patch import apply_premiere_script_installer_patch
    apply_premiere_script_installer_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere script installer patch skipped: {exc!r}")

try:
    from .premiere_panel_patch import apply_premiere_panel_patch
    apply_premiere_panel_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere panel patch skipped: {exc!r}")

try:
    from .premiere_pointer_patch import apply_premiere_pointer_patch
    apply_premiere_pointer_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere pointer patch skipped: {exc!r}")

try:
    from .premiere_panel_sync_patch import apply_premiere_panel_sync_patch
    apply_premiere_panel_sync_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere panel sync patch skipped: {exc!r}")

try:
    from .style_profile_patch import apply_style_profile_patch
    apply_style_profile_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI style profile patch skipped: {exc!r}")

try:
    from .ai_style_memory_patch import apply_ai_style_memory_patch
    apply_ai_style_memory_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI AI style memory patch skipped: {exc!r}")

try:
    from .ai_shot_scorer_patch import apply_ai_shot_scorer_patch
    apply_ai_shot_scorer_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI AI shot scorer patch skipped: {exc!r}")

try:
    from .prewedding_selector_patch import apply_prewedding_selector_patch
    apply_prewedding_selector_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding selector patch skipped: {exc!r}")

try:
    from .prewedding_roughcut_patch import apply_prewedding_roughcut_patch
    apply_prewedding_roughcut_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding roughcut patch skipped: {exc!r}")

try:
    from .prewedding_refiner_patch import apply_prewedding_refiner_patch
    apply_prewedding_refiner_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding refiner patch skipped: {exc!r}")

try:
    from .prewedding_xml_patch import apply_prewedding_xml_patch
    apply_prewedding_xml_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding XML patch skipped: {exc!r}")

try:
    from .prewedding_pipeline_patch import apply_prewedding_pipeline_patch
    apply_prewedding_pipeline_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding pipeline patch skipped: {exc!r}")

try:
    from .prewedding_doctor_patch import apply_prewedding_doctor_patch
    apply_prewedding_doctor_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding doctor patch skipped: {exc!r}")

try:
    from .release_packager_patch import apply_release_packager_patch
    apply_release_packager_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI release packager patch skipped: {exc!r}")

try:
    from .project_command_center_patch import apply_project_command_center_patch
    apply_project_command_center_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI project command center patch skipped: {exc!r}")

try:
    from .pipeline_snapshot_patch import apply_pipeline_snapshot_patch
    apply_pipeline_snapshot_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI pipeline snapshot patch skipped: {exc!r}")

try:
    from .prewedding_batch_plan_patch import apply_prewedding_batch_plan_patch
    apply_prewedding_batch_plan_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI prewedding batch plan patch skipped: {exc!r}")

try:
    from .premiere_relink_helper_patch import apply_premiere_relink_helper_patch
    apply_premiere_relink_helper_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI premiere relink helper patch skipped: {exc!r}")

try:
    from .music_beat_plan_patch import apply_music_beat_plan_patch
    apply_music_beat_plan_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI music beat plan patch skipped: {exc!r}")

try:
    from .review_package_patch import apply_review_package_patch
    apply_review_package_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI review package patch skipped: {exc!r}")

try:
    from .workflow_templates_patch import apply_workflow_templates_patch
    apply_workflow_templates_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI workflow templates patch skipped: {exc!r}")

try:
    from .master_dashboard_patch import apply_master_dashboard_patch
    apply_master_dashboard_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI master dashboard patch skipped: {exc!r}")

try:
    from .compact_scroll_patch import apply_compact_scroll_patch
    apply_compact_scroll_patch(STTAIEditorWindow)
except Exception as exc:
    print(f"STT GUI compact scroll patch skipped: {exc!r}")

__all__ = ["STTAIEditorWindow", "run_gui"]
