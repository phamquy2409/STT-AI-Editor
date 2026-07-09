from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_premiere_bridge_patch_applied"


def apply_premiere_bridge_patch(window_class) -> None:
    # Module 037.
    # Adds a Premiere Bridge button to the production GUI.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(250, lambda: _install_premiere_bridge_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_premiere_bridge_ui(window) -> None:
    if getattr(window, "_stt_premiere_bridge_ui_installed", False):
        return

    try:
        window._stt_premiere_bridge_ui_installed = True

        btn = QPushButton("Premiere Bridge Package")
        btn.setObjectName("sttProductionButton_normal_PremiereBridgePackage")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _run_premiere_bridge(window))

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(btn)
            _log(window, "PREMIERE BRIDGE BUTTON LOADED")
            return

        # Fallback: create small panel if Module 036 panel is not present.
        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            box = QGroupBox("Premiere Bridge")
            layout = QVBoxLayout(box)
            layout.addWidget(btn)
            root_layout.insertWidget(0, box)
            _log(window, "PREMIERE BRIDGE PANEL LOADED")

    except Exception:
        _log(window, "PREMIERE BRIDGE PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_premiere_bridge(window) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.premiere_bridge import export_premiere_bridge

        result = export_premiere_bridge(project_root=project_root, open_folder=True)

        _log(window, "")
        _log(window, "PREMIERE BRIDGE PACKAGE CREATED")
        _log(window, f"Folder: {result['package_dir']}")
        _log(window, f"XML: {result['xml']}")

        QMessageBox.information(
            window,
            "Premiere Bridge",
            "Đã tạo Premiere Bridge package.\n\n"
            "Folder đã mở.\n"
            "Trong Premiere: File > Import > chọn 01_STT_AI_Premiere_Import.xml",
        )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREMIERE BRIDGE ERROR")
        _log(window, msg)
        QMessageBox.critical(window, "Premiere Bridge Error", msg[-4000:])


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
