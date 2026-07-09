
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_premiere_panel_sync_patch_applied"


def apply_premiere_panel_sync_patch(window_class) -> None:
    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(850, lambda: _install_panel_sync_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_panel_sync_ui(window) -> None:
    if getattr(window, "_stt_premiere_panel_sync_ui_installed", False):
        return

    try:
        window._stt_premiere_panel_sync_ui_installed = True

        btn = QPushButton("Sync Premiere Panel")
        btn.setObjectName("sttProductionButton_primary_SyncPremierePanel")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _sync_panel(window, show_popup=True))

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(btn)
            _log(window, "PREMIERE PANEL SYNC BUTTON LOADED")
            return

        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            box = QGroupBox("Premiere Panel Sync")
            layout = QVBoxLayout(box)
            layout.addWidget(btn)
            root_layout.insertWidget(0, box)
            _log(window, "PREMIERE PANEL SYNC PANEL LOADED")

    except Exception:
        _log(window, "PREMIERE PANEL SYNC PATCH ERROR")
        _log(window, traceback.format_exc())


def _sync_panel(window, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.premiere_bridge import sync_premiere_panel

        result = sync_premiere_panel(
            project_root=project_root,
            validate_xml=True,
            open_folder=True,
        )

        _log(window, "")
        _log(window, "PREMIERE PANEL SYNC DONE")
        _log(window, f"Status: {result['status']}")
        _log(window, f"XML: {result['xml']}")
        _log(window, f"Pointer: {result['pointer_txt']}")
        _log(window, f"Report: {result['report_dir']}")

        if show_popup:
            if result.get("status") == "fail":
                QMessageBox.critical(
                    window,
                    "Sync Premiere Panel",
                    "Sync có lỗi. Xem report vừa mở.",
                )
            elif result.get("status") == "warn":
                QMessageBox.warning(
                    window,
                    "Sync Premiere Panel",
                    "Sync xong nhưng có cảnh báo. Xem report vừa mở.",
                )
            else:
                QMessageBox.information(
                    window,
                    "Sync Premiere Panel",
                    "Sync OK.\n\nQua Premiere panel bấm Refresh Latest XML rồi Import.",
                )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREMIERE PANEL SYNC ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Premiere Panel Sync Error", msg[-4000:])


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
