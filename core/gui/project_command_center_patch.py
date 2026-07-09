
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_project_command_center_patch_applied"


def apply_project_command_center_patch(window_class) -> None:
    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1700, lambda: _install_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_ui(window) -> None:
    if getattr(window, "_stt_project_command_center_ui_installed", False):
        return

    try:
        window._stt_project_command_center_ui_installed = True

        btn = QPushButton("Create Project Command Center")
        btn.setObjectName("sttButton_project_command_center")
        btn.setMinimumHeight(34)
        btn.clicked.connect(lambda: _run(window, show_popup=True))

        box = QGroupBox("Project Command Center")
        box.setObjectName("sttPanel_project_command_center")
        layout = QVBoxLayout(box)
        layout.addWidget(btn)

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().insertWidget(0, box)
            _log(window, "PROJECT COMMAND CENTER UI LOADED")
            return

        central = window.centralWidget()
        if central is not None and central.layout() is not None:
            central.layout().insertWidget(0, box)
            _log(window, "PROJECT COMMAND CENTER PANEL LOADED")

    except Exception:
        _log(window, "PROJECT COMMAND CENTER PATCH ERROR")
        _log(window, traceback.format_exc())


def _run(window, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.project_command_center import create_project_command_center

        result = create_project_command_center(
            project_root=project_root,
            open_folder=True,
        )

        _log(window, "")
        _log(window, "PROJECT COMMAND CENTER DONE")
        _log(window, f"OK: {result.get('ok')}")
        _log(window, f"Output: {result.get('output_dir')}")
        _log(window, f"BAT dir: {result.get('bat_dir')}")

        if show_popup:
            QMessageBox.information(
                window,
                "Project Command Center",
                "Đã tạo Project Command Center.\n\n"
                f"BAT files: {result.get('command_count')}\n"
                f"Folder:\n{result.get('output_dir')}",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PROJECT COMMAND CENTER ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Project Command Center Error", msg[-4000:])


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
