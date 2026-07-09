from __future__ import annotations

import os
import subprocess
import sys
import traceback
import webbrowser
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


PATCH_FLAG = "_stt_production_gui_patch_applied"


def apply_production_gui_patch(window_class) -> None:
    # Module 036.
    # Adds a clean production workflow panel on top of the existing GUI.
    # Also provides a safe toggle to hide old/test/legacy buttons without deleting them.

    if getattr(window_class, PATCH_FLAG, False):
        return

    old_init = window_class.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        QTimer.singleShot(0, lambda: _install_production_ui(self))

    window_class.__init__ = __init__
    setattr(window_class, PATCH_FLAG, True)


def _install_production_ui(window) -> None:
    if getattr(window, "_stt_production_ui_installed", False):
        return

    try:
        window._stt_production_ui_installed = True
        window.setWindowTitle("STT AI Editor - Production")

        central = window.centralWidget()
        if central is None:
            return

        root_layout = central.layout()
        if root_layout is None:
            root_layout = QVBoxLayout(central)
            central.setLayout(root_layout)

        panel = _build_production_panel(window)

        try:
            root_layout.insertWidget(0, panel)
        except Exception:
            root_layout.addWidget(panel)

        _apply_soft_style(window)

        checkbox = getattr(window, "_stt_production_mode_checkbox", None)
        if checkbox is not None:
            checkbox.setChecked(True)
            _set_production_visibility(window, True)

        _log(window, "PRODUCTION GUI CLEANUP LOADED")
        _log(window, "Stable version: STT AI Editor v0.36")

    except Exception:
        msg = traceback.format_exc()
        _log(window, "PRODUCTION GUI PATCH ERROR")
        _log(window, msg)


def _build_production_panel(window) -> QWidget:
    box = QGroupBox("STT Production Workflow")
    box.setObjectName("sttProductionPanel")

    layout = QVBoxLayout(box)

    title = QLabel("Workflow chính: chạy bản cưới cuối → review → save → export XML → import Premiere")
    title.setObjectName("sttProductionTitle")
    title.setWordWrap(True)
    layout.addWidget(title)

    grid = QGridLayout()
    layout.addLayout(grid)

    btn_final = _button("1. Run Final Wedding + Live Review", "primary")
    btn_live = _button("2. Open Live Manual Review", "normal")
    btn_xml = _button("3. Export Latest Manual XML", "normal")
    btn_folder = _button("4. Open Latest XML Folder", "normal")
    btn_health = _button("Health Check", "small")
    btn_backup = _button("Stable Backup", "small")

    btn_final.clicked.connect(lambda: _run_final_workflow(window))
    btn_live.clicked.connect(lambda: _open_live_review(window))
    btn_xml.clicked.connect(lambda: _export_latest_xml(window))
    btn_folder.clicked.connect(lambda: _open_latest_xml_folder(window))
    btn_health.clicked.connect(lambda: _run_health_check(window))
    btn_backup.clicked.connect(lambda: _run_stable_backup(window))

    grid.addWidget(btn_final, 0, 0)
    grid.addWidget(btn_live, 0, 1)
    grid.addWidget(btn_xml, 0, 2)
    grid.addWidget(btn_folder, 0, 3)
    grid.addWidget(btn_health, 1, 0)
    grid.addWidget(btn_backup, 1, 1)

    checkbox = QCheckBox("Production Mode: ẩn bớt nút cũ / test / legacy")
    checkbox.setObjectName("sttProductionModeCheckbox")
    checkbox.toggled.connect(lambda checked: _set_production_visibility(window, checked))
    layout.addWidget(checkbox)

    hint = QLabel("Tắt Production Mode nếu cần dùng lại các nút kỹ thuật cũ.")
    hint.setObjectName("sttProductionHint")
    hint.setWordWrap(True)
    layout.addWidget(hint)

    window._stt_production_mode_checkbox = checkbox
    window._stt_production_buttons = [btn_final, btn_live, btn_xml, btn_folder, btn_health, btn_backup]

    return box


def _button(text: str, kind: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName(f"sttProductionButton_{kind}_{text}")
    button.setMinimumHeight(38)
    return button


def _run_final_workflow(window) -> None:
    _call_method_or_matching_button(
        window,
        methods=[
            "run_final_wedding_v2_live_review",
            "run_final_wedding_pipeline_v2_live_review",
            "run_final_workflow",
            "run_final_wedding_v2",
            "run_wedding_pipeline_v2",
        ],
        button_phrases=[
            "Run Final Wedding V2 + Live Review",
            "Final Wedding V2",
            "Wedding Pipeline V2",
            "Run Wedding Pipeline V2",
        ],
        action_name="Run Final Wedding + Live Review",
    )


def _open_live_review(window) -> None:
    _call_method_or_matching_button(
        window,
        methods=[
            "open_live_manual_review",
            "open_live_review",
        ],
        button_phrases=[
            "Open Live Manual Review",
            "Live Manual Review",
        ],
        action_name="Open Live Manual Review",
    )


def _export_latest_xml(window) -> None:
    _call_method_or_matching_button(
        window,
        methods=[
            "export_latest_manual_xml",
            "export_manual_xml",
            "export_latest_xml",
            "export_manual_selection_xml",
        ],
        button_phrases=[
            "Export Latest Manual XML",
            "Latest Manual XML",
            "Export XML",
        ],
        action_name="Export Latest Manual XML",
    )


def _open_latest_xml_folder(window) -> None:
    _call_method_or_matching_button(
        window,
        methods=[
            "open_latest_xml_folder",
            "open_xml_folder",
            "open_latest_export_folder",
            "open_latest_output_folder",
        ],
        button_phrases=[
            "Open Latest XML Folder",
            "Open XML Folder",
            "Latest XML Folder",
            "Open Latest",
        ],
        action_name="Open Latest XML Folder",
    )


def _run_health_check(window) -> None:
    try:
        project_root = _get_project_root_from_window(window)
        repo_root = _get_repo_root()

        from core.app_health import run_health_check

        result = run_health_check(project_root=project_root, repo_root=repo_root)
        report_dir = Path(result.get("report_dir", ""))

        _log(window, "")
        _log(window, "HEALTH CHECK DONE")
        _log(window, f"OK: {result['summary'].get('ok', 0)}")
        _log(window, f"WARN: {result['summary'].get('warn', 0)}")
        _log(window, f"FAIL: {result['summary'].get('fail', 0)}")
        _log(window, str(report_dir))

        if report_dir.exists():
            os.startfile(report_dir)

        if int(result["summary"].get("fail", 0)) > 0:
            QMessageBox.warning(window, "Health Check", "Có mục FAIL. Xem report vừa mở.")
        else:
            QMessageBox.information(window, "Health Check", "Health Check OK. Report đã được mở.")

    except Exception:
        msg = traceback.format_exc()
        _log(window, "HEALTH CHECK ERROR")
        _log(window, msg)
        QMessageBox.critical(window, "Health Check Error", msg[-4000:])


def _run_stable_backup(window) -> None:
    try:
        repo_root = _get_repo_root()
        script = repo_root / "scripts" / "create_stable_backup.py"

        if script.exists():
            _log(window, "RUN STABLE BACKUP")
            proc = subprocess.Popen(
                [sys.executable, str(script)],
                cwd=str(repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            out, _ = proc.communicate()

            if out:
                for line in out.splitlines():
                    _log(window, line)

            releases = repo_root / "releases"
            if releases.exists():
                os.startfile(releases)

            if proc.returncode == 0:
                QMessageBox.information(window, "Stable Backup", "Backup xong. Folder releases đã mở.")
            else:
                QMessageBox.warning(window, "Stable Backup", "Backup có lỗi. Xem log trong GUI.")
            return

        QMessageBox.warning(
            window,
            "Stable Backup",
            f"Không thấy script:\n{script}\n\nChạy thủ công:\npython scripts/create_stable_backup.py",
        )

    except Exception:
        msg = traceback.format_exc()
        _log(window, "STABLE BACKUP ERROR")
        _log(window, msg)
        QMessageBox.critical(window, "Stable Backup Error", msg[-4000:])


def _call_method_or_matching_button(
    window,
    methods: list[str],
    button_phrases: list[str],
    action_name: str,
) -> None:
    for name in methods:
        func = getattr(window, name, None)
        if callable(func):
            _log(window, f"PRODUCTION ACTION: {action_name} -> {name}()")
            func()
            return

    buttons = window.findChildren(QPushButton)
    for phrase in button_phrases:
        phrase_l = phrase.lower()
        for button in buttons:
            if str(button.objectName()).startswith("sttProductionButton_"):
                continue
            text = button.text().strip()
            if phrase_l in text.lower():
                _log(window, f"PRODUCTION ACTION: {action_name} -> click button '{text}'")
                button.click()
                return

    QMessageBox.warning(
        window,
        "Không tìm thấy chức năng",
        f"Không tìm thấy hàm hoặc nút cho:\n{action_name}\n\nTắt Production Mode và dùng nút cũ nếu cần.",
    )


def _set_production_visibility(window, enabled: bool) -> None:
    # Hide only technical/old buttons. Do not delete anything.
    # User can turn checkbox OFF to restore.
    try:
        for button in window.findChildren(QPushButton):
            if str(button.objectName()).startswith("sttProductionButton_"):
                button.setVisible(True)
                continue

            text = button.text().strip()
            low = text.lower()

            hide = False

            if any(word in low for word in [" legacy", "old ", " old", "debug", "test only"]):
                hide = True

            if low.startswith("run ") and not any(
                keep in low
                for keep in [
                    "final",
                    "wedding v2",
                    "live",
                    "health",
                    "backup",
                ]
            ):
                hide = True

            technical_words = [
                "scanner",
                "scan source",
                "detect segments",
                "analyze segments",
                "generate report",
                "generate manual review",
                "roughcut",
                "pipeline old",
                "basic pipeline",
            ]
            if any(word in low for word in technical_words):
                hide = True

            safe_words = [
                "browse",
                "choose",
                "select",
                "open",
                "latest",
                "xml",
                "live",
                "final",
                "save",
                "preset",
                "clean",
                "archive",
                "stop",
                "project",
                "source",
            ]
            if any(word in low for word in safe_words):
                hide = False

            button.setVisible(not hide if enabled else True)

        _log(window, f"Production Mode: {'ON' if enabled else 'OFF'}")

    except Exception:
        _log(window, "SET PRODUCTION VISIBILITY ERROR")
        _log(window, traceback.format_exc())


def _apply_soft_style(window) -> None:
    # Keep safe and simple. No hard color dependency.
    try:
        old_style = window.styleSheet() or ""
        if "sttProductionPanel" in old_style:
            return

        extra = """
        QGroupBox#sttProductionPanel {
            font-weight: 700;
            border: 1px solid rgba(120,120,120,90);
            border-radius: 10px;
            margin-top: 10px;
            padding: 12px;
        }
        QLabel#sttProductionTitle {
            font-size: 13px;
            font-weight: 600;
        }
        QLabel#sttProductionHint {
            opacity: 0.75;
        }
        QPushButton[objectName^="sttProductionButton_primary"] {
            font-weight: 700;
            min-height: 42px;
        }
        """
        window.setStyleSheet(old_style + "\n" + extra)
    except Exception:
        pass


def _get_project_root_from_window(window) -> Path:
    edit = getattr(window, "project_edit", None)
    if edit is not None:
        text = edit.text().strip()
        if text:
            return Path(text)

    return Path("D:/STT Projects/Wedding_Test_001")


def _get_repo_root() -> Path:
    # source: D:/Projects/STT-AI-Editor/core/gui/production_patch.py -> parents[2]
    # EXE:    .../dist/STT AI Editor/_internal/core/gui/production_patch.py -> parents[2] = _internal
    p = Path(__file__).resolve()
    try:
        return p.parents[2]
    except Exception:
        return Path.cwd()


def _log(window, message: str) -> None:
    try:
        if hasattr(window, "append_log") and callable(window.append_log):
            window.append_log(str(message))
            return
    except Exception:
        pass

    print(message)
