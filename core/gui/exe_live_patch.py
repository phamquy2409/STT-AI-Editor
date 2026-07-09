
from __future__ import annotations

import time
import traceback
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import QMessageBox


def apply_live_server_patch(window_class) -> None:
    old_close_event = getattr(window_class, "closeEvent", None)

    def open_live_manual_review(self) -> None:
        # Save GUI settings if method exists.
        try:
            if hasattr(self, "save_settings"):
                self.save_settings(show_popup=False)
        except TypeError:
            try:
                self.save_settings(False)
            except Exception:
                pass
        except Exception:
            pass

        project_root = Path(self.project_edit.text().strip())
        if not project_root.exists():
            QMessageBox.warning(self, "Sai project", f"Không thấy project folder:\n{project_root}")
            return

        port = int(self.live_port_spin.value())
        url = f"http://127.0.0.1:{port}"

        server = getattr(self, "live_manual_server", None)
        if server is not None and getattr(server, "is_running", False):
            self.append_log(f"Live Manual server đang chạy. Mở lại: {url}")
            webbrowser.open(url)
            return

        try:
            from core.manual_live.live_review_server import LiveManualReviewServer

            server = LiveManualReviewServer(project_root=project_root, port=port)
            server.start_background(open_browser=False)

            self.live_manual_server = server
            self.live_manual_process = None

            time.sleep(1.0)

            self.append_log("")
            self.append_log("LIVE MANUAL REVIEW SERVER STARTED IN-PROCESS")
            self.append_log(f"URL: {url}")
            self.append_log("Trong browser: KEEP / REJECT → Save to Project Folder.")
            self.append_log("Sau đó quay lại GUI bấm Export Latest Manual XML.")

            if hasattr(self, "set_live_status"):
                self.set_live_status(True)

            webbrowser.open(url)

        except Exception:
            msg = traceback.format_exc()
            self.append_log("LIVE MANUAL SERVER ERROR")
            self.append_log(msg)
            if hasattr(self, "set_live_status"):
                self.set_live_status(False)
            QMessageBox.critical(self, "Không mở được Live Manual Review", msg[-4000:])

    def stop_live_manual_server(self) -> None:
        server = getattr(self, "live_manual_server", None)

        if server is not None and getattr(server, "is_running", False):
            try:
                server.stop()
                self.append_log("LIVE MANUAL REVIEW SERVER STOPPED")
                if hasattr(self, "set_live_status"):
                    self.set_live_status(False)
                return
            except Exception:
                msg = traceback.format_exc()
                self.append_log("STOP LIVE SERVER ERROR")
                self.append_log(msg)
                QMessageBox.critical(self, "Không tắt được server", msg[-4000:])
                return

        # Fallback to old subprocess behavior if user is running source version.
        proc = getattr(self, "live_manual_process", None)
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()
                self.append_log("LIVE MANUAL REVIEW SERVER STOPPED")
                if hasattr(self, "set_live_status"):
                    self.set_live_status(False)
                return
            except Exception:
                msg = traceback.format_exc()
                self.append_log("STOP LIVE SERVER ERROR")
                self.append_log(msg)
                QMessageBox.critical(self, "Không tắt được server", msg[-4000:])
                return

        self.append_log("Live Manual server hiện không chạy.")
        if hasattr(self, "set_live_status"):
            self.set_live_status(False)

    def closeEvent(self, event) -> None:
        try:
            server = getattr(self, "live_manual_server", None)
            if server is not None and getattr(server, "is_running", False):
                server.stop()
        except Exception:
            pass

        if old_close_event is not None:
            old_close_event(self, event)
        else:
            event.accept()

    window_class.open_live_manual_review = open_live_manual_review
    window_class.stop_live_manual_server = stop_live_manual_server
    window_class.closeEvent = closeEvent
