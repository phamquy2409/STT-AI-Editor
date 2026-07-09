
from __future__ import annotations

import os
import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_premiere_pointer_patch_applied"


def apply_premiere_pointer_patch(window_class) -> None:
    # Module 042.
    # Adds Update Premiere XML Pointer button.
    # Also wraps known export XML methods when possible.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(750, lambda: _install_pointer_ui(self))
        QTimer.singleShot(900, lambda: _wrap_export_methods(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_pointer_ui(window) -> None:
    if getattr(window, "_stt_premiere_pointer_ui_installed", False):
        return

    try:
        window._stt_premiere_pointer_ui_installed = True

        btn = QPushButton("Update Premiere XML Pointer")
        btn.setObjectName("sttProductionButton_normal_UpdatePremiereXMLPointer")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _update_pointer(window, show_popup=True))

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(btn)
            _log(window, "PREMIERE XML POINTER BUTTON LOADED")
            return

        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            box = QGroupBox("Premiere XML Pointer")
            layout = QVBoxLayout(box)
            layout.addWidget(btn)
            root_layout.insertWidget(0, box)
            _log(window, "PREMIERE XML POINTER PANEL LOADED")

    except Exception:
        _log(window, "PREMIERE POINTER PATCH ERROR")
        _log(window, traceback.format_exc())


def _wrap_export_methods(window) -> None:
    if getattr(window, "_stt_premiere_pointer_methods_wrapped", False):
        return

    method_names = [
        "export_latest_manual_xml",
        "export_manual_xml",
        "export_latest_xml",
        "export_manual_selection_xml",
    ]

    wrapped = 0

    for name in method_names:
        func = getattr(window, name, None)
        if not callable(func):
            continue

        def make_wrapper(original, method_name):
            def wrapper(*args, **kwargs):
                result = original(*args, **kwargs)
                QTimer.singleShot(1000, lambda: _update_pointer(window, show_popup=False))
                _log(window, f"Auto Premiere pointer scheduled after {method_name}")
                return result
            return wrapper

        try:
            setattr(window, name, make_wrapper(func, name))
            wrapped += 1
        except Exception:
            pass

    window._stt_premiere_pointer_methods_wrapped = True
    _log(window, f"Premiere pointer auto-wrap methods: {wrapped}")


def _update_pointer(window, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.premiere_bridge import update_premiere_xml_pointer

        result = update_premiere_xml_pointer(
            project_root=project_root,
            source="module_042_gui_button",
        )

        _log(window, "")
        _log(window, "PREMIERE XML POINTER UPDATED")
        _log(window, f"XML: {result['xml']}")
        _log(window, f"Pointer: {result['pointer_txt']}")

        if show_popup:
            QMessageBox.information(
                window,
                "Update Premiere XML Pointer",
                "Đã update XML pointer cho Premiere panel.\n\n"
                f"{result['xml']}",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PREMIERE XML POINTER ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Premiere XML Pointer Error", msg[-4000:])


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
