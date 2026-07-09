from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from core.project import ProjectManager, STTProject


@dataclass
class ManualReviewConfig:
    title: str = "STT AI Manual Review"
    output_name: str = "manual_review.html"


class ManualReviewGenerator:
    # Build 014.
    # Creates an interactive HTML review page:
    # KEEP / MAYBE / REJECT + notes + export manual_selection.json/csv.

    def __init__(
        self,
        project: STTProject,
        input_json: str | Path | None = None,
        config: ManualReviewConfig | None = None,
    ) -> None:
        self.project = project
        self.input_json = Path(input_json) if input_json else self._find_latest_input_json()
        self.config = config or ManualReviewConfig()

    def generate(self) -> dict[str, str]:
        if not self.input_json.exists():
            raise FileNotFoundError(f"Manual review input json not found: {self.input_json}")

        items = json.loads(self.input_json.read_text(encoding="utf-8"))
        output_dir = self.input_json.parent

        html_path = output_dir / self.config.output_name
        template_json = output_dir / "manual_selection_template.json"
        template_csv = output_dir / "manual_selection_template.csv"
        instruction_txt = output_dir / "manual_review_instruction.txt"

        prepared = self._prepare_items(items)
        template_rows = self._selection_rows(prepared, default_status="maybe")

        template_json.write_text(
            json.dumps(template_rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._write_csv(template_csv, template_rows)

        html_path.write_text(self._build_html(prepared), encoding="utf-8")

        instruction_txt.write_text(
            "\n".join([
                "STT AI Manual Review",
                "=" * 40,
                "",
                "Open manual_review.html in Chrome/Edge.",
                "Click KEEP / MAYBE / REJECT on each shot.",
                "Choices are saved in browser localStorage.",
                "Click Export JSON or Export CSV when done.",
                "",
                "Browser cannot silently save back into this folder for security reasons.",
                "The exported file will usually go to Downloads.",
                "",
                f"Input: {self.input_json}",
                f"HTML: {html_path}",
            ]),
            encoding="utf-8",
        )

        print("STT AI Manual Review Generator")
        print(f"Project: {self.project.name}")
        print(f"Input: {self.input_json}")
        print(f"Shots: {len(prepared)}")
        print("-" * 60)
        print("MANUAL REVIEW COMPLETE")
        print(f"HTML: {html_path}")
        print(f"Template JSON: {template_json}")
        print(f"Template CSV: {template_csv}")
        print("-" * 60)

        return {
            "html": str(html_path),
            "template_json": str(template_json),
            "template_csv": str(template_csv),
            "instruction": str(instruction_txt),
            "input_json": str(self.input_json),
            "output_dir": str(output_dir),
        }

    def _find_latest_input_json(self) -> Path:
        patterns = [
            "story_timeline_*/roughcut_story.json",
            "story_timeline_*/roughcut_plan.json",
            "final_roughcut_*/roughcut_final.json",
            "expanded_candidates_*/roughcut_plan_people_composition.json",
            "roughcut_*/roughcut_plan_people_composition.json",
        ]

        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))

        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan.json"

        return candidates[0]

    @staticmethod
    def _prepare_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []

        for index, item in enumerate(items, start=1):
            row = dict(item)

            order = int(row.get("order", index))
            video_path = str(row.get("video_path", ""))
            filename = str(row.get("video_filename", Path(video_path).name))

            start = float(row.get("source_start_seconds", 0.0))
            end = float(row.get("source_end_seconds", start))
            duration = max(0.0, float(row.get("duration_seconds", end - start)))

            row["order"] = order
            row["video_filename"] = filename
            row["review_id"] = ManualReviewGenerator._review_id(row)
            row["thumbnail"] = str(row.get("thumbnail", f"preview_thumbnails/thumb_{order:03d}.jpg"))
            row["source_start_seconds"] = round(start, 3)
            row["source_end_seconds"] = round(end, 3)
            row["duration_seconds"] = round(duration, 3)

            prepared.append(row)

        return prepared

    @staticmethod
    def _review_id(item: dict[str, Any]) -> str:
        safe_name = str(item.get("video_filename", "clip")).replace(" ", "_")
        order = int(item.get("order", 0))
        start = float(item.get("source_start_seconds", 0.0))
        end = float(item.get("source_end_seconds", 0.0))
        return f"{order:03d}_{safe_name}_{start:.3f}_{end:.3f}"

    @staticmethod
    def _selection_rows(items: list[dict[str, Any]], default_status: str = "maybe") -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for item in items:
            rows.append({
                "review_id": item.get("review_id", ""),
                "order": item.get("order", 0),
                "status": default_status,
                "note": "",
                "video_filename": item.get("video_filename", ""),
                "video_path": item.get("video_path", ""),
                "source_start_seconds": item.get("source_start_seconds", 0.0),
                "source_end_seconds": item.get("source_end_seconds", 0.0),
                "duration_seconds": item.get("duration_seconds", 0.0),
                "timeline_start_seconds": item.get("timeline_start_seconds", 0.0),
                "timeline_end_seconds": item.get("timeline_end_seconds", 0.0),
                "story_section": item.get("story_section", ""),
                "story_role": item.get("story_role", ""),
                "story_score": item.get("story_score", ""),
                "final_wedding_score": item.get("final_wedding_score", ""),
                "best_moment_score": item.get("best_moment_score", ""),
                "ai_keep_score": item.get("ai_keep_score", ""),
                "content_label": item.get("content_label", ""),
            })

        return rows

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            return

        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)

    def _build_html(self, items: list[dict[str, Any]]) -> str:
        data_json = json.dumps(items, ensure_ascii=False)
        storage_key = "stt_manual_review_" + str(abs(hash(str(self.input_json))))

        return f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{escape(self.config.title)}</title>
  <style>
    :root {{
      --bg:#0b0b0d;
      --panel:#15151a;
      --panel2:#202028;
      --text:#f5f5f7;
      --muted:#aaaab4;
      --line:#33333d;
      --keep:#8ef0b0;
      --maybe:#ffd166;
      --reject:#ff7b7b;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      background:var(--bg);
      color:var(--text);
      font-family:Arial, Helvetica, sans-serif;
    }}
    header {{
      position:sticky;
      top:0;
      z-index:10;
      padding:16px 18px;
      background:rgba(11,11,13,.94);
      backdrop-filter:blur(16px);
      border-bottom:1px solid var(--line);
    }}
    h1 {{ margin:0 0 8px; font-size:22px; }}
    .sub {{ color:var(--muted); font-size:12px; line-height:1.4; word-break:break-all; }}
    .toolbar {{
      display:flex;
      flex-wrap:wrap;
      gap:8px;
      margin-top:13px;
      align-items:center;
    }}
    button, select {{
      border:1px solid var(--line);
      background:var(--panel2);
      color:var(--text);
      border-radius:10px;
      padding:9px 11px;
      cursor:pointer;
      font-weight:700;
    }}
    button:hover {{ filter:brightness(1.15); }}
    .export {{ background:#1d2a3d; border-color:#31517a; }}
    .danger {{ background:#3a1f24; border-color:#7a313a; }}
    .counter {{
      padding:8px 11px;
      border:1px solid var(--line);
      background:var(--panel);
      border-radius:999px;
      font-size:13px;
    }}
    main {{
      padding:20px;
      display:grid;
      grid-template-columns:repeat(auto-fill,minmax(350px,1fr));
      gap:18px;
    }}
    .card {{
      background:var(--panel);
      border:1px solid var(--line);
      border-radius:18px;
      overflow:hidden;
      box-shadow:0 14px 34px rgba(0,0,0,.25);
    }}
    .card.keep {{ border-color:rgba(142,240,176,.75); }}
    .card.maybe {{ border-color:rgba(255,209,102,.75); }}
    .card.reject {{ opacity:.56; border-color:rgba(255,123,123,.6); }}
    .thumb {{
      width:100%;
      aspect-ratio:16/9;
      object-fit:cover;
      display:block;
      background:#050506;
    }}
    .body {{ padding:14px; }}
    .title {{
      font-size:15px;
      line-height:1.35;
      font-weight:800;
      margin-bottom:8px;
      word-break:break-word;
    }}
    .meta {{
      color:var(--muted);
      font-size:12px;
      line-height:1.5;
    }}
    .scores {{
      display:grid;
      grid-template-columns:repeat(3,1fr);
      gap:8px;
      margin-top:12px;
    }}
    .score {{
      background:var(--panel2);
      border:1px solid var(--line);
      border-radius:12px;
      padding:8px;
      font-size:11px;
      color:var(--muted);
    }}
    .score strong {{
      display:block;
      font-size:18px;
      color:var(--text);
      margin-top:2px;
    }}
    .actions {{
      display:grid;
      grid-template-columns:repeat(3,1fr);
      gap:8px;
      margin-top:12px;
    }}
    .btn-keep.active, .btn-keep:hover {{ background:rgba(142,240,176,.18); border-color:var(--keep); color:var(--keep); }}
    .btn-maybe.active, .btn-maybe:hover {{ background:rgba(255,209,102,.18); border-color:var(--maybe); color:var(--maybe); }}
    .btn-reject.active, .btn-reject:hover {{ background:rgba(255,123,123,.18); border-color:var(--reject); color:var(--reject); }}
    textarea {{
      width:100%;
      min-height:56px;
      margin-top:10px;
      resize:vertical;
      border-radius:12px;
      border:1px solid var(--line);
      background:#0f0f13;
      color:var(--text);
      padding:10px;
      font-family:inherit;
    }}
    .status {{
      display:inline-block;
      margin-top:10px;
      padding:6px 9px;
      border-radius:999px;
      font-size:12px;
      font-weight:800;
      border:1px solid var(--line);
      color:var(--muted);
    }}
    .status.keep {{ color:var(--keep); border-color:var(--keep); }}
    .status.maybe {{ color:var(--maybe); border-color:var(--maybe); }}
    .status.reject {{ color:var(--reject); border-color:var(--reject); }}
    .path {{
      margin-top:10px;
      font-size:11px;
      color:#777783;
      word-break:break-all;
    }}
    footer {{
      padding:18px 22px 35px;
      color:var(--muted);
      border-top:1px solid var(--line);
      font-size:12px;
    }}
  </style>
</head>
<body>
<header>
  <h1>{escape(self.config.title)}</h1>
  <div class="sub">
    Project: {escape(self.project.name)}<br>
    Input: {escape(str(self.input_json))}<br>
    Shots: {len(items)}
  </div>
  <div class="toolbar">
    <button class="export" onclick="exportJSON()">Export JSON</button>
    <button class="export" onclick="exportCSV()">Export CSV</button>
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
  </div>
</header>
<main id="grid"></main>
<footer>
  Bấm KEEP / MAYBE / REJECT. Lựa chọn được lưu trong trình duyệt. Khi xong bấm Export JSON hoặc Export CSV.
</footer>

<script>
const ITEMS = {data_json};
const STORAGE_KEY = {json.dumps(storage_key)};
let choices = loadChoices();

function loadChoices() {{
  try {{
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}");
  }} catch(e) {{
    return {{}};
  }}
}}

function saveChoices() {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(choices));
  updateCounters();
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
  saveChoices();
  render();
}}

function setNote(id, note) {{
  if (!choices[id]) choices[id] = {{}};
  choices[id].note = note;
  saveChoices();
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

  if (filter !== "all") {{
    shown = ITEMS.filter(item => statusOf(item) === filter);
  }}

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
  const payload = {{
    exported_at: new Date().toISOString(),
    source_input: {json.dumps(str(self.input_json))},
    project: {json.dumps(self.project.name)},
    selections: selectionRows()
  }};
  downloadFile("manual_selection.json", JSON.stringify(payload, null, 2), "application/json;charset=utf-8");
}}

function csvEscape(v) {{
  const s = String(v ?? "");
  if (s.includes(",") || s.includes('"') || s.includes("\\n")) {{
    return '"' + s.replaceAll('"', '""') + '"';
  }}
  return s;
}}

function exportCSV() {{
  const rows = selectionRows();
  if (!rows.length) return;
  const keys = Object.keys(rows[0]);
  const csv = [
    keys.join(","),
    ...rows.map(row => keys.map(k => csvEscape(row[k])).join(","))
  ].join("\\n");
  downloadFile("manual_selection.csv", csv, "text/csv;charset=utf-8");
}}

function markAllMaybe() {{
  ITEMS.forEach(item => {{
    if (!choices[item.review_id]) choices[item.review_id] = {{}};
    choices[item.review_id].status = "maybe";
  }});
  saveChoices();
  render();
}}

function clearChoices() {{
  if (!confirm("Xoá toàn bộ lựa chọn trong trình duyệt?")) return;
  choices = {{}};
  localStorage.removeItem(STORAGE_KEY);
  render();
}}

render();
</script>
</body>
</html>'''


def generate_manual_review_existing_project(
    project_root: str | Path,
    input_json: str | Path | None = None,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    generator = ManualReviewGenerator(
        project=project,
        input_json=input_json,
    )

    return generator.generate()
