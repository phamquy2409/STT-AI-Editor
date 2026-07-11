from __future__ import annotations
import csv, json, math, os, statistics
from datetime import datetime
from pathlib import Path
from typing import Any

SCENE_TAGS = [
    "decor", "detail_beauty", "getting_ready", "first_look", "cdcr_portrait",
    "ceremony_giatien", "church_ceremony", "vow", "ruoc_dau", "reception_stage",
    "wedding_game", "family_photo", "family_emotion", "guest_food", "party", "ending", "other"
]

def read_json(path: str | Path) -> dict[str, Any]:
    try:
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

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

def norm_path(v: Any) -> str:
    return str(v or "").replace("\\", "/").strip().lower()

def filename(v: Any) -> str:
    try:
        return Path(str(v or "")).name.lower()
    except Exception:
        return str(v or "").lower()

def median(vals: list[float], default: float = 0.0) -> float:
    return float(statistics.median(vals)) if vals else default

def mean(vals: list[float], default: float = 0.0) -> float:
    return float(sum(vals) / len(vals)) if vals else default

def pct(vals: list[float], p: float, default: float = 0.0) -> float:
    if not vals:
        return default
    xs = sorted(vals)
    idx = int(round((len(xs) - 1) * p))
    return float(xs[max(0, min(len(xs)-1, idx))])

def parse_top_tags(s: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in str(s or "").split(";"):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        try:
            out[k.strip()] = float(v)
        except Exception:
            pass
    return out

def load_beats(project: Path) -> list[dict[str, Any]]:
    return list(read_json(project / "stt_precise_beat_grid_v2.json").get("beats") or [])

def load_beauty(project: Path):
    d = read_json(project / "stt_scene_beauty_v1.json")
    by_path, by_name = {}, {}
    for r in d.get("items", []):
        p = norm_path(r.get("file"))
        n = str(r.get("filename") or "").lower()
        if p:
            by_path[p] = r
        if n:
            by_name.setdefault(n, r)
    return by_path, by_name

def duration_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [fnum(x.get("duration_sec"), 0) for x in items if fnum(x.get("duration_sec"), 0) > 0]
    if not vals:
        return {}
    return {
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "avg": round(mean(vals), 3),
        "p10": round(pct(vals, 0.10), 3),
        "p50": round(pct(vals, 0.50), 3),
        "p90": round(pct(vals, 0.90), 3),
        "under_0_7s": sum(1 for v in vals if v < 0.7),
        "over_3s": sum(1 for v in vals if v > 3.0),
        "over_5s": sum(1 for v in vals if v > 5.0),
    }

def count_tags(items: list[dict[str, Any]]) -> dict[str, int]:
    return {t: sum(1 for x in items if x.get("scene_tag") == t) for t in SCENE_TAGS}
