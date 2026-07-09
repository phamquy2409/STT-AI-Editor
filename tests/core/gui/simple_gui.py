from __future__ import annotations

import contextlib
import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.exporter import export_premiere_xml_existing_project
from core.manual_export import build_manual_selection_existing_project
from core.manual_review import generate_manual_review_existing_project
from core.pipeline import run_one_click_pipeline_existing_project
from core.project import ProjectManager
from core.review import generate_preview_review_existing_project


@dataclass
class GuiDefaults:
    projects_root: str = "D:/STT Projects"
    project_name: str = "Wedding_Test_001"
    project_root: str = "D:/STT Projects/Wedding_Test_001"
    source_folder: str = "D:/5thang5test"
    target_duration: int = 60
    top_candidates: int = 120


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

        if self.action == "manual_review":
            return generate_manual_review_existing_project(project_root=project_root, input_json=None)

        if self.action == "manual_export":
            selection_json = self.payload.get("selection_json")
            if not selection_json:
                raise RuntimeError("No manual_selection.json selected.")

            manual = build_manual_selection_existing_project(
                project_root=project_root,
                selection_json=Path(selection_json),
            )

            xml = export_premiere_xml_existing_project(
                project_root=project_root,
                roughcut_json=Path(manual["manual_json"]),
                sequence_fps=25,
                sequence_width=3840,
                sequence_height=2160,
            )

            review = generate_preview_review_existing_project(
                project_root=project_root,
                roughcut_json=Path(manual["manual_json"]),
            )

            return {
                "manual": manual,
                "xml": xml,
                "review": review,
                "premiere_xml": xml.get("xml", ""),
                "review_html": review.get("html", ""),
                "output_dir": manual.get("output_dir", ""),
            }

        raise RuntimeError(f"Unknown action: {self.action}")


class STTAIEditorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.defaults = GuiDefaults()
        self.worker_thread: QThread | None = None
        self.worker: Worker | None = None
        self.last_result: dict[str, Any] = {}

        self.setWindowTitle("STT AI Editor")
        self.resize(1100, 820)

        # Project creator fields
        self.projects_root_edit = QLineEdit(self.defaults.projects_root)
        self.project_name_edit = QLineEdit(self.defaults.project_name)
        self.overwrite_project_check = QCheckBox("Overwrite nếu project đã tồn tại")
        self.overwrite_project_check.setChecked(False)

        # Active project fields
        self.project_edit = QLineEdit(self.defaults.project_root)
        self.source_edit = QLineEdit(self.defaults.source_folder)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 600)
        self.duration_spin.setValue(self.defaults.target_duration)
        self.duration_spin.setSuffix(" sec")

        self.candidate_spin = QSpinBox()
        self.candidate_spin.setRange(20, 1000)
        self.candidate_spin.setValue(self.defaults.top_candidates)

        self.from_scratch_check = QCheckBox("Run from scratch: scan / detect / analyze lại")
        self.from_scratch_check.setChecked(False)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight:700; color:#8ef0b0;")

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.addWidget(self._build_create_project_box())
        layout.addWidget(self._build_active_project_box())
        layout.addWidget(self._build_action_box())
        layout.addWidget(self._build_open_box())
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log_box, 1)

        self._apply_style()

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

    def _build_action_box(self) -> QGroupBox:
        box = QGroupBox("Run")
        row = QHBoxLayout(box)

        self.run_pipeline_btn = QPushButton("Run Pipeline")
        self.run_pipeline_btn.clicked.connect(self.run_pipeline)

        self.manual_review_btn = QPushButton("Generate Manual Review")
        self.manual_review_btn.clicked.connect(self.generate_manual_review)

        self.manual_export_btn = QPushButton("Export Manual XML")
        self.manual_export_btn.clicked.connect(self.export_manual_xml)

        row.addWidget(self.run_pipeline_btn)
        row.addWidget(self.manual_review_btn)
        row.addWidget(self.manual_export_btn)
        row.addStretch(1)
        row.addWidget(self.status_label)

        return box

    def _build_open_box(self) -> QGroupBox:
        box = QGroupBox("Open")
        row = QHBoxLayout(box)

        btn_project = QPushButton("Open Project")
        btn_project.clicked.connect(self.open_project_folder)

        btn_exports = QPushButton("Open Exports")
        btn_exports.clicked.connect(self.open_exports)

        btn_review = QPushButton("Open Latest Review")
        btn_review.clicked.connect(lambda: self.open_latest("review.html"))

        btn_manual = QPushButton("Open Latest Manual Review")
        btn_manual.clicked.connect(lambda: self.open_latest("manual_review.html"))

        btn_xml = QPushButton("Open Latest XML Folder")
        btn_xml.clicked.connect(self.open_latest_xml_folder)

        btn_clear = QPushButton("Clear Log")
        btn_clear.clicked.connect(self.log_box.clear)

        row.addWidget(btn_project)
        row.addWidget(btn_exports)
        row.addWidget(btn_review)
        row.addWidget(btn_manual)
        row.addWidget(btn_xml)
        row.addStretch(1)
        row.addWidget(btn_clear)

        return box

    def _apply_style(self) -> None:
        self.setStyleSheet("""
        QMainWindow, QWidget {
            background:#101014;
            color:#f5f5f7;
            font-size:13px;
        }
        QGroupBox {
            border:1px solid #33333d;
            border-radius:12px;
            margin-top:10px;
            padding:12px;
            font-weight:700;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left:12px;
            padding:0 8px;
        }
        QLineEdit, QPlainTextEdit, QSpinBox {
            background:#17171d;
            color:#f5f5f7;
            border:1px solid #33333d;
            border-radius:9px;
            padding:8px;
        }
        QPushButton {
            background:#202028;
            color:#f5f5f7;
            border:1px solid #3d3d48;
            border-radius:10px;
            padding:9px 13px;
            font-weight:700;
        }
        QPushButton:hover {
            background:#2b2b35;
        }
        QPushButton:disabled {
            color:#777780;
            background:#17171d;
        }
        QLabel {
            color:#d8d8de;
        }
        QCheckBox {
            color:#ffd166;
        }
        """)

    def choose_projects_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn Projects Root", self.projects_root_edit.text())
        if folder:
            self.projects_root_edit.setText(folder)

    def choose_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn Project Folder", self.project_edit.text())
        if folder:
            self.project_edit.setText(folder)

    def choose_source(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn Source Folder", self.source_edit.text())
        if folder:
            self.source_edit.setText(folder)

    def create_new_project(self) -> None:
        projects_root = Path(self.projects_root_edit.text().strip())
        name = self.project_name_edit.text().strip()
        source_text = self.source_edit.text().strip()
        source_folder = Path(source_text) if source_text else None

        if not projects_root.exists():
            try:
                projects_root.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                QMessageBox.critical(self, "Không tạo được folder", str(exc))
                return

        if not name:
            QMessageBox.warning(self, "Thiếu tên project", "Nhập Project name trước.")
            return

        if self.overwrite_project_check.isChecked():
            ok = QMessageBox.question(
                self,
                "Overwrite project?",
                "Overwrite sẽ xoá/ghi đè project trùng tên nếu core project manager cho phép. Chạy tiếp?",
            )
            if ok != QMessageBox.StandardButton.Yes:
                return

        try:
            manager = ProjectManager()
            project = manager.create_project(
                projects_root=projects_root,
                name=name,
                source_folder=source_folder,
                overwrite=self.overwrite_project_check.isChecked(),
            )

            self.project_edit.setText(str(project.root).replace("\\", "/"))
            if source_folder:
                self.source_edit.setText(str(source_folder).replace("\\", "/"))

            self.append_log("")
            self.append_log("PROJECT CREATED")
            self.append_log(f"Name: {project.name}")
            self.append_log(f"Root: {project.root}")
            self.append_log("")

            QMessageBox.information(
                self,
                "Project created",
                f"Đã tạo project:\n{project.root}\n\nProject này đã được set làm Active Project.",
            )

        except Exception as exc:
            QMessageBox.critical(self, "Create project error", traceback.format_exc())
            self.append_log("CREATE PROJECT ERROR")
            self.append_log(traceback.format_exc())

    def run_pipeline(self) -> None:
        if self.from_scratch_check.isChecked():
            ok = QMessageBox.question(
                self,
                "Run from scratch?",
                "Chế độ này sẽ scan/detect/analyze lại. Có thể rất lâu. Chạy tiếp?",
            )
            if ok != QMessageBox.StandardButton.Yes:
                return

        payload = {
            "project_root": self.project_edit.text().strip(),
            "source_folder": self.source_edit.text().strip(),
            "run_from_scratch": self.from_scratch_check.isChecked(),
            "target_duration": self.duration_spin.value(),
            "top_candidates": self.candidate_spin.value(),
        }

        self.start_worker("pipeline", payload)

    def generate_manual_review(self) -> None:
        payload = {"project_root": self.project_edit.text().strip()}
        self.start_worker("manual_review", payload)

    def export_manual_xml(self) -> None:
        default_dir = str(Path.home() / "Downloads")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn manual_selection.json",
            default_dir,
            "JSON files (*.json);;All files (*.*)",
        )

        if not file_path:
            return

        payload = {
            "project_root": self.project_edit.text().strip(),
            "selection_json": file_path,
        }

        self.start_worker("manual_export", payload)

    def start_worker(self, action: str, payload: dict[str, Any]) -> None:
        project = Path(payload.get("project_root", ""))
        if not project.exists():
            QMessageBox.warning(self, "Sai project", f"Không thấy project folder:\n{project}")
            return

        self.set_running(True)
        self.append_log("")
        self.append_log("=" * 80)
        self.append_log(f"START: {action}")

        self.worker_thread = QThread()
        self.worker = Worker(action, payload)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log.connect(self.append_log)
        self.worker.done.connect(self.worker_done)
        self.worker.error.connect(self.worker_error)
        self.worker.done.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def worker_done(self, result: dict) -> None:
        self.last_result = result
        self.append_log("DONE")
        self.append_log(str(result))
        self.set_running(False)

        html = (
            result.get("manual_review_html")
            or result.get("review_html")
            or result.get("html")
        )

        if not html and isinstance(result.get("review"), dict):
            html = result["review"].get("html")

        if html and Path(html).exists():
            os.startfile(html)

    def worker_error(self, message: str) -> None:
        self.append_log("ERROR")
        self.append_log(message)
        self.set_running(False)
        QMessageBox.critical(self, "Error", message[-4000:])

    def set_running(self, running: bool) -> None:
        self.run_pipeline_btn.setDisabled(running)
        self.manual_review_btn.setDisabled(running)
        self.manual_export_btn.setDisabled(running)
        self.status_label.setText("Running..." if running else "Ready")
        self.status_label.setStyleSheet(
            "font-weight:700; color:#ffd166;" if running else "font-weight:700; color:#8ef0b0;"
        )

    def append_log(self, text: str) -> None:
        self.log_box.appendPlainText(text)
        bar = self.log_box.verticalScrollBar()
        bar.setValue(bar.maximum())

    def project_dir(self) -> Path:
        return Path(self.project_edit.text().strip())

    def exports_dir(self) -> Path:
        return self.project_dir() / "exports"

    def open_project_folder(self) -> None:
        path = self.project_dir()
        if path.exists():
            os.startfile(path)
        else:
            QMessageBox.warning(self, "Không thấy project", str(path))

    def open_exports(self) -> None:
        path = self.exports_dir()
        if path.exists():
            os.startfile(path)
        else:
            QMessageBox.warning(self, "Không thấy folder", str(path))

    def open_latest(self, filename: str) -> None:
        exports = self.exports_dir()
        if not exports.exists():
            QMessageBox.warning(self, "Không thấy exports", str(exports))
            return

        files = sorted(exports.glob(f"**/{filename}"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not files:
            QMessageBox.warning(self, "Không thấy file", f"Không thấy {filename}")
            return

        os.startfile(files[0])

    def open_latest_xml_folder(self) -> None:
        exports = self.exports_dir()
        if not exports.exists():
            QMessageBox.warning(self, "Không thấy exports", str(exports))
            return

        files = sorted(exports.glob("**/stt_ai_premiere_import.xml"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not files:
            QMessageBox.warning(self, "Không thấy XML", "Không thấy stt_ai_premiere_import.xml")
            return

        os.startfile(files[0].parent)


def run_gui() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = STTAIEditorWindow()
    window.show()
    app.exec()
