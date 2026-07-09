from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import time
import traceback
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QMainWindow,
)

from core.export_cleaner import archive_old_exports_existing_project, preview_export_cleanup_existing_project
from core.exporter import export_premiere_xml_existing_project
from core.manual_export import build_manual_selection_existing_project
from core.manual_review import generate_manual_review_existing_project
from core.pipeline import run_one_click_pipeline_existing_project
from core.pipeline_v2 import run_wedding_pipeline_v2_existing_project
from core.project import ProjectManager
from core.project_presets import (
    get_project_workflow_values,
    list_workflow_presets,
    load_project_workflow_preset,
    save_project_workflow_preset,
)
from core.review import generate_preview_review_existing_project


@dataclass
class GuiDefaults:
    projects_root: str = "D:/STT Projects"
    project_name: str = "Wedding_Test_001"
    project_root: str = "D:/STT Projects/Wedding_Test_001"
    source_folder: str = "D:/5thang5test"
    target_duration: int = 60
    top_candidates: int = 120
    live_manual_port: int = 8787
    keep_latest_exports: int = 2
    preset_name: str = "wedding_highlight_60s"
    window_width: int = 1260
    window_height: int = 980


class GuiSettingsStore:
    def __init__(self, repo_root: Path) -> None:
        appdata = os.environ.get("APPDATA", "").strip()
        self.path = Path(appdata) / "STT_AI_Editor" / "gui_settings.json" if appdata else repo_root / ".stt_ai_editor" / "gui_settings.json"

    def load(self, defaults: GuiDefaults) -> GuiDefaults:
        data = asdict(defaults)
        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    for key in data.keys():
                        if key in payload and payload[key] is not None:
                            data[key] = payload[key]
            except Exception:
                pass

        return GuiDefaults(
            projects_root=str(data["projects_root"]),
            project_name=str(data["project_name"]),
            project_root=str(data["project_root"]),
            source_folder=str(data["source_folder"]),
            target_duration=int(data["target_duration"]),
            top_candidates=int(data["top_candidates"]),
            live_manual_port=int(data["live_manual_port"]),
            keep_latest_exports=int(data["keep_latest_exports"]),
            preset_name=str(data["preset_name"]),
            window_width=int(data["window_width"]),
            window_height=int(data["window_height"]),
        )

    def save(self, values: dict[str, Any]) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.path

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()


class QtLogStream:
    def __init__(self, callback: Callable[[str], None]) -> None:
        self.callback = callback
        self._buffer = ""

    def write(self, text: str) -> None:
        if not text:
            return
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self.callback(line)

    def flush(self) -> None:
        if self._buffer.strip():
            self.callback(self._buffer.strip())
        self._buffer = ""


class Worker(QObject):
    log = Signal(str)
    done = Signal(dict)
    error = Signal(str)

    def __init__(self, action: str, payload: dict[str, Any]) -> None:
        super().__init__()
        self.action = action
        self.payload = payload

    def run(self) -> None:
        stream = QtLogStream(lambda msg: self.log.emit(msg))
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                result = self._run_action()
            stream.flush()
            self.done.emit(result if isinstance(result, dict) else {"result": result})
        except Exception:
            stream.flush()
            self.error.emit(traceback.format_exc())

    def _run_action(self) -> dict[str, Any]:
        project_root = Path(self.payload["project_root"])

        if self.action == "pipeline":
            return run_one_click_pipeline_existing_project(
                project_root=project_root,
                source_folder=Path(self.payload["source_folder"]) if self.payload.get("source_folder") else None,
                run_from_scratch=bool(self.payload.get("run_from_scratch", False)),
                target_duration_seconds=float(self.payload.get("target_duration", 60)),
                top_candidates=int(self.payload.get("top_candidates", 120)),
            )

        if self.action == "wedding_pipeline_v2":
            return run_wedding_pipeline_v2_existing_project(
                project_root=project_root,
                target_duration_seconds=float(self.payload.get("target_duration", 60)),
                max_segments_per_video=int(self.payload.get("max_segments_per_video", 1)),
            )

        if self.action == "manual_review":
            return generate_manual_review_existing_project(project_root=project_root, input_json=None)

        if self.action == "manual_export":
            selection_json = self.payload.get("selection_json")
            if not selection_json:
                raise RuntimeError("No manual_selection.json selected.")
            manual = build_manual_selection_existing_project(project_root=project_root, selection_json=Path(selection_json))
            xml = export_premiere_xml_existing_project(
                project_root=project_root,
                roughcut_json=Path(manual["manual_json"]),
                sequence_fps=int(self.payload.get("sequence_fps", 25)),
                sequence_width=int(self.payload.get("sequence_width", 3840)),
                sequence_height=int(self.payload.get("sequence_height", 2160)),
            )
            review = generate_preview_review_existing_project(project_root=project_root, roughcut_json=Path(manual["manual_json"]))
            return {"manual": manual, "xml": xml, "review": review, "premiere_xml": xml.get("xml", ""), "review_html": review.get("html", ""), "output_dir": manual.get("output_dir", "")}

        if self.action == "preview_exports":
            return preview_export_cleanup_existing_project(project_root=project_root, keep_latest_per_prefix=int(self.payload.get("keep_latest_exports", 2)))

        if self.action == "archive_exports":
            return archive_old_exports_existing_project(project_root=project_root, keep_latest_per_prefix=int(self.payload.get("keep_latest_exports", 2)))

        raise RuntimeError(f"Unknown action: {self.action}")


class STTAIEditorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.settings_store = GuiSettingsStore(self.repo_root_static())
        self.defaults = self.settings_store.load(GuiDefaults())
        self.worker_thread: QThread | None = None
        self.worker: Worker | None = None
        self.last_result: dict[str, Any] = {}
        self.live_manual_process: subprocess.Popen | None = None
        self.auto_open_live_after_done = False
        self.preset_values: dict[str, Any] = {}

        self.setWindowTitle("STT AI Editor")
        self.resize(self.defaults.window_width, self.defaults.window_height)

        self.projects_root_edit = QLineEdit(self.defaults.projects_root)
        self.project_name_edit = QLineEdit(self.defaults.project_name)
        self.project_edit = QLineEdit(self.defaults.project_root)
        self.source_edit = QLineEdit(self.defaults.source_folder)
        self.overwrite_project_check = QCheckBox("Overwrite nếu project đã tồn tại")

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 900)
        self.duration_spin.setValue(self.defaults.target_duration)
        self.duration_spin.setSuffix(" sec")

        self.candidate_spin = QSpinBox()
        self.candidate_spin.setRange(20, 2000)
        self.candidate_spin.setValue(self.defaults.top_candidates)

        self.live_port_spin = QSpinBox()
        self.live_port_spin.setRange(8000, 9999)
        self.live_port_spin.setValue(self.defaults.live_manual_port)

        self.keep_exports_spin = QSpinBox()
        self.keep_exports_spin.setRange(1, 20)
        self.keep_exports_spin.setValue(self.defaults.keep_latest_exports)

        self.preset_combo = QComboBox()
        self._load_preset_combo()

        self.from_scratch_check = QCheckBox("Run from scratch: scan / detect / analyze lại")
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight:700; color:#8ef0b0;")
        self.live_status_label = QLabel("Live Manual: OFF")
        self.live_status_label.setStyleSheet("font-weight:700; color:#aaaab2;")
        self.workflow_label = QLabel("Workflow: Run Final V2 → KEEP/REJECT → Save → Export Latest XML")
        self.workflow_label.setStyleSheet("font-weight:700; color:#ffd166;")
        self.settings_label = QLabel("Settings: loaded")
        self.settings_label.setStyleSheet("font-weight:700; color:#8fd3ff;")
        self.cleanup_label = QLabel("Cleanup: safe archive only")
        self.cleanup_label.setStyleSheet("font-weight:700; color:#ffd166;")
        self.preset_label = QLabel("Preset: ready")
        self.preset_label.setStyleSheet("font-weight:700; color:#8fd3ff;")

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.addWidget(self._build_create_project_box())
        layout.addWidget(self._build_active_project_box())
        layout.addWidget(self._build_preset_box())
        layout.addWidget(self._build_final_workflow_box())
        layout.addWidget(self._build_action_box())
        layout.addWidget(self._build_manual_live_box())
        layout.addWidget(self._build_cleanup_box())
        layout.addWidget(self._build_settings_box())
        layout.addWidget(self._build_open_box())
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log_box, 1)

        self._connect_auto_settings()
        self._apply_style()
        self.apply_preset_to_fields(save=False)

        self.append_log("GUI SETTINGS LOADED")
        self.append_log(f"Settings file: {self.settings_store.path}")
        self.append_log(f"Project: {self.project_edit.text().strip()}")
        self.append_log(f"Source: {self.source_edit.text().strip()}")

    @staticmethod
    def repo_root_static() -> Path:
        return Path(__file__).resolve().parents[2]

    def _load_preset_combo(self) -> None:
        presets = list_workflow_presets()
        current = self.defaults.preset_name
        selected_index = 0

        for idx, preset in enumerate(presets):
            self.preset_combo.addItem(preset["label"], preset["name"])
            if preset["name"] == current:
                selected_index = idx

        self.preset_combo.setCurrentIndex(selected_index)

    def _build_create_project_box(self) -> QGroupBox:
        box = QGroupBox("Create / Open Project")
        grid = QGridLayout(box)
        root_btn = QPushButton("Chọn Projects Root")
        root_btn.clicked.connect(self.choose_projects_root)
        create_btn = QPushButton("Create New Project")
        create_btn.clicked.connect(self.create_new_project)
        open_existing_btn = QPushButton("Open Existing Project")
        open_existing_btn.clicked.connect(self.choose_project)
        grid.addWidget(QLabel("Projects root"), 0, 0)
        grid.addWidget(self.projects_root_edit, 0, 1)
        grid.addWidget(root_btn, 0, 2)
        grid.addWidget(QLabel("Project name"), 1, 0)
        grid.addWidget(self.project_name_edit, 1, 1)
        grid.addWidget(create_btn, 1, 2)
        grid.addWidget(QLabel("Existing project"), 2, 0)
        grid.addWidget(open_existing_btn, 2, 2)
        grid.addWidget(self.overwrite_project_check, 3, 1)
        grid.setColumnStretch(1, 1)
        return box

    def _build_active_project_box(self) -> QGroupBox:
        box = QGroupBox("Active Project")
        grid = QGridLayout(box)
        project_btn = QPushButton("Chọn Project")
        project_btn.clicked.connect(self.choose_project)
        source_btn = QPushButton("Chọn Source")
        source_btn.clicked.connect(self.choose_source)
        grid.addWidget(QLabel("Project folder"), 0, 0)
        grid.addWidget(self.project_edit, 0, 1)
        grid.addWidget(project_btn, 0, 2)
        grid.addWidget(QLabel("Source folder"), 1, 0)
        grid.addWidget(self.source_edit, 1, 1)
        grid.addWidget(source_btn, 1, 2)
        grid.addWidget(QLabel("Target duration"), 2, 0)
        grid.addWidget(self.duration_spin, 2, 1)
        grid.addWidget(QLabel("Top candidates"), 3, 0)
        grid.addWidget(self.candidate_spin, 3, 1)
        grid.addWidget(self.from_scratch_check, 4, 1)
        grid.setColumnStretch(1, 1)
        return box

    def _build_preset_box(self) -> QGroupBox:
        box = QGroupBox("Workflow Preset")
        row = QHBoxLayout(box)
        apply_btn = QPushButton("Apply Preset")
        apply_btn.clicked.connect(lambda: self.apply_preset_to_fields(save=True))
        save_project_btn = QPushButton("Save Preset to Project")
        save_project_btn.clicked.connect(self.save_preset_to_project)
        load_project_btn = QPushButton("Load Project Preset")
        load_project_btn.clicked.connect(self.load_preset_from_project)
        row.addWidget(QLabel("Preset"))
        row.addWidget(self.preset_combo)
        row.addWidget(apply_btn)
        row.addWidget(save_project_btn)
        row.addWidget(load_project_btn)
        row.addStretch(1)
        row.addWidget(self.preset_label)
        return box

    def _build_final_workflow_box(self) -> QGroupBox:
        box = QGroupBox("Final Workflow - Recommended")
        row = QHBoxLayout(box)
        self.run_final_v2_btn = QPushButton("Run Final Wedding V2 + Live Review")
        self.run_final_v2_btn.clicked.connect(self.run_final_wedding_v2_workflow)
        self.export_latest_big_btn = QPushButton("Export Latest Manual XML")
        self.export_latest_big_btn.clicked.connect(self.export_latest_manual_xml)
        self.open_latest_xml_big_btn = QPushButton("Open Latest XML Folder")
        self.open_latest_xml_big_btn.clicked.connect(self.open_latest_xml_folder)
        row.addWidget(self.run_final_v2_btn)
        row.addWidget(self.export_latest_big_btn)
        row.addWidget(self.open_latest_xml_big_btn)
        row.addStretch(1)
        row.addWidget(self.workflow_label)
        return box

    def _build_action_box(self) -> QGroupBox:
        box = QGroupBox("Run Pipeline / Legacy")
        row = QHBoxLayout(box)
        self.run_pipeline_btn = QPushButton("Run Pipeline Old")
        self.run_pipeline_btn.clicked.connect(self.run_pipeline)
        self.run_wedding_v2_btn = QPushButton("Run Wedding Pipeline V2")
        self.run_wedding_v2_btn.clicked.connect(self.run_wedding_pipeline_v2)
        self.manual_review_btn = QPushButton("Generate Manual Review Old")
        self.manual_review_btn.clicked.connect(self.generate_manual_review)
        self.manual_export_btn = QPushButton("Export Manual XML...")
        self.manual_export_btn.clicked.connect(self.export_manual_xml)
        row.addWidget(self.run_pipeline_btn)
        row.addWidget(self.run_wedding_v2_btn)
        row.addWidget(self.manual_review_btn)
        row.addWidget(self.manual_export_btn)
        row.addStretch(1)
        row.addWidget(self.status_label)
        return box

    def _build_manual_live_box(self) -> QGroupBox:
        box = QGroupBox("Live Manual Review - Direct Save")
        row = QHBoxLayout(box)
        self.live_open_btn = QPushButton("Open Live Manual Review")
        self.live_open_btn.clicked.connect(self.open_live_manual_review)
        self.live_stop_btn = QPushButton("Stop Live Server")
        self.live_stop_btn.clicked.connect(self.stop_live_manual_server)
        self.export_latest_manual_btn = QPushButton("Export Latest Manual XML")
        self.export_latest_manual_btn.clicked.connect(self.export_latest_manual_xml)
        row.addWidget(QLabel("Port"))
        row.addWidget(self.live_port_spin)
        row.addWidget(self.live_open_btn)
        row.addWidget(self.live_stop_btn)
        row.addWidget(self.export_latest_manual_btn)
        row.addStretch(1)
        row.addWidget(self.live_status_label)
        return box

    def _build_cleanup_box(self) -> QGroupBox:
        box = QGroupBox("Clean / Archive Exports")
        row = QHBoxLayout(box)
        self.preview_cleanup_btn = QPushButton("Preview Cleanup")
        self.preview_cleanup_btn.clicked.connect(self.preview_export_cleanup)
        self.archive_cleanup_btn = QPushButton("Archive Old Exports")
        self.archive_cleanup_btn.clicked.connect(self.archive_old_exports)
        self.open_archive_btn = QPushButton("Open Archive")
        self.open_archive_btn.clicked.connect(self.open_archive_folder)
        self.open_reports_btn = QPushButton("Open Cleanup Reports")
        self.open_reports_btn.clicked.connect(self.open_cleanup_reports)
        row.addWidget(QLabel("Keep latest per type"))
        row.addWidget(self.keep_exports_spin)
        row.addWidget(self.preview_cleanup_btn)
        row.addWidget(self.archive_cleanup_btn)
        row.addWidget(self.open_archive_btn)
        row.addWidget(self.open_reports_btn)
        row.addStretch(1)
        row.addWidget(self.cleanup_label)
        return box

    def _build_settings_box(self) -> QGroupBox:
        box = QGroupBox("Settings")
        row = QHBoxLayout(box)
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(lambda: self.save_settings(show_popup=True))
        reset_btn = QPushButton("Reset Settings")
        reset_btn.clicked.connect(self.reset_settings)
        open_settings_btn = QPushButton("Open Settings Folder")
        open_settings_btn.clicked.connect(self.open_settings_folder)
        row.addWidget(save_btn)
        row.addWidget(reset_btn)
        row.addWidget(open_settings_btn)
        row.addStretch(1)
        row.addWidget(self.settings_label)
        return box

    def _build_open_box(self) -> QGroupBox:
        box = QGroupBox("Open")
        row = QHBoxLayout(box)
        for text, func in [
            ("Open Project", self.open_project_folder),
            ("Open Exports", self.open_exports),
            ("Open Latest Review", lambda: self.open_latest("review.html")),
            ("Open Latest Manual Review", lambda: self.open_latest("manual_review.html")),
            ("Open Latest XML Folder", self.open_latest_xml_folder),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            row.addWidget(btn)
        btn_clear = QPushButton("Clear Log")
        btn_clear.clicked.connect(self.log_box.clear)
        row.addStretch(1)
        row.addWidget(btn_clear)
        return box

    def _connect_auto_settings(self) -> None:
        self.projects_root_edit.editingFinished.connect(lambda: self.save_settings(False))
        self.project_name_edit.editingFinished.connect(lambda: self.save_settings(False))
        self.project_edit.editingFinished.connect(lambda: self.save_settings(False))
        self.source_edit.editingFinished.connect(lambda: self.save_settings(False))
        self.duration_spin.valueChanged.connect(lambda _: self.save_settings(False))
        self.candidate_spin.valueChanged.connect(lambda _: self.save_settings(False))
        self.live_port_spin.valueChanged.connect(lambda _: self.save_settings(False))
        self.keep_exports_spin.valueChanged.connect(lambda _: self.save_settings(False))
        self.preset_combo.currentIndexChanged.connect(lambda _: self.save_settings(False))

    def _apply_style(self) -> None:
        self.setStyleSheet("""
        QMainWindow, QWidget { background:#101014; color:#f5f5f7; font-size:13px; }
        QGroupBox { border:1px solid #33333d; border-radius:12px; margin-top:10px; padding:12px; font-weight:700; }
        QGroupBox::title { subcontrol-origin: margin; left:12px; padding:0 8px; }
        QLineEdit, QPlainTextEdit, QSpinBox, QComboBox { background:#17171d; color:#f5f5f7; border:1px solid #33333d; border-radius:9px; padding:8px; }
        QPushButton { background:#202028; color:#f5f5f7; border:1px solid #3d3d48; border-radius:10px; padding:9px 13px; font-weight:700; }
        QPushButton:hover { background:#2b2b35; }
        QPushButton:disabled { color:#777780; background:#17171d; }
        QLabel { color:#d8d8de; }
        QCheckBox { color:#ffd166; }
        """)

    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def current_preset_name(self) -> str:
        return str(self.preset_combo.currentData() or "wedding_highlight_60s")

    def apply_preset_to_fields(self, save: bool = True) -> None:
        try:
            values = get_project_workflow_values(self.project_edit.text().strip(), self.current_preset_name())
            self.preset_values = values
            self.duration_spin.setValue(int(values["target_duration"]))
            self.candidate_spin.setValue(int(values["top_candidates"]))
            self.preset_label.setText(f"Preset: {values['label']}")
            self.preset_label.setStyleSheet("font-weight:700; color:#8ef0b0;")
            self.append_log(f"APPLY PRESET: {values['label']} - {values['description']}")
            if save:
                self.save_settings(False)
        except Exception:
            self.preset_label.setText("Preset: error")
            self.preset_label.setStyleSheet("font-weight:700; color:#ff6b6b;")
            self.append_log(traceback.format_exc())

    def save_preset_to_project(self) -> None:
        try:
            result = save_project_workflow_preset(self.project_edit.text().strip(), self.current_preset_name())
            self.append_log(f"SAVED PROJECT PRESET: {result.get('preset_file')}")
            QMessageBox.information(self, "Saved", f"Đã lưu preset vào project:\n{result.get('preset_file')}")
        except Exception:
            QMessageBox.critical(self, "Preset error", traceback.format_exc())

    def load_preset_from_project(self) -> None:
        try:
            payload = load_project_workflow_preset(self.project_edit.text().strip())
            name = str(payload.get("name", ""))
            index = self.preset_combo.findData(name)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
            self.apply_preset_to_fields(save=True)
        except Exception:
            QMessageBox.critical(self, "Preset error", traceback.format_exc())

    def current_settings_dict(self) -> dict[str, Any]:
        size = self.size()
        return {
            "projects_root": self.projects_root_edit.text().strip(),
            "project_name": self.project_name_edit.text().strip(),
            "project_root": self.project_edit.text().strip(),
            "source_folder": self.source_edit.text().strip(),
            "target_duration": int(self.duration_spin.value()),
            "top_candidates": int(self.candidate_spin.value()),
            "live_manual_port": int(self.live_port_spin.value()),
            "keep_latest_exports": int(self.keep_exports_spin.value()),
            "preset_name": self.current_preset_name(),
            "window_width": int(size.width()),
            "window_height": int(size.height()),
        }

    def save_settings(self, show_popup: bool = False) -> None:
        try:
            path = self.settings_store.save(self.current_settings_dict())
            self.settings_label.setText("Settings: saved")
            self.settings_label.setStyleSheet("font-weight:700; color:#8ef0b0;")
            if show_popup:
                QMessageBox.information(self, "Saved", f"Đã lưu settings:\n{path}")
        except Exception:
            self.settings_label.setText("Settings: save error")
            self.settings_label.setStyleSheet("font-weight:700; color:#ff6b6b;")

    def reset_settings(self) -> None:
        ok = QMessageBox.question(self, "Reset settings?", "Xoá settings đã lưu và quay về mặc định ở lần mở app sau?")
        if ok == QMessageBox.StandardButton.Yes:
            self.settings_store.reset()
            QMessageBox.information(self, "Reset done", "Đã xoá settings. Đóng app và mở lại.")

    def open_settings_folder(self) -> None:
        self.settings_store.path.parent.mkdir(parents=True, exist_ok=True)
        os.startfile(self.settings_store.path.parent)

    def choose_projects_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn Projects Root", self.projects_root_edit.text())
        if folder:
            self.projects_root_edit.setText(folder); self.save_settings(False)

    def choose_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn Project Folder", self.project_edit.text())
        if folder:
            self.project_edit.setText(folder); self.save_settings(False); self.load_preset_from_project()

    def choose_source(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn Source Folder", self.source_edit.text())
        if folder:
            self.source_edit.setText(folder); self.save_settings(False)

    def create_new_project(self) -> None:
        projects_root = Path(self.projects_root_edit.text().strip())
        name = self.project_name_edit.text().strip()
        source_folder = Path(self.source_edit.text().strip()) if self.source_edit.text().strip() else None
        if not name:
            QMessageBox.warning(self, "Thiếu tên project", "Nhập Project name trước."); return
        projects_root.mkdir(parents=True, exist_ok=True)
        try:
            project = ProjectManager().create_project(projects_root=projects_root, name=name, source_folder=source_folder, overwrite=self.overwrite_project_check.isChecked())
            self.project_edit.setText(str(project.root).replace("\\", "/"))
            if source_folder: self.source_edit.setText(str(source_folder).replace("\\", "/"))
            self.save_preset_to_project()
            self.save_settings(False)
            QMessageBox.information(self, "Project created", f"Đã tạo project:\n{project.root}")
        except Exception:
            QMessageBox.critical(self, "Create project error", traceback.format_exc())
            self.append_log(traceback.format_exc())

    def run_final_wedding_v2_workflow(self) -> None:
        self.apply_preset_to_fields(save=True)
        self.auto_open_live_after_done = True
        self.append_log("FINAL WORKFLOW START")
        self.run_wedding_pipeline_v2()

    def run_pipeline(self) -> None:
        if self.from_scratch_check.isChecked():
            ok = QMessageBox.question(self, "Run from scratch?", "Chế độ này sẽ scan/detect/analyze lại. Có thể rất lâu. Chạy tiếp?")
            if ok != QMessageBox.StandardButton.Yes: return
        self.save_settings(False)
        self.start_worker("pipeline", {"project_root": self.project_edit.text().strip(), "source_folder": self.source_edit.text().strip(), "run_from_scratch": self.from_scratch_check.isChecked(), "target_duration": self.duration_spin.value(), "top_candidates": self.candidate_spin.value()})

    def run_wedding_pipeline_v2(self) -> None:
        self.save_settings(False)
        max_per = int(self.preset_values.get("max_segments_per_video", 1) or 1)
        self.start_worker("wedding_pipeline_v2", {"project_root": self.project_edit.text().strip(), "target_duration": self.duration_spin.value(), "max_segments_per_video": max_per})

    def generate_manual_review(self) -> None:
        self.start_worker("manual_review", {"project_root": self.project_edit.text().strip()})

    def export_manual_xml(self) -> None:
        project_root = Path(self.project_edit.text().strip())
        default_dir = str(project_root if (project_root / "manual_selection.json").exists() else Path.home() / "Downloads")
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn manual_selection.json", default_dir, "JSON files (*.json);;All files (*.*)")
        if file_path:
            self.start_worker("manual_export", {"project_root": str(project_root), "selection_json": file_path, **self.sequence_payload()})

    def sequence_payload(self) -> dict[str, int]:
        return {
            "sequence_fps": int(self.preset_values.get("sequence_fps", 25) or 25),
            "sequence_width": int(self.preset_values.get("sequence_width", 3840) or 3840),
            "sequence_height": int(self.preset_values.get("sequence_height", 2160) or 2160),
        }

    def open_live_manual_review(self) -> None:
        self.save_settings(False)
        project_root = Path(self.project_edit.text().strip())
        script = self.repo_root() / "scripts" / "run_live_manual_review.py"
        if not script.exists():
            QMessageBox.critical(self, "Thiếu Module 020", f"Không thấy file:\n{script}"); return
        port = int(self.live_port_spin.value())
        url = f"http://127.0.0.1:{port}"
        if self.live_manual_process and self.live_manual_process.poll() is None:
            webbrowser.open(url); return
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        try:
            self.live_manual_process = subprocess.Popen([sys.executable, str(script), "--port", str(port)], cwd=str(self.repo_root()), creationflags=creationflags)
            time.sleep(0.8)
            self.append_log(f"LIVE MANUAL SERVER STARTED: {url}")
            self.set_live_status(True)
            webbrowser.open(url)
        except Exception:
            QMessageBox.critical(self, "Không mở được Live Manual Review", traceback.format_exc())

    def stop_live_manual_server(self) -> None:
        proc = self.live_manual_process
        if not proc or proc.poll() is not None:
            self.set_live_status(False); self.append_log("Live Manual server hiện không chạy."); return
        try:
            proc.terminate() if os.name == "nt" else proc.send_signal(signal.SIGTERM)
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: proc.kill()
            self.set_live_status(False); self.append_log("LIVE MANUAL SERVER STOPPED")
        except Exception:
            QMessageBox.critical(self, "Không tắt được server", traceback.format_exc())

    def export_latest_manual_xml(self) -> None:
        project_root = Path(self.project_edit.text().strip())
        selection_json = project_root / "manual_selection.json"
        if not selection_json.exists():
            QMessageBox.warning(self, "Chưa thấy manual_selection.json", f"Chưa thấy file:\n{selection_json}\n\nMở Live Manual Review → KEEP/REJECT → Save to Project Folder trước.")
            return
        self.start_worker("manual_export", {"project_root": str(project_root), "selection_json": str(selection_json), **self.sequence_payload()})

    def preview_export_cleanup(self) -> None:
        self.start_worker("preview_exports", {"project_root": self.project_edit.text().strip(), "keep_latest_exports": self.keep_exports_spin.value()})

    def archive_old_exports(self) -> None:
        keep = self.keep_exports_spin.value()
        ok = QMessageBox.question(self, "Archive old exports?", f"Không xoá file. Giữ {keep} folder mới nhất mỗi loại, folder cũ chuyển vào exports\\_archive. Chạy tiếp?")
        if ok == QMessageBox.StandardButton.Yes:
            self.start_worker("archive_exports", {"project_root": self.project_edit.text().strip(), "keep_latest_exports": keep})

    def open_archive_folder(self) -> None:
        path = self.exports_dir() / "_archive"; path.mkdir(parents=True, exist_ok=True); os.startfile(path)

    def open_cleanup_reports(self) -> None:
        path = self.exports_dir() / "_cleanup_reports"; path.mkdir(parents=True, exist_ok=True); os.startfile(path)

    def set_live_status(self, running: bool) -> None:
        self.live_status_label.setText("Live Manual: ON" if running else "Live Manual: OFF")
        self.live_status_label.setStyleSheet("font-weight:700; color:#8ef0b0;" if running else "font-weight:700; color:#aaaab2;")

    def start_worker(self, action: str, payload: dict[str, Any]) -> None:
        project = Path(payload.get("project_root", ""))
        if not project.exists():
            QMessageBox.warning(self, "Sai project", f"Không thấy project folder:\n{project}"); return
        self.set_running(True); self.append_log("=" * 80); self.append_log(f"START: {action}")
        self.worker_thread = QThread(); self.worker = Worker(action, payload); self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run); self.worker.log.connect(self.append_log); self.worker.done.connect(self.worker_done); self.worker.error.connect(self.worker_error)
        self.worker.done.connect(self.worker_thread.quit); self.worker.error.connect(self.worker_thread.quit); self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def worker_done(self, result: dict) -> None:
        self.last_result = result; self.append_log("DONE"); self.append_log(str(result)); self.set_running(False)
        if "archive_count" in result:
            report = result.get("report_json", "")
            if report and Path(report).exists(): os.startfile(Path(report).parent)
            return
        if self.auto_open_live_after_done:
            self.auto_open_live_after_done = False; self.open_live_manual_review(); return
        html = result.get("manual_review_html") or result.get("review_html") or result.get("html")
        if not html and isinstance(result.get("review"), dict): html = result["review"].get("html")
        if html and Path(html).exists(): os.startfile(html)

    def worker_error(self, message: str) -> None:
        self.auto_open_live_after_done = False; self.append_log("ERROR"); self.append_log(message); self.set_running(False); QMessageBox.critical(self, "Error", message[-4000:])

    def set_running(self, running: bool) -> None:
        for attr in ["run_final_v2_btn", "run_pipeline_btn", "run_wedding_v2_btn", "manual_review_btn", "manual_export_btn", "export_latest_manual_btn", "export_latest_big_btn", "preview_cleanup_btn", "archive_cleanup_btn"]:
            if hasattr(self, attr): getattr(self, attr).setDisabled(running)
        self.status_label.setText("Running..." if running else "Ready")
        self.status_label.setStyleSheet("font-weight:700; color:#ffd166;" if running else "font-weight:700; color:#8ef0b0;")

    def append_log(self, text: str) -> None:
        self.log_box.appendPlainText(text)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def project_dir(self) -> Path:
        return Path(self.project_edit.text().strip())

    def exports_dir(self) -> Path:
        return self.project_dir() / "exports"

    def open_project_folder(self) -> None:
        path = self.project_dir()
        if path.exists(): os.startfile(path)

    def open_exports(self) -> None:
        path = self.exports_dir()
        if path.exists(): os.startfile(path)

    def open_latest(self, filename: str) -> None:
        files = sorted(self.exports_dir().glob(f"**/{filename}"), key=lambda p: p.stat().st_mtime, reverse=True) if self.exports_dir().exists() else []
        if files: os.startfile(files[0])
        else: QMessageBox.warning(self, "Không thấy file", f"Không thấy {filename}")

    def open_latest_xml_folder(self) -> None:
        files = sorted(self.exports_dir().glob("**/stt_ai_premiere_import.xml"), key=lambda p: p.stat().st_mtime, reverse=True) if self.exports_dir().exists() else []
        if files: os.startfile(files[0].parent)
        else: QMessageBox.warning(self, "Không thấy XML", "Không thấy stt_ai_premiere_import.xml")

    def closeEvent(self, event) -> None:
        self.save_settings(False)
        if self.live_manual_process and self.live_manual_process.poll() is None:
            try: self.live_manual_process.terminate()
            except Exception: pass
        super().closeEvent(event)


def run_gui() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = STTAIEditorWindow()
    window.show()
    app.exec()
