from __future__ import annotations
import csv, json, os
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

def read_csv(path: str | Path) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

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

def boolish(v: Any) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y", "x"}

def duration_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [fnum(x.get("duration_sec"), 0) for x in items if fnum(x.get("duration_sec"), 0) > 0]
    if not vals:
        return {}
    xs = sorted(vals)
    def pct(p: float) -> float:
        return round(xs[int(round((len(xs)-1)*p))], 3)
    return {
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "avg": round(sum(vals)/len(vals), 3),
        "p10": pct(0.10),
        "p50": pct(0.50),
        "p90": pct(0.90),
        "under_0_7s": sum(1 for v in vals if v < 0.7),
        "over_3s": sum(1 for v in vals if v > 3.0),
        "over_5s": sum(1 for v in vals if v > 5.0),
    }

def load_beats(project: Path) -> list[dict[str, Any]]:
    d = read_json(project / "stt_precise_beat_grid_v2.json")
    return list(d.get("beats") or [])

def parse_top_tags(s: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for part in str(s or "").split(";"):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        k = k.strip()
        try:
            scores[k] = float(v)
        except Exception:
            pass
    return scores

def score(scores: dict[str, float], tag: str) -> float:
    return float(scores.get(tag, 0.0))

def best_of(scores: dict[str, float], tags: list[str]) -> tuple[str, float]:
    best_t, best_s = "", -1.0
    for t in tags:
        s = score(scores, t)
        if s > best_s:
            best_t, best_s = t, s
    return best_t, best_s

def count_tags(items: list[dict[str, Any]]) -> dict[str, int]:
    return {t: sum(1 for x in items if x.get("scene_tag") == t) for t in SCENE_TAGS}

def load_beauty(project: Path):
    d = read_json(project / "stt_scene_beauty_v1.json")
    by_path, by_name = {}, {}
    for r in d.get("items", []):
        p = str(r.get("file") or "").replace("\\", "/").lower()
        n = str(r.get("filename") or "").lower()
        if p:
            by_path[p] = r
        if n:
            by_name.setdefault(n, r)
    return by_path, by_name
