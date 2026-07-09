
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_release_packager_patch_applied"


def apply_release_packager_patch(window_class) -> None:
    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1600, lambda: _install_release_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_release_ui(window) -> None:
    if getattr(window, "_stt_release_packager_ui_installed", False):
        return

    try:
        window._stt_release_packager_ui_installed = True

        build_first_check = QCheckBox("Build EXE first")
        build_first_check.setObjectName("sttReleaseBuildFirstCheck")
        build_first_check.setChecked(False)

        btn = QPushButton("Create Release Package")
        btn.setObjectName("sttProductionButton_CreateReleasePackage")
        btn.setMinimumHeight(34)
        btn.clicked.connect(lambda: _run_packager(window, build_first_check.isChecked(), show_popup=True))

        box = QGroupBox("App Release Packager")
        box.setObjectName("sttReleasePackagerPanel")
        layout = QVBoxLayout(box)
        layout.addWidget(build_first_check)
        layout.addWidget(btn)

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(box)
            _log(window, "RELEASE PACKAGER UI LOADED")
            return

        central = window.centralWidget()
        if central is not None and central.layout() is not None:
            central.layout().insertWidget(0, box)
            _log(window, "RELEASE PACKAGER PANEL LOADED")

    except Exception:
        _log(window, "RELEASE PACKAGER PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_packager(window, build_first: bool, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.release_packager import create_release_package

        result = create_release_package(
            project_root=project_root,
            build_first=build_first,
            run_doctor=True,
            open_folder=True,
        )

        _log(window, "")
        _log(window, "RELEASE PACKAGE DONE")
        _log(window, f"OK: {result['ok']}")
        _log(window, f"Release: {result['release_dir']}")
        _log(window, f"ZIP: {result['zip']}")
        _log(window, f"EXE: {result['exe']}")

        if show_popup:
            if result["ok"]:
                QMessageBox.information(
                    window,
                    "Release Package",
                    "Đã tạo release package.\n\n"
                    f"ZIP:\n{result['zip']}\n\n"
                    "Copy nguyên folder STT AI Editor trong release, không copy riêng file EXE.",
                )
            else:
                QMessageBox.warning(
                    window,
                    "Release Package",
                    "Tạo release package có lỗi.\n\n"
                    f"Report folder:\n{result['release_dir']}",
                )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "RELEASE PACKAGE ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Release Package Error", msg[-4000:])


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
