
from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/27thang6pschh/souce"


def appdata_dir() -> Path:
    p = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "STT_AI_Editor"
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def outdir(project_root: Path, name: str) -> Path:
    p = project_root / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def open_path(path: Path) -> None:
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


def inum(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def load_analyzer(project_root: Path) -> list[dict[str, Any]]:
    d = read_json(project_root / "stt_wedding_source_analyzer_v2.json") or read_json(appdata_dir() / "stt_wedding_source_analyzer_v2.json")
    return list(d.get("items") or [])


def clean_text(s: str) -> str:
    s = s.lower()
    repl = {
        "á": "a", "à": "a", "ả": "a", "ã": "a", "ạ": "a",
        "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
        "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "é": "e", "è": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
        "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "í": "i", "ì": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ó": "o", "ò": "o", "ỏ": "o", "õ": "o", "ọ": "o",
        "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
        "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ú": "u", "ù": "u", "ủ": "u", "ũ": "u", "ụ": "u",
        "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ý": "y", "ỳ": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
        "đ": "d",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


CHAPTER_KEYWORDS = [
    ("intro_hook", [
        "intro", "hook", "highlight", "teaser", "opening", "open",
        "detail", "details", "decor", "ring", "nhan", "hoa", "dress", "vay", "giay",
        "venue", "khong gian", "space", "setup", "makeup"
    ]),
    ("getting_ready", [
        "getting", "ready", "makeup", "make up", "chuan bi", "co dau", "bride",
        "chu re", "groom", "makeup", "ao dai", "dress", "home bride", "home groom"
    ]),
    ("gia_tien_story", [
        "gia tien", "giatien", "le gia tien", "le gia", "altar", "ban tho",
        "thap huong", "thắp hương", "mam qua", "qua", "trao qua", "family",
        "nha trai", "nha gai", "nghi le", "ceremony", "traditional"
    ]),
    ("ruoc_dau_story", [
        "ruoc dau", "ruocdau", "don dau", "xe hoa", "car", "di chuyen",
        "move", "road", "arrival", "arrive", "walk", "di vao"
    ]),
    ("reception_story", [
        "reception", "tiẹc", "tiec", "party", "sanh", "stage", "san khau",
        "khach", "guest", "photo", "photobooth", "welcome", "dinner", "restaurant"
    ]),
    ("emotion_climax", [
        "vow", "speech", "phat bieu", "wishing", "loi chuc", "cam xuc",
        "cry", "kiss", "hug", "dance", "first dance", "champagne", "cake", "toast"
    ]),
    ("ending_release", [
        "ending", "end", "final", "dance", "party", "after party", "thank", "cam on",
        "last", "outro", "ket"
    ]),
]


EVENT_TO_CHAPTER = {
    "details": "intro_hook",
    "getting_ready": "getting_ready",
    "gia_tien": "gia_tien_story",
    "ruoc_dau": "ruoc_dau_story",
    "reception": "reception_story",
    "vow_speech": "emotion_climax",
    "dance_party": "ending_release",
}


CHAPTER_ORDER = {
    "intro_hook": 10,
    "getting_ready": 20,
    "gia_tien_story": 30,
    "ruoc_dau_story": 40,
    "reception_story": 50,
    "emotion_climax": 60,
    "ending_release": 70,
}


def chapter_from_path(path: str, analyzer_event: str = "") -> tuple[str, str]:
    text = clean_text(path.replace("\\", " / ").replace("_", " ").replace("-", " "))
    scores = []
    for chapter, kws in CHAPTER_KEYWORDS:
        score = 0
        hits = []
        for kw in kws:
            kwc = clean_text(kw)
            if kwc in text:
                score += 2 if "/" in text else 1
                hits.append(kw)
        if score:
            scores.append((score, chapter, ",".join(hits)))
    if scores:
        scores.sort(key=lambda x: (-x[0], CHAPTER_ORDER.get(x[1], 999)))
        return scores[0][1], f"path_keywords:{scores[0][2]}"

    event = str(analyzer_event or "")
    if event in EVENT_TO_CHAPTER:
        return EVENT_TO_CHAPTER[event], f"analyzer_event:{event}"

    return "unknown", "unknown"


def numeric_key(path: str) -> int:
    nums = re.findall(r"\d+", Path(path).stem)
    if not nums:
        return 0
    try:
        return int(nums[-1])
    except Exception:
        return 0


def file_mtime(path: str) -> float:
    try:
        return Path(path).stat().st_mtime
    except Exception:
        return 0.0


def quality_rank(item: dict[str, Any]) -> float:
    score = fnum(item.get("score"), 0)
    decision = str(item.get("decision") or "").lower()
    flags = str(item.get("quality_flags") or "")
    motion = fnum(item.get("motion_score"), 0)
    blur = fnum(item.get("blur_score"), 0)

    if decision == "strong_pick":
        score += 25
    elif decision == "keep":
        score += 12
    elif decision == "review":
        score -= 2
    elif decision == "reject":
        score -= 100

    if "possible_out_focus" in flags:
        score -= 25
    if "too_dark" in flags or "too_bright" in flags:
        score -= 22
    if motion > 55:
        score -= 18
    if blur >= 120:
        score += 7
    elif 0 < blur < 35:
        score -= 14
    return round(score, 3)


def create_wedding_story_role_classifier(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    source_folder: str | Path = DEFAULT_SOURCE_FOLDER,
    order_mode: str = "chapter_then_time",
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "wedding_story_role_classifier_127")

    items = load_analyzer(project_root)
    if not items:
        res = {"ok": False, "error": "NO_ANALYZER_ITEMS", "message": "Run 110 first."}
        write_json(out / "story_role_classifier_error.json", res)
        if open_folder:
            open_path(out)
        return res

    rows = []
    for i, item in enumerate(items, start=1):
        path = str(item.get("file") or "")
        if not path:
            continue
        event = str(item.get("event") or "unknown")
        chapter, reason = chapter_from_path(path, event)
        mtime = file_mtime(path)
        num = numeric_key(path)
        q = quality_rank(item)

        # If chapter unknown, use chronological block later.
        row = dict(item)
        row.update({
            "story_chapter": chapter,
            "story_reason": reason,
            "story_chapter_order": CHAPTER_ORDER.get(chapter, 999),
            "file_mtime": mtime,
            "file_number": num,
            "rank_score": q,
            "source_path": path,
        })
        rows.append(row)

    # Assign unknown by chronological blocks, so source without folder names still has rough story order.
    known = [r for r in rows if r.get("story_chapter") != "unknown"]
    unknown = [r for r in rows if r.get("story_chapter") == "unknown"]
    if unknown:
        unknown.sort(key=lambda r: (fnum(r.get("file_mtime"), 0), inum(r.get("source_order"), 0), inum(r.get("file_number"), 0)))
        blocks = [
            ("intro_hook", 0.08),
            ("getting_ready", 0.14),
            ("gia_tien_story", 0.28),
            ("ruoc_dau_story", 0.12),
            ("reception_story", 0.18),
            ("emotion_climax", 0.14),
            ("ending_release", 0.06),
        ]
        total = len(unknown)
        pos = 0
        for idx, (chapter, frac) in enumerate(blocks):
            count = total - pos if idx == len(blocks) - 1 else max(1, int(round(total * frac)))
            for r in unknown[pos:pos+count]:
                r["story_chapter"] = chapter
                r["story_reason"] = "chrono_block_fallback"
                r["story_chapter_order"] = CHAPTER_ORDER[chapter]
            pos += count
            if pos >= total:
                break

    # Final strict order list.
    if order_mode == "time_then_chapter":
        rows.sort(key=lambda r: (fnum(r.get("file_mtime"), 0), inum(r.get("story_chapter_order"), 999), inum(r.get("source_order"), 0), inum(r.get("file_number"), 0)))
    else:
        rows.sort(key=lambda r: (inum(r.get("story_chapter_order"), 999), fnum(r.get("file_mtime"), 0), inum(r.get("source_order"), 0), inum(r.get("file_number"), 0)))

    for idx, r in enumerate(rows, start=1):
        r["story_order"] = idx

    chapter_counts: dict[str, int] = {}
    for r in rows:
        c = str(r.get("story_chapter") or "unknown")
        chapter_counts[c] = chapter_counts.get(c, 0) + 1

    data = {
        "ok": True,
        "module": "127_wedding_story_role_classifier",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source_folder": str(source_folder),
        "order_mode": order_mode,
        "item_count": len(rows),
        "chapter_counts": chapter_counts,
        "items": rows,
    }

    write_json(project_root / "stt_wedding_story_roles_v1.json", data)
    write_json(appdata_dir() / "stt_wedding_story_roles_v1.json", data)
    write_json(out / "stt_wedding_story_roles_v1.json", data)
    write_csv(out / "WEDDING_STORY_ROLES.csv", rows, [
        "story_order", "filename", "story_chapter", "event", "story_reason", "rank_score", "source_order", "file_number", "file_mtime", "file",
    ])
    (out / "WEDDING_STORY_ROLES_REPORT.html").write_text(
        make_html(
            "Wedding Story Role Classifier 127",
            rows,
            ["story_order", "filename", "story_chapter", "event", "story_reason", "rank_score", "source_order"],
            "127 phân lại story/chapter từ folder path + filename + thời gian file, để 126B xếp timeline đúng thứ tự hơn.",
        ),
        encoding="utf-8",
    )
    if open_folder:
        open_path(out)

    return {
        "ok": True,
        "report_dir": str(out),
        "item_count": len(rows),
        "chapter_counts": chapter_counts,
        "fix": "127_wedding_story_role_classifier",
    }


def make_html(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
    import html
    th = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    tr = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(r.get(c,'')))}</td>" for c in cols) + "</tr>"
        for r in rows
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:Arial;background:#111;color:#eee;margin:32px}"
        ".card{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "td,th{border-bottom:1px solid #333;padding:8px;text-align:left;font-size:13px}</style></head>"
        f"<body><div class='card'><h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{th}</tr>{tr}</table></div></body></html>"
    )
