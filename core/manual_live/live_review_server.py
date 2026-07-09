
from __future__ import annotations

import argparse
import json
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from core.manual_review import ModernManualReviewGenerator
from core.project import ProjectManager


class LiveManualReviewServer:
    def __init__(self, project_root: str | Path, port: int = 8787, input_json: str | Path | None = None) -> None:
        self.project_root = Path(project_root)
        self.port = int(port)
        self.input_json = Path(input_json) if input_json else None

        self.project = ProjectManager().open_project(self.project_root)
        generator = ModernManualReviewGenerator(project=self.project, input_json=self.input_json)
        self.input_json = generator.input_json
        self.items = generator._prepare_items(generator._load_rows(generator.input_json), generator.input_json.parent)

        self.save_dir = generator.input_json.parent
        self.project_selection_path = self.project_root / "manual_selection.json"

    def run(self) -> None:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, code: int, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                if self.path in {"/", "/index.html"}:
                    self._send(200, outer.render_live_html().encode("utf-8"))
                    return
                if self.path == "/api/items":
                    self._send(200, json.dumps({"items": outer.items}, ensure_ascii=False, indent=2).encode("utf-8"), "application/json; charset=utf-8")
                    return
                self._send(404, b"Not found", "text/plain")

            def do_POST(self) -> None:
                if self.path not in {"/api/save", "/api/autosave"}:
                    self._send(404, b"Not found", "text/plain")
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    result = outer.save_selection(payload, autosave=(self.path == "/api/autosave"))
                    self._send(200, json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"), "application/json; charset=utf-8")
                except Exception as exc:
                    self._send(500, json.dumps({"ok": False, "error": repr(exc)}, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

            def log_message(self, format: str, *args: Any) -> None:
                print(f"[LiveManual] {format % args}")

        httpd = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        url = f"http://127.0.0.1:{self.port}"

        print("STT AI Live Manual Review")
        print(f"Project: {self.project_root}")
        print(f"Input: {self.input_json}")
        print(f"Items: {len(self.items)}")
        print(f"URL: {url}")
        print("Press Ctrl+C to stop server.")
        webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
            print("Live Manual Review stopped.")

    def save_selection(self, payload: dict[str, Any], autosave: bool = False) -> dict[str, Any]:
        payload = dict(payload)
        payload["project_root"] = str(self.project_root)
        payload["source"] = str(self.input_json)
        payload["saved_at"] = datetime.now().isoformat(timespec="seconds")
        payload["ui"] = "module_031_live_manual_review"

        name = "manual_selection_autosave.json" if autosave else "manual_selection.json"
        path = self.save_dir / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        alias_path = ""
        if not autosave:
            self.project_selection_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            alias_path = str(self.project_selection_path)

        counts = {"keep": 0, "maybe": 0, "reject": 0, "unset": 0, "liked": 0}
        for item in payload.get("items", []):
            status = str(item.get("status", "unset")).lower()
            counts[status] = counts.get(status, 0) + 1
            if item.get("liked"):
                counts["liked"] += 1

        return {"ok": True, "autosave": autosave, "path": str(path), "project_alias": alias_path, "counts": counts}

    def render_live_html(self) -> str:
        # Reuse the modern manual review page, then inject direct-save buttons/js.
        temp_generator = ModernManualReviewGenerator(project=self.project, input_json=self.input_json)
        html = temp_generator._render_html(self.items)
        html = html.replace("STT AI Manual Review", "STT AI Live Manual Review")
        html = html.replace(
            '<button class="primary" onclick="downloadSelection()">Export JSON</button>',
            '<button class="primary" onclick="downloadSelection()">Export JSON</button><button class="keep" onclick="saveToProject()">Save to Project Folder</button>'
        )
        save_js = """
<script>
async function saveToProject(autosave=false) {
  try {
    const res = await fetch(autosave ? '/api/autosave' : '/api/save', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload())
    });
    const data = await res.json();
    if (!autosave) alert('Saved OK\\n' + data.path + '\\n' + (data.project_alias || ''));
  } catch (e) {
    if (!autosave) alert('Save error: ' + e);
  }
}
setInterval(() => saveToProject(true), 20000);
</script>
"""
        html = html.replace("</body></html>", save_js + "</body></html>")
        return html


def run_live_manual_review_server(project_root: str | Path = "D:/STT Projects/Wedding_Test_001", port: int = 8787, input_json: str | Path | None = None) -> None:
    LiveManualReviewServer(project_root=project_root, port=port, input_json=input_json).run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STT AI Live Manual Review server.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--input-json", default=None)
    args = parser.parse_args()
    run_live_manual_review_server(project_root=args.project, port=args.port, input_json=args.input_json)


if __name__ == "__main__":
    main()
