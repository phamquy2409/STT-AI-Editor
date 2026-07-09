
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_premiere_script_installer_patch_applied"


def apply_premiere_script_installer_patch(window_class) -> None:
    # Module 040.
    # Adds Premiere Script Installer button to GUI.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(550, lambda: _install_script_installer_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_script_installer_ui(window) -> None:
    if getattr(window, "_stt_premiere_script_installer_ui_installed", False):
        return

    try:
        window._stt_premiere_script_installer_ui_installed = True

        btn = QPushButton("Install Premiere Script")
        btn.setObjectName("sttProductionButton_normal_InstallPremiereScript")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _run_installer(window))

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(btn)
            _log(window, "PREMIERE SCRIPT INSTALLER BUTTON LOADED")
            return

        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            box = QGroupBox("Premiere Script Installer")
            layout = QVBoxLayout(box)
            layout.addWidget(btn)
            root_layout.insertWidget(0, box)
            _log(window, "PREMIERE SCRIPT INSTALLER PANEL LOADED")

    except Exception:
        _log(window, "PREMIERE SCRIPT INSTALLER PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_installer(window) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.premiere_bridge import install_premiere_script

        result = install_premiere_script(project_root=project_root, install_to_premiere=True, open_folder=True)

        ok_installs = [
            item for item in result.get("install_results", [])
            if item.get("ok") and not item.get("safe_copy")
        ]
        failed_installs = [
            item for item in result.get("install_results", [])
            if not item.get("ok")
        ]

        _log(window, "")
        _log(window, "PREMIERE SCRIPT INSTALLER DONE")
        _log(window, f"Folder: {result['package_dir']}")
        _log(window, f"Pointer: {result['latest_xml_pointer']}")
        _log(window, f"XML: {result['xml']}")
        _log(window, f"Installed to Premiere folders: {len(ok_installs)}")
        _log(window, f"Failed Program Files installs: {len(failed_installs)}")

        if ok_installs:
            QMessageBox.information(
                window,
                "Install Premiere Script",
                "Đã cài script vào Premiere folder.\n\n"
                "Restart Premiere rồi vào:\n"
                "File > Scripts > STT_Import_Latest_XML",
            )
        else:
            QMessageBox.warning(
                window,
                "Install Premiere Script",
                "Đã tạo package và safe copy trong Documents.\n\n"
                "Nếu muốn hiện trong File > Scripts menu, chạy:\n"
                "INSTALL_TO_PREMIERE_MENU.bat bằng Run as Administrator.\n\n"
                "Hoặc trong Premiere dùng:\n"
                "File > Scripts > Run Script File",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREMIERE SCRIPT INSTALLER ERROR")
        _log(window, msg)
        QMessageBox.critical(window, "Premiere Script Installer Error", msg[-4000:])


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
