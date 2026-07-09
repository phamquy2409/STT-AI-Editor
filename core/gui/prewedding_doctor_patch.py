
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_prewedding_doctor_patch_applied"


def apply_prewedding_doctor_patch(window_class) -> None:
    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1550, lambda: _install_doctor_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_doctor_ui(window) -> None:
    if getattr(window, "_stt_prewedding_doctor_ui_installed", False):
        return

    try:
        window._stt_prewedding_doctor_ui_installed = True

        btn = QPushButton("Check Prewedding Pipeline")
        btn.setObjectName("sttProductionButton_CheckPreweddingPipeline")
        btn.setMinimumHeight(34)
        btn.clicked.connect(lambda: _run_doctor(window, show_popup=True))

        box = QGroupBox("Prewedding Pipeline Doctor")
        box.setObjectName("sttPreweddingDoctorPanel")
        layout = QVBoxLayout(box)
        layout.addWidget(btn)

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().insertWidget(1, box)
            _log(window, "PREWEDDING PIPELINE DOCTOR UI LOADED")
            return

        central = window.centralWidget()
        if central is not None and central.layout() is not None:
            central.layout().insertWidget(0, box)
            _log(window, "PREWEDDING PIPELINE DOCTOR PANEL LOADED")

    except Exception:
        _log(window, "PREWEDDING PIPELINE DOCTOR PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_doctor(window, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.prewedding_doctor import check_prewedding_pipeline

        result = check_prewedding_pipeline(
            project_root=project_root,
            open_folder=True,
        )

        _log(window, "")
        _log(window, "PREWEDDING PIPELINE DOCTOR DONE")
        _log(window, f"Ready pipeline: {result['ready_for_pipeline']}")
        _log(window, f"Ready XML: {result['ready_for_xml']}")
        _log(window, f"Ready Premiere: {result['ready_for_premiere']}")
        _log(window, f"Missing modules: {result['missing_modules']}")
        _log(window, f"Report: {result['report_dir']}")

        if show_popup:
            QMessageBox.information(
                window,
                "Prewedding Pipeline Doctor",
                "Đã kiểm tra pipeline.\n\n"
                f"Ready pipeline: {result['ready_for_pipeline']}\n"
                f"Ready XML: {result['ready_for_xml']}\n"
                f"Ready Premiere: {result['ready_for_premiere']}\n\n"
                "Mở report HTML để xem chi tiết.",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREWEDDING PIPELINE DOCTOR ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Prewedding Pipeline Doctor Error", msg[-4000:])


def _get_project_root_from_window(window) -> Path:
    edit = getattr(window, "project_edit", None)
    if edit is not None:
        text = edit.text().strip()
        if text:
            return Path(text)
    return Path("D:/STT Projects/Wedding_Test_001")


def _log(window, message: str) -> None:
    try:
        if hasattr(window, "append_log") and callable(window.append_log):
            window.append_log(str(message))
            return
    except Exception:
        pass
    print(message)
