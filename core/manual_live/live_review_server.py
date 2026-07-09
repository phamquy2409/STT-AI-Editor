
from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import urllib.parse
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

from core.manual_review import ModernManualReviewGenerator
from core.project import ProjectManager


class LiveManualReviewServer:
    # Module 034C.
    # Adds background/in-process server support for PyInstaller EXE.
    #
    # Why:
    # In EXE mode, sys.executable is STT AI Editor.exe, not python.exe.
    # Starting run_live_manual_review.py through sys.executable can fail.
    #
    # Fix:
    # GUI can now create LiveManualReviewServer(...) and run it in a background thread.

    def __init__(self, project_root: str | Path, port: int = 8787, input_json: str | Path | None = None) -> None:
        self.project_root = Path(project_root)
        self.port = int(port)
        self.input_json = Path(input_json) if input_json else None
        self.media_map: dict[str, Path] = {}
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.is_running = False

        self.project = ProjectManager().open_project(self.project_root)

        generator = ModernManualReviewGenerator(project=self.project, input_json=self.input_json)
        self.input_json = generator.input_json
        self.items = generator._prepare_items(generator._load_rows(generator.input_json), generator.input_json.parent)

        self.save_dir = generator.input_json.parent
        self.project_selection_path = self.project_root / "manual_selection.json"
        self.generated_thumb_dir = self.save_dir / "_live_thumbnails"
        self.generated_thumb_dir.mkdir(parents=True, exist_ok=True)

        self._prepare_media_urls()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start_background(self, open_browser: bool = False) -> None:
        if self.thread and self.thread.is_alive():
            if open_browser:
                webbrowser.open(self.url)
            return

        self.thread = threading.Thread(
            target=lambda: self.serve(open_browser=open_browser),
            name=f"STTLiveManualReview-{self.port}",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.is_running = False
        if self.httpd is not None:
            try:
                self.httpd.shutdown()
            except Exception:
                pass
            try:
                self.httpd.server_close()
            except Exception:
                pass
        self.httpd = None

    def _prepare_media_urls(self) -> None:
        for index, item in enumerate(self.items, start=1):
            video_path = self._find_video_path(item)
            thumb_path = self._find_thumbnail_path(item, index)

            if not thumb_path and video_path:
                thumb_path = self._generate_thumbnail_from_video(item=item, video_path=video_path, index=index)

            if thumb_path:
                media_id = f"thumb_{index:04d}"
                self.media_map[media_id] = thumb_path
                item["thumbnail_url"] = f"/media/{media_id}"
            else:
                item["thumbnail_url"] = ""

            if video_path:
                media_id = f"video_{index:04d}"
                self.media_map[media_id] = video_path
                item["video_url"] = f"/media/{media_id}"
            else:
                item["video_url"] = ""

    def _find_thumbnail_path(self, item: dict[str, Any], index: int) -> Path | None:
        candidates: list[Path] = []

        thumb = str(item.get("thumbnail", "")).strip()
        if thumb:
            p = Path(thumb)
            if p.is_absolute():
                candidates.append(p)
            else:
                candidates.append(self.input_json.parent / p)

        order = int(float(item.get("order", index) or index))

        possible_parents = [
            self.input_json.parent,
            self.save_dir,
            self.project_root / "exports",
        ]

        exports_dir = self.project_root / "exports"
        if exports_dir.exists():
            possible_parents.extend([p for p in exports_dir.iterdir() if p.is_dir() and p.name != "_archive"])

        for parent in possible_parents:
            candidates.append(parent / "preview_thumbnails" / f"thumb_{order:03d}.jpg")
            candidates.append(parent / "preview_thumbnails" / f"thumb_{index:03d}.jpg")
            candidates.append(parent / "thumbnails" / f"thumb_{order:03d}.jpg")
            candidates.append(parent / "thumbnails" / f"thumb_{index:03d}.jpg")
            candidates.append(parent / "_live_thumbnails" / f"live_thumb_{index:04d}.jpg")

        seen: set[str] = set()
        for p in candidates:
            key = str(p)
            if key in seen:
                continue
            seen.add(key)
            if p.exists() and p.is_file() and p.stat().st_size > 0:
                return p

        return None

    @staticmethod
    def _find_video_path(item: dict[str, Any]) -> Path | None:
        video = str(item.get("video_path", "")).strip()
        if not video:
            return None

        p = Path(video)
        if p.exists() and p.is_file():
            return p

        return None

    def _generate_thumbnail_from_video(self, item: dict[str, Any], video_path: Path, index: int) -> Path | None:
        if cv2 is None:
            print(f"[LiveManual] cv2 unavailable, cannot generate thumbnail for {video_path}")
            return None

        out_path = self.generated_thumb_dir / f"live_thumb_{index:04d}.jpg"
        if out_path.exists() and out_path.stat().st_size > 0:
            return out_path

        start_seconds = self._num(item, "source_start_seconds", 0.0)
        grab_seconds = max(0.0, start_seconds + 0.35)

        cap = None
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                print(f"[LiveManual] cannot open video for thumbnail: {video_path}")
                return None

            fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
            frame_index = int(grab_seconds * fps)

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()

            if not ok or frame is None:
                cap.set(cv2.CAP_PROP_POS_MSEC, grab_seconds * 1000.0)
                ok, frame = cap.read()

            if not ok or frame is None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = cap.read()

            if not ok or frame is None:
                print(f"[LiveManual] cannot read frame for thumbnail: {video_path}")
                return None

            h, w = frame.shape[:2]
            if w <= 0 or h <= 0:
                return None

            target_w = 640
            scale = target_w / float(w)
            target_h = max(1, int(h * scale))
            resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

            ok = cv2.imwrite(str(out_path), resized, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
            if not ok:
                return None

            print(f"[LiveManual] generated thumbnail: {out_path}")
            return out_path

        except Exception as exc:
            print(f"[LiveManual] thumbnail generation error for {video_path}: {exc!r}")
            return None

        finally:
            if cap is not None:
                cap.release()

    def serve(self, open_browser: bool = True) -> None:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, code: int, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                parsed = urllib.parse.urlparse(self.path)

                if parsed.path in {"/", "/index.html"}:
                    self._send(200, outer.render_live_html().encode("utf-8"))
                    return

                if parsed.path == "/api/items":
                    self._send(
                        200,
                        json.dumps({"items": outer.items}, ensure_ascii=False, indent=2).encode("utf-8"),
                        "application/json; charset=utf-8",
                    )
                    return

                if parsed.path.startswith("/media/"):
                    media_id = parsed.path.split("/media/", 1)[1]
                    media_id = urllib.parse.unquote(media_id)
                    media_path = outer.media_map.get(media_id)

                    if not media_path or not media_path.exists():
                        self._send(404, b"Media not found", "text/plain")
                        return

                    try:
                        content_type = mimetypes.guess_type(str(media_path))[0] or "application/octet-stream"
                        data = media_path.read_bytes()
                        self._send(200, data, content_type)
                    except Exception as exc:
                        self._send(500, f"Media read error: {exc!r}".encode("utf-8"), "text/plain")
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
                    self._send(
                        200,
                        json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"),
                        "application/json; charset=utf-8",
                    )
                except Exception as exc:
                    self._send(
                        500,
                        json.dumps({"ok": False, "error": repr(exc)}, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8",
                    )

            def log_message(self, format: str, *args: Any) -> None:
                print(f"[LiveManual] {format % args}")

        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self.is_running = True

        thumb_count = sum(1 for item in self.items if item.get("thumbnail_url"))
        print("STT AI Live Manual Review")
        print(f"Project: {self.project_root}")
        print(f"Input: {self.input_json}")
        print(f"Items: {len(self.items)}")
        print(f"Thumbnails available: {thumb_count}/{len(self.items)}")
        print(f"Media files: {len(self.media_map)}")
        print(f"URL: {self.url}")
        print("Press Ctrl+C or Stop Live Server to stop.")

        if open_browser:
            webbrowser.open(self.url)

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.is_running = False
            try:
                if self.httpd is not None:
                    self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None
            print("Live Manual Review stopped.")

    def run(self) -> None:
        self.serve(open_browser=True)

    def save_selection(self, payload: dict[str, Any], autosave: bool = False) -> dict[str, Any]:
        payload = dict(payload)
        payload["project_root"] = str(self.project_root)
        payload["source"] = str(self.input_json)
        payload["saved_at"] = datetime.now().isoformat(timespec="seconds")
        payload["ui"] = "module_034c_live_manual_review_inprocess"

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
        temp_generator = ModernManualReviewGenerator(project=self.project, input_json=self.input_json)
        html = temp_generator._render_html(self.items)
        html = html.replace("STT AI Manual Review", "STT AI Live Manual Review")
        html = html.replace(
            '<button class="primary" onclick="downloadSelection()">Export JSON</button>',
            '<button class="primary" onclick="downloadSelection()">Export JSON</button><button class="keep" onclick="saveToProject()">Save to Project Folder</button>',
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
        return html.replace("</body></html>", save_js + "</body></html>")

    @staticmethod
    def _num(row: dict[str, Any], key: str, default: float = 0.0) -> float:
        try:
            value = row.get(key, default)
            if value is None:
                return default
            return float(value)
        except Exception:
            return default


def run_live_manual_review_server(
    project_root: str | Path = "D:/STT Projects/Wedding_Test_001",
    port: int = 8787,
    input_json: str | Path | None = None,
) -> None:
    LiveManualReviewServer(project_root=project_root, port=port, input_json=input_json).run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STT AI Live Manual Review server.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--input-json", default=None)
    args = parser.parse_args()

    run_live_manual_review_server(
        project_root=args.project,
        port=args.port,
        input_json=args.input_json,
    )


if __name__ == "__main__":
    main()
