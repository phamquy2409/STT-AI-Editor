from __future__ import annotations
import csv, json, os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

def read_json(path):
    try:
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def write_csv(path, rows, cols):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

def outdir(project: Path, name: str):
    p = project / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def open_path(path):
    try:
        os.startfile(str(path))
    except Exception:
        pass

def fnum(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def inum(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def norm_path(v):
    return str(v or "").replace("\\", "/").strip().lower()

def semantic_family(tag):
    tag = str(tag or "other")
    mapping = {
        "decor": "establishing",
        "detail_beauty": "detail",
        "getting_ready": "preparation",
        "first_look": "couple",
        "cdcr_portrait": "couple",
        "ceremony_giatien": "ceremony",
        "church_ceremony": "ceremony",
        "vow": "ceremony",
        "ruoc_dau": "procession",
        "reception_stage": "reception",
        "wedding_game": "reception",
        "family_photo": "family",
        "family_emotion": "family",
        "guest_food": "guest",
        "party": "party",
        "ending": "couple",
        "other": "other",
    }
    return mapping.get(tag, "other")
