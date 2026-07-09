
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_prewedding_xml_patch_applied"


def apply_prewedding_xml_patch(window_class) -> None:
    # Module 049.
    # Adds Prewedding XML Exporter to GUI.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1350, lambda: _install_prewedding_xml_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_prewedding_xml_ui(window) -> None:
    if getattr(window, "_stt_prewedding_xml_ui_installed", False):
        return

    try:
        window._stt_prewedding_xml_ui_installed = True

        from core.prewedding_xml import PREWEDDING_XML_PRESETS

        combo = QComboBox()
        combo.setObjectName("sttPreweddingXMLPresetCombo")
        combo.addItem("auto")
        for preset in sorted(PREWEDDING_XML_PRESETS):
            combo.addItem(preset)

        btn = QPushButton("Export Prewedding XML")
        btn.setObjectName("sttProductionButton_primary_ExportPreweddingXML")
        btn.setMinimumHeight(34)
        btn.clicked.connect(lambda: _export_xml(window, combo.currentText(), show_popup=True))

        box = QGroupBox("Prewedding XML Export")
        box.setObjectName("sttPreweddingXMLExportPanel")
        layout = QVBoxLayout(box)
        layout.addWidget(combo)
        layout.addWidget(btn)

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(box)
            _log(window, "PREWEDDING XML EXPORT UI LOADED")
            return

        central = window.centralWidget()
        if central is not None and central.layout() is not None:
            central.layout().insertWidget(0, box)
            _log(window, "PREWEDDING XML EXPORT PANEL LOADED")

    except Exception:
        _log(window, "PREWEDDING XML PATCH ERROR")
        _log(window, traceback.format_exc())


def _export_xml(window, preset_text: str, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)
        preset = None if preset_text == "auto" else preset_text

        from core.prewedding_xml import export_prewedding_xml

        result = export_prewedding_xml(
            project_root=project_root,
            preset=preset,
            open_folder=True,
        )

        _log(window, "")
        _log(window, "PREWEDDING XML EXPORTED")
        _log(window, f"Preset: {result['preset']}")
        _log(window, f"XML: {result['xml']}")
        _log(window, f"Duration: {result['duration']}")
        _log(window, f"Report: {result['report_dir']}")

        if show_popup:
            QMessageBox.information(
                window,
                "Export Prewedding XML",
                "Đã xuất XML prewedding cho Premiere.\n\n"
                f"Preset: {result['preset']}\n"
                f"Duration: {result['duration']}s\n\n"
                "Qua Premiere panel bấm Refresh Latest XML rồi Import.",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREWEDDING XML EXPORT ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Prewedding XML Export Error", msg[-4000:])


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
