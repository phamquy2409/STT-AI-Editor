from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from core.project import ProjectManager, STTProject


@dataclass
class LiveManualReviewConfig:
    host: str = "127.0.0.1"
    port: int = 8787


class LiveManualReviewServer:
    # Build 020.
    # Local browser review with direct save to project folder.
    # No manual Export JSON to Downloads required.

    def __init__(
        self,
        project: STTProject,
        input_json: str | Path | None = None,
        config: LiveManualReviewConfig | None = None,
    ) -> None:
        self.project = project
        self.input_json = Path(input_json) if input_json else self._find_latest_input_json()
        self.config = config or LiveManualReviewConfig()
        self.output_dir = self.input_json.parent
        self.selection_json = self.output_dir / "manual_selection.json"
        self.autosave_json = self.output_dir / "manual_selection_autosave.json"
        self.server: ThreadingHTTPServer | None = None

    def start_blocking(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Input json not found: {self.input_json}")

        handler = self._make_handler()
        self.server = ThreadingHTTPServer((self.config.host, self.config.port), handler)
        url = f"http://{self.config.host}:{self.config.port}/"

        print("STT AI Live Manual Review Server")
        print(f"Project: {self.project.name}")
        print(f"Input: {self.input_json}")
        print(f"URL: {url}")
        print(f"Save file: {self.selection_json}")
        print("-" * 60)
        print("Opening browser ...")
        print("Close this server with Ctrl+C when done.")
        print("-" * 60)

        try:
            os.startfile(url)
        except Exception:
            pass

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print()
            print("Stopping live manual review server ...")
        finally:
            self.server.server_close()

        return {
            "url": url,
            "input_json": str(self.input_json),
            "selection_json": str(self.selection_json),
            "autosave_json": str(self.autosave_json),
            "output_dir": str(self.output_dir),
        }

    def start_in_background(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Input json not found: {self.input_json}")

        handler = self._make_handler()
        self.server = ThreadingHTTPServer((self.config.host, self.config.port), handler)
        url = f"http://{self.config.host}:{self.config.port}/"

        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()

        try:
            os.startfile(url)
        except Exception:
            pass

        return {
            "url": url,
            "input_json": str(self.input_json),
            "selection_json": str(self.selection_json),
            "autosave_json": str(self.autosave_json),
            "output_dir": str(self.output_dir),
        }

    def _find_latest_input_json(self) -> Path:
        patterns = [
            "story_timeline_*/roughcut_story.json",
            "story_timeline_*/roughcut_plan.json",
            "manual_final_*/manual_roughcut.json",
            "manual_final_*/roughcut_plan.json",
            "final_roughcut_*/roughcut_final.json",
            "expanded_candidates_*/roughcut_plan_people_composition.json",
            "roughcut_*/roughcut_plan_people_composition.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan.json"

        return candidates[0]

    def _load_items(self) -> list[dict[str, Any]]:
        payload = json.loads(self.input_json.read_text(encoding="utf-8"))

        if isinstance(payload, list):
            rows = [dict(x) for x in payload if isinstance(x, dict)]
        elif isinstance(payload, dict) and isinstance(payload.get("segments"), list):
            rows = [dict(x) for x in payload["segments"] if isinstance(x, dict)]
        elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
            rows = [dict(x) for x in payload["items"] if isinstance(x, dict)]
        else:
            raise RuntimeError(f"Unsupported json format: {self.input_json}")

        prepared: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            item = dict(row)
            order = int(float(item.get("order", index)))
            video_path = str(item.get("video_path", ""))
            filename = str(item.get("video_filename", "")) or Path(video_path).name

            start = float(item.get("source_start_seconds", 0.0))
            end = float(item.get("source_end_seconds", start))
            duration = float(item.get("duration_seconds", end - start))

            if end <= start and duration > 0:
                end = start + duration

            item["order"] = order
            item["video_filename"] = filename
            item["source_start_seconds"] = round(start, 3)
            item["source_end_seconds"] = round(end, 3)
            item["duration_seconds"] = round(max(0.0, end - start), 3)
            item["review_id"] = self._review_id(item)
            item["thumbnail"] = str(item.get("thumbnail", f"preview_thumbnails/thumb_{order:03d}.jpg"))
            prepared.append(item)

        return prepared

    @staticmethod
    def _review_id(item: dict[str, Any]) -> str:
        safe_name = str(item.get("video_filename", "clip")).replace(" ", "_")
        order = int(float(item.get("order", 0)))
        start = float(item.get("source_start_seconds", 0.0))
        end = float(item.get("source_end_seconds", 0.0))
        return f"{order:03d}_{safe_name}_{start:.3f}_{end:.3f}"

    def _existing_choices(self) -> dict[str, dict[str, str]]:
        source = None
        if self.selection_json.exists():
            source = self.selection_json
        elif self.autosave_json.exists():
            source = self.autosave_json

        if not source:
            return {}

        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            selections = payload.get("selections", payload if isinstance(payload, list) else [])
            choices: dict[str, dict[str, str]] = {}

            for row in selections:
                if not isinstance(row, dict):
                    continue
                rid = str(row.get("review_id", ""))
                if not rid:
                    continue
                choices[rid] = {
                    "status": str(row.get("status", "unset")),
                    "note": str(row.get("note", "")),
                }

            return choices
        except Exception:
            return {}

    def _save_payload(self, payload: dict[str, Any], autosave: bool = False) -> Path:
        rows = payload.get("selections", [])
        if not isinstance(rows, list):
            raise RuntimeError("Payload missing selections list.")

        output = self.autosave_json if autosave else self.selection_json

        full_payload = {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "source_input": str(self.input_json),
            "project": self.project.name,
            "mode": "autosave" if autosave else "manual_save",
            "selections": rows,
        }

        output.write_text(
            json.dumps(full_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Alias for module 015B/manual-export convenience.
        if not autosave:
            latest = Path(self.project.root) / "manual_selection.json"
            latest.write_text(
                json.dumps(full_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return output

    def _make_handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status: int, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                path = parsed.path

                if path == "/":
                    html = outer._build_html()
                    self._send(200, html.encode("utf-8"))
                    return

                if path == "/api/state":
                    payload = {
                        "input_json": str(outer.input_json),
                        "selection_json": str(outer.selection_json),
                        "autosave_json": str(outer.autosave_json),
                        "choices": outer._existing_choices(),
                    }
                    self._send(200, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
                    return

                # Serve thumbnails relative to input folder.
                safe_path = path.lstrip("/")
                file_path = (outer.output_dir / safe_path).resolve()

                try:
                    output_root = outer.output_dir.resolve()
                    if output_root not in file_path.parents and file_path != output_root:
                        self._send(403, b"Forbidden", "text/plain")
                        return

                    if not file_path.exists() or not file_path.is_file():
                        self._send(404, b"Not found", "text/plain")
                        return

                    suffix = file_path.suffix.lower()
                    content_type = "application/octet-stream"
                    if suffix in (".jpg", ".jpeg"):
                        content_type = "image/jpeg"
                    elif suffix == ".png":
                        content_type = "image/png"
                    elif suffix == ".webp":
                        content_type = "image/webp"

                    self._send(200, file_path.read_bytes(), content_type)
                    return
                except Exception as exc:
                    self._send(500, str(exc).encode("utf-8"), "text/plain")

            def do_POST(self) -> None:
                parsed = urlparse(self.path)
                path = parsed.path
                params = parse_qs(parsed.query)

                if path not in ("/api/save", "/api/autosave"):
                    self._send(404, b"Not found", "text/plain")
                    return

                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length)
                    payload = json.loads(raw.decode("utf-8"))

                    autosave = path == "/api/autosave" or params.get("autosave", ["0"])[0] == "1"
                    output = outer._save_payload(payload, autosave=autosave)

                    response = {
                        "ok": True,
                        "autosave": autosave,
                        "path": str(output),
                        "saved_at": datetime.now().isoformat(timespec="seconds"),
                    }
                    self._send(200, json.dumps(response, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
                    return

                except Exception as exc:
                    response = {"ok": False, "error": str(exc)}
                    self._send(500, json.dumps(response, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        return Handler

    def _build_html(self) -> str:
        items = self._load_items()
        items_json = json.dumps(items, ensure_ascii=False)
        input_text = str(self.input_json)
        save_text = str(self.selection_json)

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>STT AI Live Manual Review</title>
<style>
:root {{
  --bg:#0b0b0d; --panel:#15151a; --panel2:#202028; --text:#f5f5f7;
  --muted:#aaaab4; --line:#33333d; --keep:#8ef0b0; --maybe:#ffd166; --reject:#ff7b7b;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family:Arial, Helvetica, sans-serif; }}
header {{
  position:sticky; top:0; z-index:10; padding:16px 18px;
  background:rgba(11,11,13,.94); backdrop-filter:blur(16px); border-bottom:1px solid var(--line);
}}
h1 {{ margin:0 0 8px; font-size:22px; }}
.sub {{ color:var(--muted); font-size:12px; line-height:1.4; word-break:break-all; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:13px; align-items:center; }}
button, select {{
  border:1px solid var(--line); background:var(--panel2); color:var(--text);
  border-radius:10px; padding:9px 11px; cursor:pointer; font-weight:700;
}}
button:hover {{ filter:brightness(1.15); }}
.save {{ background:#163323; border-color:#2e8b57; color:var(--keep); }}
.export {{ background:#1d2a3d; border-color:#31517a; }}
.danger {{ background:#3a1f24; border-color:#7a313a; }}
.counter {{
  padding:8px 11px; border:1px solid var(--line); background:var(--panel); border-radius:999px; font-size:13px;
}}
#saveStatus {{ color:var(--keep); font-weight:800; }}
main {{ padding:20px; display:grid; grid-template-columns:repeat(auto-fill,minmax(350px,1fr)); gap:18px; }}
.card {{
  background:var(--panel); border:1px solid var(--line); border-radius:18px; overflow:hidden;
  box-shadow:0 14px 34px rgba(0,0,0,.25);
}}
.card.keep {{ border-color:rgba(142,240,176,.75); }}
.card.maybe {{ border-color:rgba(255,209,102,.75); }}
.card.reject {{ opacity:.56; border-color:rgba(255,123,123,.6); }}
.thumb {{ width:100%; aspect-ratio:16/9; object-fit:cover; display:block; background:#050506; }}
.body {{ padding:14px; }}
.title {{ font-size:15px; line-height:1.35; font-weight:800; margin-bottom:8px; word-break:break-word; }}
.meta {{ color:var(--muted); font-size:12px; line-height:1.5; }}
.scores {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:12px; }}
.score {{
  background:var(--panel2); border:1px solid var(--line); border-radius:12px;
  padding:8px; font-size:11px; color:var(--muted);
}}
.score strong {{ display:block; font-size:18px; color:var(--text); margin-top:2px; }}
.actions {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:12px; }}
.btn-keep.active, .btn-keep:hover {{ background:rgba(142,240,176,.18); border-color:var(--keep); color:var(--keep); }}
.btn-maybe.active, .btn-maybe:hover {{ background:rgba(255,209,102,.18); border-color:var(--maybe); color:var(--maybe); }}
.btn-reject.active, .btn-reject:hover {{ background:rgba(255,123,123,.18); border-color:var(--reject); color:var(--reject); }}
textarea {{
  width:100%; min-height:56px; margin-top:10px; resize:vertical;
  border-radius:12px; border:1px solid var(--line); background:#0f0f13;
  color:var(--text); padding:10px; font-family:inherit;
}}
.status {{
  display:inline-block; margin-top:10px; padding:6px 9px; border-radius:999px;
  font-size:12px; font-weight:800; border:1px solid var(--line); color:var(--muted);
}}
.status.keep {{ color:var(--keep); border-color:var(--keep); }}
.status.maybe {{ color:var(--maybe); border-color:var(--maybe); }}
.status.reject {{ color:var(--reject); border-color:var(--reject); }}
.path {{ margin-top:10px; font-size:11px; color:#777783; word-break:break-all; }}
footer {{ padding:18px 22px 35px; color:var(--muted); border-top:1px solid var(--line); font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>STT AI Live Manual Review</h1>
  <div class="sub">
    Input: {escape(input_text)}<br>
    Save trực tiếp: {escape(save_text)}<br>
    Shots: {len(items)}
  </div>
  <div class="toolbar">
    <button class="save" onclick="saveNow()">Save to Project Folder</button>
    <button class="export" onclick="exportJSON()">Export JSON backup</button>
    <button onclick="markAllMaybe()">All MAYBE</button>
    <button class="danger" onclick="clearChoices()">Clear</button>
    <select id="filter" onchange="render()">
      <option value="all">Show all</option>
      <option value="keep">KEEP only</option>
      <option value="maybe">MAYBE only</option>
      <option value="reject">REJECT only</option>
      <option value="unset">Unset only</option>
    </select>
    <span class="counter" id="countAll">All: 0</span>
    <span class="counter" id="countKeep">KEEP: 0</span>
    <span class="counter" id="countMaybe">MAYBE: 0</span>
    <span class="counter" id="countReject">REJECT: 0</span>
    <span class="counter" id="countUnset">Unset: 0</span>
    <span id="saveStatus">Ready</span>
  </div>
</header>
<main id="grid"></main>
<footer>
  Bấm KEEP / REJECT xong nhấn <b>Save to Project Folder</b>. File sẽ được lưu trực tiếp vào project, không cần tải JSON từ browser nữa.
</footer>

<script>
const ITEMS = {items_json};
const STORAGE_KEY = "stt_live_manual_review_" + btoa(unescape(encodeURIComponent({json.dumps(input_text)}))).slice(0, 60);
let choices = {{}};
let saveTimer = null;

function loadLocal() {{
  try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}"); }}
  catch(e) {{ return {{}}; }}
}}

async function loadServerState() {{
  choices = loadLocal();
  try {{
    const res = await fetch("/api/state");
    const data = await res.json();
    if (data.choices) {{
      choices = Object.assign({{}}, choices, data.choices);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(choices));
    }}
  }} catch(e) {{}}
}}

function saveLocal() {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(choices));
  updateCounters();
  scheduleAutosave();
}}

function statusOf(item) {{
  return (choices[item.review_id] && choices[item.review_id].status) || "unset";
}}

function noteOf(item) {{
  return (choices[item.review_id] && choices[item.review_id].note) || "";
}}

function setStatus(id, status) {{
  if (!choices[id]) choices[id] = {{}};
  choices[id].status = status;
  saveLocal();
  render();
}}

function setNote(id, note) {{
  if (!choices[id]) choices[id] = {{}};
  choices[id].note = note;
  saveLocal();
}}

function formatNum(v) {{
  const n = Number(v);
  if (!Number.isFinite(n)) return "";
  return n.toFixed(1);
}}

function cardHTML(item) {{
  const st = statusOf(item);
  const note = noteOf(item);
  const thumb = item.thumbnail || ("preview_thumbnails/thumb_" + String(item.order).padStart(3, "0") + ".jpg");
  const finalScore = item.final_wedding_score ?? item.expansion_score ?? "";
  const storyScore = item.story_score ?? "";
  const momentScore = item.best_moment_score ?? "";
  const keepScore = item.ai_keep_score ?? "";
  const role = item.story_role || "";
  const section = item.story_section || "";
  const label = item.content_label || "";

  return `
  <article class="card ${{st}}" data-id="${{item.review_id}}">
    <img class="thumb" src="${{thumb}}" onerror="this.style.display='none'">
    <div class="body">
      <div class="title">#${{String(item.order).padStart(3,"0")}} · ${{item.video_filename || ""}}</div>
      <div class="meta">
        Source: ${{Number(item.source_start_seconds || 0).toFixed(2)}}s → ${{Number(item.source_end_seconds || 0).toFixed(2)}}s · Duration: ${{Number(item.duration_seconds || 0).toFixed(2)}}s<br>
        Section: ${{section}} · Role: ${{role}} · Label: ${{label}}
      </div>
      <div class="scores">
        <div class="score">Final<strong>${{formatNum(finalScore)}}</strong></div>
        <div class="score">Story<strong>${{formatNum(storyScore)}}</strong></div>
        <div class="score">Moment<strong>${{formatNum(momentScore)}}</strong></div>
        <div class="score">AI Keep<strong>${{formatNum(keepScore)}}</strong></div>
        <div class="score">Motion<strong>${{formatNum(item.motion_score)}}</strong></div>
        <div class="score">Beauty<strong>${{formatNum(item.beauty_score)}}</strong></div>
      </div>
      <div class="actions">
        <button class="btn-keep ${{st === "keep" ? "active" : ""}}" onclick="setStatus('${{item.review_id}}','keep')">KEEP</button>
        <button class="btn-maybe ${{st === "maybe" ? "active" : ""}}" onclick="setStatus('${{item.review_id}}','maybe')">MAYBE</button>
        <button class="btn-reject ${{st === "reject" ? "active" : ""}}" onclick="setStatus('${{item.review_id}}','reject')">REJECT</button>
      </div>
      <textarea placeholder="Ghi chú shot này..." oninput="setNote('${{item.review_id}}', this.value)">${{note}}</textarea>
      <div class="status ${{st}}">${{st.toUpperCase()}}</div>
      <div class="path">${{item.video_path || ""}}</div>
    </div>
  </article>`;
}}

function render() {{
  const filter = document.getElementById("filter").value;
  let shown = ITEMS;
  if (filter !== "all") shown = ITEMS.filter(item => statusOf(item) === filter);
  document.getElementById("grid").innerHTML = shown.map(cardHTML).join("");
  updateCounters();
}}

function updateCounters() {{
  let keep = 0, maybe = 0, reject = 0, unset = 0;
  ITEMS.forEach(item => {{
    const st = statusOf(item);
    if (st === "keep") keep++;
    else if (st === "maybe") maybe++;
    else if (st === "reject") reject++;
    else unset++;
  }});
  document.getElementById("countAll").textContent = "All: " + ITEMS.length;
  document.getElementById("countKeep").textContent = "KEEP: " + keep;
  document.getElementById("countMaybe").textContent = "MAYBE: " + maybe;
  document.getElementById("countReject").textContent = "REJECT: " + reject;
  document.getElementById("countUnset").textContent = "Unset: " + unset;
}}

function selectionRows() {{
  return ITEMS.map(item => {{
    const choice = choices[item.review_id] || {{}};
    return {{
      review_id: item.review_id,
      order: item.order,
      status: choice.status || "unset",
      note: choice.note || "",
      video_filename: item.video_filename || "",
      video_path: item.video_path || "",
      source_start_seconds: item.source_start_seconds || 0,
      source_end_seconds: item.source_end_seconds || 0,
      duration_seconds: item.duration_seconds || 0,
      timeline_start_seconds: item.timeline_start_seconds || 0,
      timeline_end_seconds: item.timeline_end_seconds || 0,
      story_section: item.story_section || "",
      story_role: item.story_role || "",
      story_score: item.story_score || "",
      final_wedding_score: item.final_wedding_score || "",
      best_moment_score: item.best_moment_score || "",
      ai_keep_score: item.ai_keep_score || "",
      content_label: item.content_label || ""
    }};
  }});
}}

function payload() {{
  return {{
    source_input: {json.dumps(input_text)},
    selections: selectionRows()
  }};
}}

async function postSave(url) {{
  const res = await fetch(url, {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify(payload())
  }});
  return await res.json();
}}

function scheduleAutosave() {{
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {{
    try {{
      document.getElementById("saveStatus").textContent = "Autosaving...";
      const data = await postSave("/api/autosave");
      document.getElementById("saveStatus").textContent = data.ok ? "Autosaved" : "Autosave error";
    }} catch(e) {{
      document.getElementById("saveStatus").textContent = "Autosave failed";
    }}
  }}, 800);
}}

async function saveNow() {{
  try {{
    document.getElementById("saveStatus").textContent = "Saving...";
    const data = await postSave("/api/save");
    if (data.ok) {{
      document.getElementById("saveStatus").textContent = "Saved: " + data.path;
      alert("Đã lưu manual_selection.json trực tiếp vào project.\\n\\n" + data.path);
    }} else {{
      document.getElementById("saveStatus").textContent = "Save error";
      alert(data.error || "Save error");
    }}
  }} catch(e) {{
    document.getElementById("saveStatus").textContent = "Save failed";
    alert(String(e));
  }}
}}

function downloadFile(filename, content, mime) {{
  const blob = new Blob([content], {{type: mime}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}}

function exportJSON() {{
  downloadFile("manual_selection.json", JSON.stringify(payload(), null, 2), "application/json;charset=utf-8");
}}

function markAllMaybe() {{
  ITEMS.forEach(item => {{
    if (!choices[item.review_id]) choices[item.review_id] = {{}};
    choices[item.review_id].status = "maybe";
  }});
  saveLocal();
  render();
}}

function clearChoices() {{
  if (!confirm("Xoá toàn bộ lựa chọn?")) return;
  choices = {{}};
  localStorage.removeItem(STORAGE_KEY);
  saveLocal();
  render();
}}

loadServerState().then(render);
</script>
</body>
</html>'''


def run_live_manual_review_existing_project(
    project_root: str | Path,
    input_json: str | Path | None = None,
    port: int = 8787,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    server = LiveManualReviewServer(
        project=project,
        input_json=input_json,
        config=LiveManualReviewConfig(port=port),
    )

    return server.start_blocking()
