
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QMessageBox, QPushButton, QVBoxLayout


PATCH_FLAG = "_stt_ai_shot_scorer_patch_applied"


def apply_ai_shot_scorer_patch(window_class) -> None:
    # Module 046.
    # Adds AI Shot Scorer V1 with Prewedding intents.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(1150, lambda: _install_ai_shot_scorer_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_ai_shot_scorer_ui(window) -> None:
    if getattr(window, "_stt_ai_shot_scorer_ui_installed", False):
        return

    try:
        window._stt_ai_shot_scorer_ui_installed = True

        from core.ai_shot_scorer import ALL_INTENTS

        combo = QComboBox()
        combo.setObjectName("sttAIShotScorerIntentCombo")
        for intent in sorted(ALL_INTENTS):
            combo.addItem(intent)

        preferred = "prewedding_reel_60s"
        index = combo.findText(preferred)
        if index >= 0:
            combo.setCurrentIndex(index)

        btn = QPushButton("Run AI Shot Scorer V1")
        btn.setObjectName("sttProductionButton_primary_RunAIShotScorerV1")
        btn.setMinimumHeight(38)
        btn.clicked.connect(lambda: _run_scorer(window, combo.currentText(), show_popup=True))

        box = QGroupBox("AI Shot Scorer / Prewedding")
        box.setObjectName("sttAIShotScorerPanel")
        layout = QVBoxLayout(box)
        layout.addWidget(combo)
        layout.addWidget(btn)

        production_panel = None
        for group in window.findChildren(QGroupBox):
            if group.objectName() == "sttProductionPanel" or "Production Workflow" in group.title():
                production_panel = group
                break

        if production_panel is not None and production_panel.layout() is not None:
            production_panel.layout().addWidget(box)
            _log(window, "AI SHOT SCORER V1 UI LOADED")
            return

        central = window.centralWidget()
        if central is not None:
            root_layout = central.layout()
            if root_layout is None:
                root_layout = QVBoxLayout(central)
                central.setLayout(root_layout)

            root_layout.insertWidget(0, box)
            _log(window, "AI SHOT SCORER V1 PANEL LOADED")

    except Exception:
        _log(window, "AI SHOT SCORER PATCH ERROR")
        _log(window, traceback.format_exc())


def _run_scorer(window, intent: str, show_popup: bool = False) -> None:
    try:
        project_root = _get_project_root_from_window(window)

        from core.ai_shot_scorer import run_ai_shot_scorer

        result = run_ai_shot_scorer(
            project_root=project_root,
            intent=intent,
            top_n=120,
            open_folder=True,
        )

        _log(window, "")
        _log(window, "AI SHOT SCORER V1 DONE")
        _log(window, f"Intent: {result['intent']}")
        _log(window, f"Candidates: {result['candidate_count']}")
        _log(window, f"Selected: {result['selected_count']}")
        _log(window, f"Top score: {result['top_score']}")
        _log(window, f"Report: {result['report_dir']}")

        if show_popup:
            QMessageBox.information(
                window,
                "AI Shot Scorer V1",
                "Đã chấm điểm shot.\n\n"
                f"Intent: {result['intent']}\n"
                f"Candidates: {result['candidate_count']}\n"
                f"Selected: {result['selected_count']}\n\n"
                "Mở report để xem danh sách top shots.",
            )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "AI SHOT SCORER V1 ERROR")
        _log(window, msg)

        if show_popup:
            QMessageBox.critical(window, "AI Shot Scorer V1 Error", msg[-4000:])


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
