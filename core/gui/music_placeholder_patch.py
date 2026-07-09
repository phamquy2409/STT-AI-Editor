
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_music_placeholder_patch_applied"


def apply_music_placeholder_patch(window_class) -> None:
    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1720, lambda: _install_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_ui(window) -> None:
    if getattr(window, "_stt_music_placeholder_ui_installed", False):
        return

    try:
        window._stt_music_placeholder_ui_installed = True

        from core.music_placeholder import MUSIC_MOODS

        combo = QComboBox()
        combo.setObjectName("sttMusicPlaceholderIntentCombo")
        for key in MUSIC_MOODS:
            combo.addItem(key)

        btn = QPushButton("Create Music Cue Sheet / Placeholder")
        btn.setObjectName("sttButton_music_placeholder")
        btn.setMinimumHeight(34)
        btn.clicked.connect(lambda: _run(window, combo.currentText(), show_popup=True))

        box = QGroupBox("Music Placeholder / Cue Sheet")
        box.setObjectName("sttPanel_music_placeholder")
        layout = QVBoxLayout(box)
        layout.addWidget(combo)
        layout.addWidget(btn)

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().insertWidget(1, box)
            _log(window, "MUSIC PLACEHOLDER UI LOADED")
            return

        central = window.centralWidget()
        if central is not None and central.layout() is not None:
            central.layout().insertWidget(0, box)
            _log(window, "MUSIC PLACEHOLDER PANEL LOADED")

    except Exception:
        _log(window, "MUSIC PLACEHOLDER PATCH ERROR")
        _log(window, traceback.format_exc())


def _run(window, intent: str, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.music_placeholder import create_music_placeholder_manager

        result = create_music_placeholder_manager(
            project_root=project_root,
            intent=intent,
            open_folder=True,
        )

        _log(window, "")
        _log(window, "MUSIC PLACEHOLDER DONE")
        _log(window, f"OK: {result.get('ok')}")
        _log(window, f"Cue CSV: {result.get('cue_csv')}")
        _log(window, f"Links: {result.get('links_html')}")

        if show_popup:
            QMessageBox.information(
                window,
                "Music Placeholder / Cue Sheet",
                "Đã tạo cue sheet nhạc.\n\n"
                f"Tracks: {result.get('track_count')}\n"
                f"Folder:\n{result.get('output_dir')}",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "MUSIC PLACEHOLDER ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "Music Placeholder Error", msg[-4000:])


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
