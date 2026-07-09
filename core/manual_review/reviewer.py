
from __future__ import annotations

import csv
import html
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project import ProjectManager, STTProject


@dataclass
class ManualReviewConfig:
    output_prefix: str = "manual_review"
    title: str = "STT AI Manual Review"
    default_status: str = "unset"


class ModernManualReviewGenerator:
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
            raise FileNotFoundError(f"Input json not found: {self.input_json}")

        rows = self._load_rows(self.input_json)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.project.paths.exports_dir / f"{self.config.output_prefix}_{stamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        html_path = output_dir / "manual_review.html"
        data_json = output_dir / "manual_review_data.json"
        template_json = output_dir / "manual_selection_template.json"
        template_csv = output_dir / "manual_selection_template.csv"

        items = self._prepare_items(rows, output_dir)
        data_json.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

        selection = {
            "project_root": str(self.project.root),
            "source": str(self.input_json),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "items": [
                {
                    "id": item["id"],
                    "status": self.config.default_status,
                    "liked": False,
                    "note": "",
                    "video_path": item.get("video_path", ""),
                    "video_filename": item.get("video_filename", ""),
                    "source_start_seconds": item.get("source_start_seconds", 0.0),
                    "source_end_seconds": item.get("source_end_seconds", 0.0),
                    "duration_seconds": item.get("duration_seconds", 0.0),
                    "order": item.get("order", 0),
                }
                for item in items
            ],
        }
        template_json.write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_selection_csv(template_csv, selection["items"])
        html_path.write_text(self._render_html(items), encoding="utf-8")

        print("MODERN MANUAL REVIEW CREATED")
        print(f"Input: {self.input_json}")
        print(f"Items: {len(items)}")
        print(f"HTML: {html_path}")

        return {
            "output_dir": str(output_dir),
            "html": str(html_path),
            "data_json": str(data_json),
            "selection_template_json": str(template_json),
            "selection_template_csv": str(template_csv),
            "input_json": str(self.input_json),
        }

    def _find_latest_input_json(self) -> Path:
        patterns = [
            "duplicate_removed_*/roughcut_no_duplicates.json",
            "duplicate_removed_*/roughcut_plan.json",
            "story_timeline_v2_*/roughcut_story_v2.json",
            "story_timeline_v2_*/roughcut_plan.json",
            "manual_final_*/manual_roughcut.json",
            "final_roughcut_*/roughcut_final.json",
            "story_timeline_*/roughcut_story.json",
            "roughcut_*/roughcut_plan.json",
        ]
        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(self.project.paths.exports_dir.glob(pattern))
        candidates = [p for p in candidates if p.exists() and p.is_file()]
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0] if candidates else self.project.paths.exports_dir / "roughcut_plan.json"

    @staticmethod
    def _load_rows(path: Path) -> list[dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(x) for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict) and isinstance(payload.get("segments"), list):
            return [dict(x) for x in payload["segments"] if isinstance(x, dict)]
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            return [dict(x) for x in payload["items"] if isinstance(x, dict)]
        raise RuntimeError(f"Unsupported json format: {path}")

    def _prepare_items(self, rows: list[dict[str, Any]], output_dir: Path) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            item = dict(row)
            item["id"] = str(item.get("id") or f"shot_{idx:04d}")
            item["order"] = int(float(item.get("order", idx) or idx))
            item["video_path"] = str(item.get("video_path", ""))
            item["video_filename"] = str(item.get("video_filename") or Path(item["video_path"]).name or f"shot_{idx:04d}")
            item["source_start_seconds"] = round(self._num(item, "source_start_seconds", 0.0), 3)
            item["source_end_seconds"] = round(self._num(item, "source_end_seconds", item["source_start_seconds"]), 3)
            item["duration_seconds"] = round(self._num(item, "duration_seconds", item["source_end_seconds"] - item["source_start_seconds"]), 3)
            item["timeline_start_seconds"] = round(self._num(item, "timeline_start_seconds", 0.0), 3)
            item["timeline_end_seconds"] = round(self._num(item, "timeline_end_seconds", 0.0), 3)
            item["score"] = round(self._score(item), 2)
            item["scene"] = str(item.get("wedding_scene") or item.get("content_label") or item.get("story_section") or "unknown")
            item["section"] = str(item.get("story_section") or item.get("story_v2_bucket") or "")
            item["thumbnail_url"] = self._thumbnail_url(item, output_dir)
            item["video_url"] = self._file_url(item.get("video_path", ""))
            item["status"] = "unset"
            item["liked"] = False
            item["note"] = ""
            items.append(item)
        items.sort(key=lambda x: int(x.get("order", 0)))
        return items

    def _thumbnail_url(self, item: dict[str, Any], output_dir: Path) -> str:
        thumb = str(item.get("thumbnail", "")).strip()
        candidates: list[Path] = []
        if thumb:
            p = Path(thumb)
            if p.is_absolute():
                candidates.append(p)
            else:
                candidates.append(self.input_json.parent / p)
                candidates.append(output_dir / p)
        order = int(float(item.get("order", 0) or 0))
        if order > 0:
            candidates.append(self.input_json.parent / "preview_thumbnails" / f"thumb_{order:03d}.jpg")
            candidates.append(output_dir / "preview_thumbnails" / f"thumb_{order:03d}.jpg")
        for p in candidates:
            if p.exists():
                return self._file_url(str(p))
        return ""

    @staticmethod
    def _file_url(path_text: str) -> str:
        if not path_text:
            return ""
        try:
            p = Path(path_text)
            if p.exists():
                return p.resolve().as_uri()
        except Exception:
            pass
        return ""

    @staticmethod
    def _score(row: dict[str, Any]) -> float:
        for key in ["story_v2_score", "final_wedding_score", "expansion_score", "ai_keep_score", "score"]:
            value = row.get(key)
            if value is not None:
                try:
                    return float(value)
                except Exception:
                    pass
        return 0.0

    @staticmethod
    def _num(row: dict[str, Any], key: str, default: float = 0.0) -> float:
        try:
            value = row.get(key, default)
            return default if value is None else float(value)
        except Exception:
            return default

    @staticmethod
    def _write_selection_csv(path: Path, items: list[dict[str, Any]]) -> None:
        keys = ["id", "order", "status", "liked", "note", "video_filename", "video_path", "source_start_seconds", "source_end_seconds", "duration_seconds"]
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in items:
                writer.writerow({k: row.get(k, "") for k in keys})

    def _render_html(self, items: list[dict[str, Any]]) -> str:
        items_json = json.dumps(items, ensure_ascii=False)
        title = html.escape(self.config.title)
        project_json = json.dumps(str(self.project.root), ensure_ascii=False)
        source_json = json.dumps(str(self.input_json), ensure_ascii=False)

        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ --bg:#0d0d10; --panel:#17171d; --panel2:#202028; --text:#f4f4f6; --muted:#a5a5ad; --line:#34343e; --keep:#27d17f; --maybe:#ffd166; --reject:#ff5c77; --blue:#8fd3ff; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:linear-gradient(180deg,#08080b,#111117); color:var(--text); font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
header {{ position:sticky; top:0; z-index:10; background:rgba(13,13,16,.94); backdrop-filter:blur(18px); border-bottom:1px solid var(--line); }}
.top {{ padding:14px 18px; display:flex; gap:14px; align-items:center; flex-wrap:wrap; }}
h1 {{ margin:0; font-size:20px; letter-spacing:-.02em; }}
.badge {{ padding:7px 10px; border-radius:999px; background:var(--panel2); border:1px solid var(--line); color:var(--muted); font-size:12px; }}
.summary {{ display:flex; gap:8px; flex-wrap:wrap; margin-left:auto; }}
.sum {{ padding:8px 12px; border-radius:12px; background:var(--panel); border:1px solid var(--line); font-weight:900; }}
.sum.keep {{ color:var(--keep); }} .sum.maybe {{ color:var(--maybe); }} .sum.reject {{ color:var(--reject); }}
.controls {{ padding:0 18px 14px; display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
button, select, input {{ background:var(--panel2); color:var(--text); border:1px solid var(--line); border-radius:12px; padding:10px 12px; font-weight:800; }}
button:hover {{ filter:brightness(1.15); cursor:pointer; }}
button.primary {{ background:#24415a; border-color:#3d6f9a; }}
button.keep {{ background:rgba(39,209,127,.14); border-color:rgba(39,209,127,.55); color:var(--keep); }}
button.maybe {{ background:rgba(255,209,102,.14); border-color:rgba(255,209,102,.55); color:var(--maybe); }}
button.reject {{ background:rgba(255,92,119,.14); border-color:rgba(255,92,119,.55); color:var(--reject); }}
input.search {{ min-width:240px; flex:1; }}
main {{ padding:18px; max-width:1500px; margin:0 auto; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:16px; }}
.card {{ background:linear-gradient(180deg,#191921,#121217); border:1px solid var(--line); border-radius:18px; overflow:hidden; box-shadow:0 12px 36px rgba(0,0,0,.28); }}
.card.active {{ outline:2px solid var(--blue); box-shadow:0 0 0 6px rgba(143,211,255,.12); }}
.thumb {{ position:relative; aspect-ratio:16/9; background:#050507; overflow:hidden; }}
.thumb img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.no-thumb {{ height:100%; display:flex; align-items:center; justify-content:center; color:var(--muted); font-weight:900; }}
.status-ribbon {{ position:absolute; top:10px; left:10px; padding:7px 10px; border-radius:999px; background:rgba(0,0,0,.65); border:1px solid rgba(255,255,255,.18); font-size:12px; font-weight:900; }}
.card[data-status="keep"] .status-ribbon {{ color:var(--keep); }} .card[data-status="maybe"] .status-ribbon {{ color:var(--maybe); }} .card[data-status="reject"] .status-ribbon {{ color:var(--reject); }}
.meta {{ padding:14px; }} .title {{ font-weight:900; font-size:14px; line-height:1.35; margin-bottom:10px; word-break:break-word; }}
.tags {{ display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }}
.tag {{ font-size:11px; color:var(--muted); padding:5px 8px; border-radius:999px; background:#101014; border:1px solid var(--line); }}
.time {{ color:var(--muted); font-size:12px; line-height:1.5; margin-bottom:12px; }}
.actions {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; }}
.actions2 {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px; }}
.note {{ width:100%; margin-top:10px; font-size:12px; }}
.hidden {{ display:none !important; }} .help {{ color:var(--muted); font-size:12px; }}
@media (max-width:760px) {{ .summary {{ margin-left:0; width:100%; }} .grid {{ grid-template-columns:1fr; }} main {{ padding:12px; }} }}
</style>
</head>
<body>
<header>
  <div class="top">
    <h1>{title}</h1>
    <span class="badge" id="totalBadge">0 shots</span>
    <span class="badge">K=Keep · M=Maybe · R=Reject · Space=Next</span>
    <div class="summary">
      <div class="sum keep" id="keepCount">KEEP 0</div>
      <div class="sum maybe" id="maybeCount">MAYBE 0</div>
      <div class="sum reject" id="rejectCount">REJECT 0</div>
      <div class="sum" id="unsetCount">UNSET 0</div>
    </div>
  </div>
  <div class="controls">
    <input class="search" id="searchBox" placeholder="Search filename / scene / section">
    <select id="filterStatus"><option value="all">All status</option><option value="unset">Unset</option><option value="keep">Keep</option><option value="maybe">Maybe</option><option value="reject">Reject</option><option value="liked">Liked</option></select>
    <select id="filterScene"><option value="all">All scenes</option></select>
    <button class="keep" onclick="bulkSetVisible('keep')">Keep visible</button>
    <button class="reject" onclick="bulkSetVisible('reject')">Reject visible</button>
    <button onclick="resetAll()">Reset</button>
    <button class="primary" onclick="downloadSelection()">Export JSON</button>
  </div>
</header>
<main>
  <div class="help">Tip: bấm card rồi dùng K/M/R. Export JSON sẽ tải manual_selection.json về Downloads nếu dùng manual review cũ.</div>
  <br><div class="grid" id="grid"></div>
</main>
<script>
const ITEMS = {items_json};
const PROJECT_ROOT = {project_json};
const SOURCE_JSON = {source_json};
let activeIndex = 0;
const state = {{}};
for (const item of ITEMS) state[item.id] = {{status:item.status||'unset', liked:!!item.liked, note:item.note||''}};

function esc(s) {{ return String(s ?? '').replace(/[&<>"']/g, m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m])); }}
function fmtTime(s) {{ s=Number(s||0); const m=Math.floor(s/60); const sec=(s%60).toFixed(1).padStart(4,'0'); return `${{m}}:${{sec}}`; }}
function render() {{ totalBadge.textContent=ITEMS.length+' shots'; buildSceneFilter(); grid.innerHTML=ITEMS.map((item,i)=>cardHtml(item,i)).join(''); updateAllCards(); applyFilters(); }}
function cardHtml(item,i) {{
 const thumb=item.thumbnail_url?`<img src="${{esc(item.thumbnail_url)}}" loading="lazy">`:`<div class="no-thumb">NO THUMBNAIL</div>`;
 return `<article class="card" data-id="${{esc(item.id)}}" data-index="${{i}}" data-status="unset" data-scene="${{esc(item.scene)}}" onclick="setActive(${{i}})">
 <div class="thumb">${{thumb}}<div class="status-ribbon" id="ribbon_${{esc(item.id)}}">UNSET</div></div>
 <div class="meta"><div class="title">#${{item.order}} · ${{esc(item.video_filename)}}</div>
 <div class="tags"><span class="tag">${{esc(item.scene)}}</span><span class="tag">${{esc(item.section||'no-section')}}</span><span class="tag">score ${{Number(item.score||0).toFixed(1)}}</span><span class="tag">${{Number(item.duration_seconds||0).toFixed(1)}}s</span></div>
 <div class="time">Source: ${{fmtTime(item.source_start_seconds)}} → ${{fmtTime(item.source_end_seconds)}}<br>Timeline: ${{fmtTime(item.timeline_start_seconds)}} → ${{fmtTime(item.timeline_end_seconds)}}</div>
 <div class="actions"><button class="keep" onclick="event.stopPropagation(); setStatus('${{esc(item.id)}}','keep')">KEEP</button><button class="maybe" onclick="event.stopPropagation(); setStatus('${{esc(item.id)}}','maybe')">MAYBE</button><button class="reject" onclick="event.stopPropagation(); setStatus('${{esc(item.id)}}','reject')">REJECT</button></div>
 <div class="actions2"><button onclick="event.stopPropagation(); toggleLike('${{esc(item.id)}}')" id="like_${{esc(item.id)}}">☆ Like</button><button onclick="event.stopPropagation(); openVideo('${{esc(item.id)}}')">Open Source</button></div>
 <input class="note" id="note_${{esc(item.id)}}" placeholder="Note..." oninput="setNote('${{esc(item.id)}}', this.value)" onclick="event.stopPropagation()"></div></article>`;
}}
function buildSceneFilter() {{ const sel=filterScene; const current=sel.value||'all'; const scenes=[...new Set(ITEMS.map(x=>x.scene||'unknown'))].sort(); sel.innerHTML='<option value="all">All scenes</option>'+scenes.map(s=>`<option value="${{esc(s)}}">${{esc(s)}}</option>`).join(''); sel.value=scenes.includes(current)?current:'all'; }}
function setActive(i) {{ activeIndex=Math.max(0,Math.min(ITEMS.length-1,i)); document.querySelectorAll('.card').forEach(c=>c.classList.remove('active')); const el=document.querySelector(`.card[data-index="${{activeIndex}}"]`); if(el){{el.classList.add('active'); el.scrollIntoView({{block:'nearest',behavior:'smooth'}});}} }}
function setStatus(id,status) {{ state[id].status=status; updateCard(id); updateCounts(); }}
function toggleLike(id) {{ state[id].liked=!state[id].liked; updateCard(id); updateCounts(); }}
function setNote(id,note) {{ state[id].note=note; }}
function updateCard(id) {{ const card=document.querySelector(`.card[data-id="${{CSS.escape(id)}}"]`); if(!card)return; const st=state[id].status; card.dataset.status=st; const r=document.getElementById('ribbon_'+id); if(r)r.textContent=st.toUpperCase(); const l=document.getElementById('like_'+id); if(l)l.textContent=state[id].liked?'★ Liked':'☆ Like'; const n=document.getElementById('note_'+id); if(n&&n.value!==state[id].note)n.value=state[id].note||''; }}
function updateAllCards() {{ for(const item of ITEMS)updateCard(item.id); updateCounts(); setActive(activeIndex); }}
function updateCounts() {{ const c={{keep:0,maybe:0,reject:0,unset:0,liked:0}}; for(const id in state){{c[state[id].status||'unset']++; if(state[id].liked)c.liked++;}} keepCount.textContent='KEEP '+c.keep; maybeCount.textContent='MAYBE '+c.maybe; rejectCount.textContent='REJECT '+c.reject; unsetCount.textContent='UNSET '+c.unset+' · LIKE '+c.liked; }}
function applyFilters() {{ const q=searchBox.value.toLowerCase().trim(), st=filterStatus.value, scene=filterScene.value; for(const item of ITEMS){{ const card=document.querySelector(`.card[data-id="${{CSS.escape(item.id)}}"]`); if(!card)continue; const text=`${{item.video_filename}} ${{item.scene}} ${{item.section}}`.toLowerCase(); let show=true; if(q&&!text.includes(q))show=false; if(st!=='all')show=show&&(st==='liked'?state[item.id].liked:state[item.id].status===st); if(scene!=='all')show=show&&item.scene===scene; card.classList.toggle('hidden',!show); }} }}
function visibleItems() {{ return ITEMS.filter(item=>{{const c=document.querySelector(`.card[data-id="${{CSS.escape(item.id)}}"]`); return c&&!c.classList.contains('hidden');}}); }}
function bulkSetVisible(status) {{ for(const item of visibleItems())state[item.id].status=status; updateAllCards(); applyFilters(); }}
function resetAll() {{ if(!confirm('Reset all status?'))return; for(const id in state){{state[id].status='unset';state[id].liked=false;state[id].note='';}} updateAllCards(); }}
function openVideo(id) {{ const item=ITEMS.find(x=>x.id===id); if(item&&item.video_url)window.open(item.video_url,'_blank'); else alert('No source video URL found.'); }}
function payload() {{ return {{project_root:PROJECT_ROOT, source:SOURCE_JSON, created_at:new Date().toISOString(), items:ITEMS.map(item=>({{id:item.id,order:item.order,status:state[item.id].status||'unset',liked:!!state[item.id].liked,note:state[item.id].note||'',video_path:item.video_path||'',video_filename:item.video_filename||'',source_start_seconds:item.source_start_seconds||0,source_end_seconds:item.source_end_seconds||0,duration_seconds:item.duration_seconds||0,wedding_scene:item.scene||'',story_section:item.section||''}}))}}; }}
function downloadSelection() {{ const blob=new Blob([JSON.stringify(payload(),null,2)],{{type:'application/json'}}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='manual_selection.json'; a.click(); URL.revokeObjectURL(a.href); }}
searchBox.addEventListener('input',applyFilters); filterStatus.addEventListener('change',applyFilters); filterScene.addEventListener('change',applyFilters);
document.addEventListener('keydown',e=>{{ if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName))return; const item=ITEMS[activeIndex]; if(!item)return; if(e.key.toLowerCase()==='k')setStatus(item.id,'keep'); if(e.key.toLowerCase()==='m')setStatus(item.id,'maybe'); if(e.key.toLowerCase()==='r')setStatus(item.id,'reject'); if(e.key===' '){{e.preventDefault();setActive(activeIndex+1);}} if(e.key==='ArrowRight')setActive(activeIndex+1); if(e.key==='ArrowLeft')setActive(activeIndex-1); }});
render();
</script>
</body></html>"""


def generate_manual_review_existing_project(project_root: str | Path, input_json: str | Path | None = None) -> dict[str, str]:
    project = ProjectManager().open_project(project_root)
    return ModernManualReviewGenerator(project=project, input_json=input_json).generate()
