
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_style_profile_patch_applied"


def apply_style_profile_patch(window_class) -> None:
    # Module 044.
    # Adds Create/Update Wedding Style Profile button to GUI.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(950, lambda: _install_style_profile_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_style_profile_ui(window) -> None:
    if getattr(window, "_stt_style_profile_ui_installed", False):
        return

    try:
        window._stt_style_profile_ui_installed = True

        btn = QPushButton("Create Wedding Style Profile")
        btn.setObjectName("sttProductionButton_primary_CreateWeddingStyleProfile")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _create_profile(window, show_popup=True))

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(btn)
            _log(window, "WEDDING STYLE PROFILE BUTTON LOADED")
            return

        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            box = QGroupBox("Wedding Style Profile")
            layout = QVBoxLayout(box)
            layout.addWidget(btn)
            root_layout.insertWidget(0, box)
            _log(window, "WEDDING STYLE PROFILE PANEL LOADED")

    except Exception:
        _log(window, "WEDDING STYLE PROFILE PATCH ERROR")
        _log(window, traceback.format_exc())


def _create_profile(window, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.style_profile import create_wedding_style_profile

        result = create_wedding_style_profile(project_root=project_root)

        _log(window, "")
        _log(window, "WEDDING STYLE PROFILE UPDATED")
        _log(window, f"Profile: {result['profile']}")
        _log(window, f"Report: {result['report_dir']}")

        if show_popup:
            QMessageBox.information(
                window,
                "Wedding Style Profile",
                "Đã tạo/cập nhật Wedding Style Profile.\n\n"
                "Đây là nền để module AI sau học gu dựng của anh.",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "WEDDING STYLE PROFILE ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Wedding Style Profile Error", msg[-4000:])


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
