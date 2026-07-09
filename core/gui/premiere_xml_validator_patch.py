
from __future__ import annotations

import os
import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_premiere_xml_validator_patch_applied"


def apply_premiere_xml_validator_patch(window_class) -> None:
    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(350, lambda: _install_xml_validator_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_xml_validator_ui(window) -> None:
    if getattr(window, "_stt_premiere_xml_validator_ui_installed", False):
        return

    try:
        window._stt_premiere_xml_validator_ui_installed = True

        btn = QPushButton("Check Premiere XML")
        btn.setObjectName("sttProductionButton_normal_CheckPremiereXML")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _run_xml_check(window))

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(btn)
            _log(window, "PREMIERE XML CHECK BUTTON LOADED")
            return

        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            box = QGroupBox("Premiere XML Check")
            layout = QVBoxLayout(box)
            layout.addWidget(btn)
            root_layout.insertWidget(0, box)
            _log(window, "PREMIERE XML CHECK PANEL LOADED")

    except Exception:
        _log(window, "PREMIERE XML CHECK PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_xml_check(window) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.premiere_bridge import PremiereBridgeExporter, PremiereXMLValidator

        xml = PremiereBridgeExporter(project_root).find_latest_xml()
        if not xml:
            QMessageBox.warning(
                window,
                "Check Premiere XML",
                "Không tìm thấy XML.\n\nBấm Export Latest Manual XML trước.",
            )
            return

        validator = PremiereXMLValidator(xml)
        result = validator.validate()
        reports = validator.write_reports(xml.parent)

        _log(window, "")
        _log(window, "PREMIERE XML VALIDATION DONE")
        _log(window, f"XML: {xml}")
        _log(window, f"Status: {result['status']}")
        _log(window, f"Errors: {len(result['errors'])}")
        _log(window, f"Warnings: {len(result['warnings'])}")
        _log(window, f"Report: {reports.get('html')}")

        try:
            html_report = reports.get("html")
            if html_report:
                os.startfile(html_report)
        except Exception:
            pass

        if result.get("errors"):
            QMessageBox.critical(
                window,
                "XML có lỗi",
                "XML có lỗi trước khi import Premiere.\n\nXem XML_VALIDATION_REPORT.html vừa mở.",
            )
        elif result.get("warnings"):
            QMessageBox.warning(
                window,
                "XML có cảnh báo",
                "XML dùng được nhưng có cảnh báo.\n\nXem XML_VALIDATION_REPORT.html vừa mở.",
            )
        else:
            QMessageBox.information(
                window,
                "XML OK",
                "XML kiểm tra OK. Có thể import vào Premiere.",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREMIERE XML CHECK ERROR")
        _log(window, msg)
        QMessageBox.critical(window, "Premiere XML Check Error", msg[-4000:])


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
