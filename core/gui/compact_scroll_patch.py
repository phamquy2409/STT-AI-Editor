
from __future__ import annotations

import traceback

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


PATCH_FLAG = "_stt_compact_scroll_patch_applied"


def apply_compact_scroll_patch(window_class) -> None:
    # Module 047B.
    # Fix GUI getting too tall after many AI/Premiere buttons.
    #
    # Adds:
    # - Scroll area around the whole app
    # - Smaller button heights
    # - Smaller group margins/spacings
    # - Resizable window with smaller minimum size

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1600, lambda: _apply_compact_layout(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _apply_compact_layout(window) -> None:
    try:
        if getattr(window, "_stt_compact_scroll_applied", False):
            return

        window._stt_compact_scroll_applied = True

        _make_window_resizable(window)
        _compact_widgets(window)
        _wrap_central_widget_in_scroll_area(window)

        QTimer.singleShot(400, lambda: _compact_widgets(window))

        _log(window, "COMPACT SCROLL GUI FIX APPLIED")

    except Exception:
        _log(window, "COMPACT SCROLL GUI FIX ERROR")
        _log(window, traceback.format_exc())


def _make_window_resizable(window) -> None:
    try:
        window.setMinimumSize(920, 620)
        window.resize(1180, 760)
    except Exception:
        pass

    try:
        flags = window.windowFlags()
        window.setWindowFlags(flags | Qt.WindowMaximizeButtonHint)
        window.show()
    except Exception:
        pass


def _compact_widgets(root) -> None:
    # Buttons were getting huge because every module adds full-width buttons.
    # Keep them usable but much shorter.
    for btn in root.findChildren(QPushButton):
        try:
            text = btn.text().strip()

            if text.startswith(("1.", "2.", "3.", "4.")):
                btn.setMinimumHeight(34)
                btn.setMaximumHeight(40)
            else:
                btn.setMinimumHeight(26)
                btn.setMaximumHeight(34)

            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        except Exception:
            pass

    for combo in root.findChildren(QComboBox):
        try:
            combo.setMinimumHeight(26)
            combo.setMaximumHeight(32)
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        except Exception:
            pass

    for group in root.findChildren(QGroupBox):
        try:
            group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
            lay = group.layout()
            if lay is not None:
                lay.setContentsMargins(10, 10, 10, 10)
                lay.setSpacing(6)
        except Exception:
            pass

    try:
        central = root.centralWidget()
        if central is not None and central.layout() is not None:
            central.layout().setContentsMargins(6, 6, 6, 6)
            central.layout().setSpacing(6)
    except Exception:
        pass


def _wrap_central_widget_in_scroll_area(window) -> None:
    central = window.centralWidget()

    if central is None:
        return

    if isinstance(central, QScrollArea):
        central.setWidgetResizable(True)
        central.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        central.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        return

    # Avoid wrapping twice.
    if getattr(window, "_stt_original_central_widget", None) is not None:
        return

    window._stt_original_central_widget = central

    scroll = QScrollArea()
    scroll.setObjectName("sttMainScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setFrameShape(QScrollArea.NoFrame)

    # Detach original central from the window and put it inside scroll area.
    central.setParent(None)
    scroll.setWidget(central)

    window.setCentralWidget(scroll)


def _log(window, message: str) -> None:
    try:
        if hasattr(window, "append_log") and callable(window.append_log):
            window.append_log(str(message))
            return
    except Exception:
        pass

    print(message)
