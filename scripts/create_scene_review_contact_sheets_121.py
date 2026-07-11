from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> dict[str, Any]:
    try:
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def write_csv(path: str | Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def outdir(project: Path, name: str) -> Path:
    p = project / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def open_path(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def safe_name(s: str) -> str:
    keep = []
    for ch in s:
        if ch.isalnum() or ch in "_-.":
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep)[:140]


def get_thumb(path: Path, sec: float, width: int, height: int):
    import cv2  # type: ignore
    from PIL import Image

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0

    if fps > 0 and frames > 0:
        duration = frames / fps
        sec = max(0.1, min(duration * 0.80, sec if sec > 0 else duration * 0.45))
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
    else:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 5)

    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame)
    img.thumbnail((width, height))
    bg = Image.new("RGB", (width, height), (20, 20, 20))
    x = (width - img.width) // 2
    y = (height - img.height) // 2
    bg.paste(img, (x, y))
    return bg


def draw_text(draw, xy, text, font, fill=(255, 255, 255), max_chars=40):
    s = str(text or "")
    if len(s) > max_chars:
        s = s[:max_chars-3] + "..."
    draw.text(xy, s, font=font, fill=fill)


def make_sheet(tag: str, rows: list[dict[str, Any]], out: Path, max_per_tag: int, thumb_w: int, thumb_h: int, cols: int) -> dict[str, Any]:
    from PIL import Image, ImageDraw, ImageFont

    selected = rows[:max_per_tag]
    label_h = 72
    tile_w = thumb_w
    tile_h = thumb_h + label_h
    rows_n = max(1, math.ceil(len(selected) / cols))
    sheet = Image.new("RGB", (cols * tile_w, rows_n * tile_h), (12, 12, 12))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    ok_count = 0
    fail_count = 0
    for idx, r in enumerate(selected):
        p = Path(str(r.get("file") or ""))
        x = (idx % cols) * tile_w
        y = (idx // cols) * tile_h
        sec = fnum(r.get("best_source_in_sec"), 0)
        if sec <= 0:
            sec = max(0.5, fnum(r.get("media_duration_sec"), 0) * 0.45)

        thumb = None
        if p.exists() and p.suffix.lower() != ".braw":
            try:
                thumb = get_thumb(p, sec, thumb_w, thumb_h)
            except Exception:
                thumb = None

        if thumb is None:
            fail_count += 1
            thumb = Image.new("RGB", (thumb_w, thumb_h), (45, 45, 45))
            d2 = ImageDraw.Draw(thumb)
            d2.text((12, 12), "NO PREVIEW / BRAW", font=font, fill=(255, 180, 180))
        else:
            ok_count += 1

        sheet.paste(thumb, (x, y))
        label_y = y + thumb_h + 4
        draw_text(draw, (x+6, label_y), f"{idx+1}. {r.get('filename','')}", font, max_chars=34)
        draw_text(draw, (x+6, label_y+22), f"conf={r.get('confidence','')} margin={r.get('margin','')}", font_small, fill=(190, 190, 190), max_chars=38)
        draw_text(draw, (x+6, label_y+42), str(r.get("top_tags", "")), font_small, fill=(150, 200, 255), max_chars=48)

    out_file = out / f"{safe_name(tag)}__count_{len(rows)}__show_{len(selected)}.jpg"
    sheet.save(out_file, quality=90)
    return {"scene_tag": tag, "count": len(rows), "shown": len(selected), "preview_ok": ok_count, "preview_fail": fail_count, "contact_sheet": str(out_file)}


def main() -> None:
    p = argparse.ArgumentParser(description="121 Scene review contact sheets from visual AI tags.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--json", default="", help="default: project/stt_visual_ai_scene_tags_v1.json")
    p.add_argument("--max-per-tag", type=int, default=60)
    p.add_argument("--thumb-width", type=int, default=320)
    p.add_argument("--thumb-height", type=int, default=180)
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    json_path = Path(a.json) if a.json else project / "stt_visual_ai_scene_tags_v1.json"
    out = outdir(project, "scene_review_contact_sheets_121")

    data = read_json(json_path)
    items = list(data.get("items") or [])
    if not items:
        res = {
            "ok": False,
            "error": "NO_SCENE_TAG_ITEMS",
            "json": str(json_path),
            "message": "Run 119E first.",
        }
        (out / "scene_review_error.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in items:
        tag = str(r.get("scene_tag") or "other")
        grouped.setdefault(tag, []).append(r)

    summaries = []
    for tag in sorted(grouped.keys()):
        rows = grouped[tag]
        summaries.append(make_sheet(tag, rows, out, a.max_per_tag, a.thumb_width, a.thumb_height, a.cols))

    flat = []
    for tag, rows in grouped.items():
        for r in rows:
            flat.append({
                "scene_tag": tag,
                "filename": r.get("filename", ""),
                "confidence": r.get("confidence", ""),
                "margin": r.get("margin", ""),
                "top_tags": r.get("top_tags", ""),
                "file": r.get("file", ""),
            })
    write_csv(out / "SCENE_REVIEW_ALL_TAGS.csv", flat, ["scene_tag", "filename", "confidence", "margin", "top_tags", "file"])
    write_csv(out / "SCENE_REVIEW_SUMMARY.csv", summaries, ["scene_tag", "count", "shown", "preview_ok", "preview_fail", "contact_sheet"])

    result = {
        "ok": True,
        "module": "121_scene_review_contact_sheets",
        "report_dir": str(out),
        "json": str(json_path),
        "file_count": len(items),
        "tag_count": len(grouped),
        "summary": summaries,
        "fix": "121_scene_review_contact_sheets",
    }
    (out / "scene_review_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "file_count": len(items),
        "tag_count": len(grouped),
        "summary_csv": str(out / "SCENE_REVIEW_SUMMARY.csv"),
        "all_tags_csv": str(out / "SCENE_REVIEW_ALL_TAGS.csv"),
        "fix": "121_scene_review_contact_sheets",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
