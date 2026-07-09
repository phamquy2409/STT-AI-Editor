from __future__ import annotations
import traceback
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QMessageBox, QPushButton, QVBoxLayout

PATCH_FLAG = "_stt_review_package_patch_applied"

def apply_review_package_patch(window_class) -> None:
    if getattr(window_class, PATCH_FLAG, False): return
    old_init = window_class.__init__
    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1650, lambda: _install_ui(self))
    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)

def _install_ui(window) -> None:
    if getattr(window, "_stt_review_package_ui_installed", False): return
    try:
        window._stt_review_package_ui_installed = True
        btn = QPushButton("Create Review Package")
        btn.setMinimumHeight(34)
        btn.clicked.connect(lambda: _run(window, show_popup=True))
        box = QGroupBox("Review Package")
        layout = QVBoxLayout(box); layout.addWidget(btn)
        target = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                target = group; break
        if target is not None and target.layout() is not None:
            target.layout().addWidget(box)
        elif window.centralWidget() and window.centralWidget().layout():
            window.centralWidget().layout().insertWidget(0, box)
        _log(window, "REVIEW PACKAGE UI LOADED")
    except Exception:
        _log(window, "REVIEW PACKAGE PATCH ERROR"); _log(window, traceback.format_exc())

def _run(window, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)
        from core.review_package import create_review_package
        result = create_review_package(project_root=project_root, open_folder=True)
        _log(window, ""); _log(window, "REVIEW PACKAGE DONE")
        _log(window, f"OK: {result.get('ok')}")
        _log(window, f"Output: {result.get('report_dir') or result.get('output_dir') or result.get('dashboard_html')}")
        if show_popup:
            QMessageBox.information(window, "Review Package", "Đã chạy xong.\n\n" + str(result.get("report_dir") or result.get("output_dir") or result.get("dashboard_html")))
    except Exception:
        msg = traceback.format_exc()
        _log(window, "REVIEW PACKAGE ERROR"); _log(window, msg)
        if show_popup: QMessageBox.critical(window, "Review Package Error", msg[-4000:])

def _get_project_root_from_window(window) -> Path:
    edit = getattr(window, "project_edit", None)
    if edit is not None and edit.text().strip(): return Path(edit.text().strip())
    return Path("D:/STT Projects/Wedding_Test_001")

def _log(window, message: str) -> None:
    try:
        if hasattr(window, "append_log") and callable(window.append_log):
            window.append_log(str(message)); return
    except Exception: pass
    print(message)
