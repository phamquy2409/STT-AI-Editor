
from __future__ import annotations

import csv
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


MUSIC_MOODS = {
    "prewedding_reel_60s": {
        "mood": "modern romantic, energetic, fashion, emotional hook",
        "bpm_min": 88,
        "bpm_max": 128,
        "duration": 60,
        "keywords": ["romantic", "fashion", "cinematic pop", "indie pop", "emotional", "uplifting"],
        "sources": ["Artlist", "Musicbed", "YouTube Audio Library"],
    },
    "prewedding_reel_30s": {
        "mood": "fast hook, trendy, fashion, beat cut",
        "bpm_min": 100,
        "bpm_max": 140,
        "duration": 30,
        "keywords": ["fashion", "trendy", "beat", "pop", "electronic", "hook"],
        "sources": ["Artlist", "Musicbed", "YouTube Audio Library"],
    },
    "prewedding_cinematic": {
        "mood": "cinematic romantic, soft emotional, piano strings ambient",
        "bpm_min": 60,
        "bpm_max": 95,
        "duration": 120,
        "keywords": ["cinematic", "romantic", "piano", "strings", "ambient", "emotional"],
        "sources": ["Artlist", "Musicbed", "YouTube Audio Library"],
    },
    "wedding_highlight_3min": {
        "mood": "cinematic emotional wedding, piano strings, warm build, dance ending",
        "bpm_min": 65,
        "bpm_max": 120,
        "duration": 180,
        "keywords": ["wedding", "cinematic", "piano", "strings", "emotional", "uplifting", "dance"],
        "sources": ["Artlist", "Musicbed", "YouTube Audio Library"],
    },
}


@dataclass
class MusicTrack:
    source: str = ""
    title: str = ""
    artist: str = ""
    url: str = ""
    track_id: str = ""
    duration: str = ""
    bpm: str = ""
    mood: str = ""
    preview_file: str = ""
    final_replace_filename: str = ""
    license_status: str = "placeholder_preview"
    notes: str = ""


def create_music_placeholder_manager(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    intent: str = "prewedding_reel_60s",
    candidates_csv: str | Path | None = None,
    preview_file: str | Path | None = None,
    open_folder: bool = True,
) -> dict[str, Any]:
    project_root = Path(project_root)
    exports = project_root / "exports"
    music_root = project_root / "music"
    preview_dir = music_root / "music_previews"
    final_dir = music_root / "music_final"
    cue_dir = music_root / "cue_sheets"

    for folder in [exports, preview_dir, final_dir, cue_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = exports / f"music_placeholder_manager_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    mood = MUSIC_MOODS.get(intent, MUSIC_MOODS["prewedding_reel_60s"])
    candidates = load_candidates(candidates_csv) if candidates_csv else []

    copied_preview = None
    if preview_file:
        src = Path(preview_file)
        if src.exists():
            dst = preview_dir / src.name
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            copied_preview = str(dst)

    if not candidates:
        candidates = create_empty_candidates(intent, mood, copied_preview)

    cue_sheet = build_cue_sheet(
        project_root=project_root,
        intent=intent,
        mood=mood,
        candidates=candidates,
        copied_preview=copied_preview,
    )

    cue_csv = output_dir / "MUSIC_CUE_SHEET.csv"
    cue_json = output_dir / "music_cue_sheet.json"
    links_html = output_dir / "MUSIC_LICENSE_LINKS.html"
    guide_txt = output_dir / "MUSIC_REPLACE_GUIDE.txt"
    search_prompt = output_dir / "MUSIC_SEARCH_PROMPT.txt"
    candidate_template = output_dir / "music_candidates_template.csv"

    write_cue_csv(cue_csv, cue_sheet["tracks"])
    cue_json.write_text(json.dumps(cue_sheet, ensure_ascii=False, indent=2), encoding="utf-8")
    links_html.write_text(render_links_html(cue_sheet), encoding="utf-8")
    guide_txt.write_text(render_replace_guide(cue_sheet), encoding="utf-8")
    search_prompt.write_text(render_search_prompt(cue_sheet), encoding="utf-8")
    write_candidate_template(candidate_template)

    # Also copy current cue sheet to stable project paths.
    stable_csv = cue_dir / "MUSIC_CUE_SHEET.csv"
    stable_json = cue_dir / "music_cue_sheet.json"
    write_cue_csv(stable_csv, cue_sheet["tracks"])
    stable_json.write_text(json.dumps(cue_sheet, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "ok": True,
        "module": "062_music_placeholder_manager",
        "intent": intent,
        "output_dir": str(output_dir),
        "report_dir": str(output_dir),
        "music_root": str(music_root),
        "preview_dir": str(preview_dir),
        "final_dir": str(final_dir),
        "cue_csv": str(cue_csv),
        "cue_json": str(cue_json),
        "stable_cue_csv": str(stable_csv),
        "links_html": str(links_html),
        "guide_txt": str(guide_txt),
        "search_prompt": str(search_prompt),
        "candidate_template": str(candidate_template),
        "track_count": len(cue_sheet["tracks"]),
        "copied_preview": copied_preview,
    }

    (output_dir / "music_placeholder_manager_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if open_folder:
        try:
            os.startfile(output_dir)
        except Exception:
            pass

    return result


def load_candidates(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.exists():
        return []

    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({str(k): str(v or "") for k, v in row.items()})

    return rows


def create_empty_candidates(intent: str, mood: dict[str, Any], copied_preview: str | None = None) -> list[dict[str, str]]:
    keywords = ", ".join(mood.get("keywords", []))
    source = "Artlist / Musicbed / YouTube Audio Library"
    return [
        {
            "source": source,
            "title": "CHUA_CHON_BAI",
            "artist": "",
            "url": "",
            "track_id": "",
            "duration": str(mood.get("duration", "")),
            "bpm": f"{mood.get('bpm_min')}-{mood.get('bpm_max')}",
            "mood": str(mood.get("mood", "")),
            "preview_file": copied_preview or "",
            "final_replace_filename": "",
            "license_status": "need_search",
            "notes": f"Tìm bài theo keyword: {keywords}",
        }
    ]


def build_cue_sheet(
    project_root: Path,
    intent: str,
    mood: dict[str, Any],
    candidates: list[dict[str, str]],
    copied_preview: str | None = None,
) -> dict[str, Any]:
    timeline_info = load_timeline_info(project_root)

    tracks = []
    for i, item in enumerate(candidates, start=1):
        track = normalize_track(item)
        if copied_preview and not track["preview_file"] and i == 1:
            track["preview_file"] = copied_preview

        if not track["final_replace_filename"]:
            track["final_replace_filename"] = suggest_final_filename(track)

        track["cue_index"] = i
        track["used_in_timeline_start"] = "00:00"
        track["used_in_timeline_end"] = seconds_to_timecode(timeline_info["duration_seconds"])
        track["timeline_duration_seconds"] = timeline_info["duration_seconds"]
        track["replace_method"] = "Premiere > Project panel > right click preview music > Replace Footage > choose final licensed file"
        tracks.append(track)

    return {
        "ok": True,
        "module": "062_music_placeholder_manager",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "intent": intent,
        "music_mood": mood,
        "timeline_info": timeline_info,
        "tracks": tracks,
        "workflow": [
            "Tìm bài trên Artlist/Musicbed/YouTube Audio Library theo MUSIC_SEARCH_PROMPT.txt.",
            "Tải preview/watermark hợp lệ nếu platform cho phép.",
            "Dựng thử với preview/watermark.",
            "Final thì mở MUSIC_CUE_SHEET.csv hoặc MUSIC_LICENSE_LINKS.html.",
            "Vào đúng link bài, mua/tải bản sạch.",
            "Trong Premiere dùng Replace Footage để thay preview bằng file sạch cùng bài.",
        ],
        "copyright_note": "Không tự tải lậu từ YouTube/video thường. Chỉ dùng preview hợp lệ, YouTube Audio Library, hoặc file đã có license.",
    }


def normalize_track(item: dict[str, str]) -> dict[str, Any]:
    fields = [
        "source",
        "title",
        "artist",
        "url",
        "track_id",
        "duration",
        "bpm",
        "mood",
        "preview_file",
        "final_replace_filename",
        "license_status",
        "notes",
    ]
    out = {key: str(item.get(key, "") or "").strip() for key in fields}
    if not out["license_status"]:
        out["license_status"] = "placeholder_preview"
    return out


def suggest_final_filename(track: dict[str, Any]) -> str:
    source = safe_name(track.get("source") or "music")
    title = safe_name(track.get("title") or "track")
    artist = safe_name(track.get("artist") or "artist")
    return f"{source}_{artist}_{title}_FINAL.wav"


def safe_name(text: str) -> str:
    bad = '<>:"/\\|?*'
    text = "".join("_" if c in bad else c for c in text)
    text = text.strip().replace(" ", "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text[:80] or "untitled"


def load_timeline_info(project_root: Path) -> dict[str, Any]:
    for name in [
        "stt_prewedding_refined_v1.json",
        "stt_prewedding_roughcut_v1.json",
        "stt_prewedding_selection_v1.json",
        "stt_prewedding_pipeline_v1.json",
    ]:
        path = project_root / name
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                timeline = data.get("timeline")
                if isinstance(timeline, list):
                    duration = sum(float(x.get("timeline_duration", 0) or 0) for x in timeline)
                    if not duration:
                        duration = float(data.get("actual_duration_seconds", 0) or data.get("target_duration_seconds", 0) or 60)
                    return {
                        "source_file": str(path),
                        "clip_count": len(timeline),
                        "duration_seconds": round(duration, 3),
                    }
                if data.get("summary"):
                    return {
                        "source_file": str(path),
                        "clip_count": None,
                        "duration_seconds": 60,
                    }
            except Exception:
                pass

    return {
        "source_file": None,
        "clip_count": 0,
        "duration_seconds": 60,
    }


def seconds_to_timecode(seconds: float) -> str:
    seconds = max(0, float(seconds or 0))
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def write_cue_csv(path: Path, tracks: list[dict[str, Any]]) -> None:
    fieldnames = [
        "cue_index",
        "source",
        "title",
        "artist",
        "url",
        "track_id",
        "duration",
        "bpm",
        "mood",
        "preview_file",
        "final_replace_filename",
        "used_in_timeline_start",
        "used_in_timeline_end",
        "timeline_duration_seconds",
        "license_status",
        "replace_method",
        "notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for track in tracks:
            writer.writerow({key: track.get(key, "") for key in fieldnames})


def write_candidate_template(path: Path) -> None:
    fieldnames = [
        "source",
        "title",
        "artist",
        "url",
        "track_id",
        "duration",
        "bpm",
        "mood",
        "preview_file",
        "final_replace_filename",
        "license_status",
        "notes",
    ]
    sample_rows = [
        {
            "source": "Artlist",
            "title": "",
            "artist": "",
            "url": "",
            "track_id": "",
            "duration": "",
            "bpm": "",
            "mood": "",
            "preview_file": "",
            "final_replace_filename": "",
            "license_status": "placeholder_preview",
            "notes": "Điền bài preview đã chọn ở đây.",
        },
        {
            "source": "Musicbed",
            "title": "",
            "artist": "",
            "url": "",
            "track_id": "",
            "duration": "",
            "bpm": "",
            "mood": "",
            "preview_file": "",
            "final_replace_filename": "",
            "license_status": "placeholder_preview",
            "notes": "",
        },
        {
            "source": "YouTube Audio Library",
            "title": "",
            "artist": "",
            "url": "",
            "track_id": "",
            "duration": "",
            "bpm": "",
            "mood": "",
            "preview_file": "",
            "final_replace_filename": "",
            "license_status": "free_or_license_checked",
            "notes": "",
        },
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_rows)


def render_search_prompt(cue_sheet: dict[str, Any]) -> str:
    mood = cue_sheet["music_mood"]
    keywords = ", ".join(mood.get("keywords", []))
    return "\n".join([
        "STT AI Editor - Music Search Prompt",
        "=" * 72,
        f"Intent: {cue_sheet['intent']}",
        f"Mood: {mood.get('mood')}",
        f"BPM: {mood.get('bpm_min')} - {mood.get('bpm_max')}",
        f"Target duration: {mood.get('duration')}s",
        f"Keywords: {keywords}",
        "",
        "Search on:",
        "- Artlist",
        "- Musicbed",
        "- YouTube Audio Library",
        "",
        "Ghi lại đúng các thông tin này vào music_candidates_template.csv:",
        "- source",
        "- title",
        "- artist",
        "- url",
        "- track_id nếu có",
        "- duration",
        "- bpm nếu có",
        "- mood",
        "- preview_file nếu đã tải preview hợp lệ",
        "",
        "Không tự tải lậu nhạc từ YouTube video thường.",
    ])


def render_replace_guide(cue_sheet: dict[str, Any]) -> str:
    lines = [
        "STT AI Editor - Music Replace Guide",
        "=" * 72,
        "",
        "Workflow:",
        "1. Dùng preview/watermark để dựng nháp.",
        "2. Final: mở MUSIC_CUE_SHEET.csv hoặc MUSIC_LICENSE_LINKS.html.",
        "3. Vào đúng link bài đã ghi.",
        "4. Mua/tải bản sạch cùng bài.",
        "5. Trong Premiere: Project panel > right click preview music > Replace Footage.",
        "6. Chọn file final sạch.",
        "",
        "Tracks:",
    ]
    for track in cue_sheet["tracks"]:
        lines += [
            "",
            f"#{track.get('cue_index')}",
            f"Source: {track.get('source')}",
            f"Title: {track.get('title')}",
            f"Artist: {track.get('artist')}",
            f"URL: {track.get('url')}",
            f"Preview: {track.get('preview_file')}",
            f"Final filename: {track.get('final_replace_filename')}",
        ]
    return "\n".join(lines)


def render_links_html(cue_sheet: dict[str, Any]) -> str:
    import html

    rows = []
    for track in cue_sheet["tracks"]:
        url = str(track.get("url") or "")
        url_html = f"<a href='{html.escape(url)}' target='_blank'>{html.escape(url)}</a>" if url else ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(track.get('cue_index')))}</td>"
            f"<td>{html.escape(str(track.get('source')))}</td>"
            f"<td>{html.escape(str(track.get('title')))}</td>"
            f"<td>{html.escape(str(track.get('artist')))}</td>"
            f"<td>{url_html}</td>"
            f"<td>{html.escape(str(track.get('preview_file')))}</td>"
            f"<td>{html.escape(str(track.get('final_replace_filename')))}</td>"
            f"<td>{html.escape(str(track.get('license_status')))}</td>"
            "</tr>"
        )

    return (
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        "<title>Music License Links</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:32px;line-height:1.55}"
        ".card{max-width:1500px;background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "table{border-collapse:collapse;width:100%;margin-top:12px}"
        "th,td{border-bottom:1px solid #333;padding:8px;vertical-align:top;text-align:left}"
        "a{color:#9cf}code{background:#000;padding:4px 8px;border-radius:8px}"
        "</style></head><body><div class='card'>"
        "<h1>Music License Links / Cue Sheet</h1>"
        f"<p>Intent: <code>{html.escape(str(cue_sheet['intent']))}</code></p>"
        "<p>Final dùng file này để biết chính xác bài nào cần mua/tải bản sạch.</p>"
        "<table><tr><th>#</th><th>Source</th><th>Title</th><th>Artist</th><th>URL</th><th>Preview</th><th>Final filename</th><th>Status</th></tr>"
        + "".join(rows) +
        "</table>"
        "<h2>Copyright note</h2>"
        f"<p>{html.escape(str(cue_sheet.get('copyright_note')))}</p>"
        "</div></body></html>"
    )
