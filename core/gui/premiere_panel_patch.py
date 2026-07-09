
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_premiere_panel_patch_applied"


def apply_premiere_panel_patch(window_class) -> None:
    # Module 041.
    # Adds Create Premiere Panel button to GUI.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(650, lambda: _install_panel_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_panel_ui(window) -> None:
    if getattr(window, "_stt_premiere_panel_ui_installed", False):
        return

    try:
        window._stt_premiere_panel_ui_installed = True

        btn = QPushButton("Create Premiere Panel")
        btn.setObjectName("sttProductionButton_normal_CreatePremierePanel")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _run_panel_creator(window))

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(btn)
            _log(window, "PREMIERE PANEL BUTTON LOADED")
            return

        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            box = QGroupBox("Premiere Panel")
            layout = QVBoxLayout(box)
            layout.addWidget(btn)
            root_layout.insertWidget(0, box)
            _log(window, "PREMIERE PANEL UI LOADED")

    except Exception:
        _log(window, "PREMIERE PANEL PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_panel_creator(window) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.premiere_bridge import create_premiere_panel

        result = create_premiere_panel(project_root=project_root, install_to_user_cep=True, open_folder=True)

        _log(window, "")
        _log(window, "PREMIERE PANEL STARTER CREATED")
        _log(window, f"Folder: {result['package_dir']}")
        _log(window, f"Installed to: {result.get('installed_to_user_cep')}")
        _log(window, f"XML pointer: {result['latest_xml_pointer']}")

        if result.get("installed_to_user_cep"):
            QMessageBox.information(
                window,
                "Create Premiere Panel",
                "Đã tạo và copy panel vào User CEP folder.\n\n"
                "Chạy ENABLE_CEP_DEBUG_MODE.bat nếu chưa chạy.\n"
                "Restart Premiere rồi mở:\n"
                "Window > Extensions > STT AI Editor",
            )
        else:
            QMessageBox.warning(
                window,
                "Create Premiere Panel",
                "Đã tạo panel package nhưng chưa copy được vào CEP folder.\n\n"
                "Mở folder vừa tạo và chạy:\n"
                "INSTALL_PANEL_TO_USER_CEP.bat",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREMIERE PANEL ERROR")
        _log(window, msg)
        QMessageBox.critical(window, "Premiere Panel Error", msg[-4000:])


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
