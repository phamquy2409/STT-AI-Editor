from __future__ import annotations
import csv, json, os, subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv", ".braw"}
SCENE_TAGS = [
    "decor", "detail_beauty", "getting_ready", "first_look", "cdcr_portrait",
    "ceremony_giatien", "church_ceremony", "vow", "ruoc_dau", "reception_stage",
    "wedding_game", "family_photo", "family_emotion", "guest_food", "party", "ending", "other"
]
PROXY_DIR_NAMES = {"proxy", "proxies", "proxy media", "proxy_media", "adobe premiere pro video previews", "premiere pro video previews"}
PROXY_NAME_TOKENS = ["_proxy", "-proxy", " proxy.", "_proxy.", "-proxy.", "proxy_"]

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

def is_proxy_path(path: Path) -> bool:
    parts = [p.strip().lower() for p in path.parts]
    if any(part in PROXY_DIR_NAMES for part in parts):
        return True
    name = path.name.lower()
    stem = path.stem.lower()
    if stem.endswith("_proxy") or stem.endswith("-proxy") or stem.endswith(" proxy"):
        return True
    return any(tok in name for tok in PROXY_NAME_TOKENS)

def list_original_files(source: Path) -> tuple[list[Path], list[Path]]:
    all_files = []
    for ext in VIDEO_EXTS:
        all_files.extend(source.rglob(f"*{ext}"))
    all_files = sorted(set(all_files), key=lambda p: str(p).lower())
    proxies = [p for p in all_files if is_proxy_path(p)]
    originals = [p for p in all_files if not is_proxy_path(p)]
    return originals, proxies

def media_duration(path: str | Path) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and (r.stdout or "").strip():
            return float((r.stdout or "").strip())
    except Exception:
        pass
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(str(path))
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            if fps > 0 and frames > 0:
                return float(frames / fps)
    except Exception:
        pass
    return 0.0

def sample_frames(path: Path, frame_samples: int) -> list[Any]:
    try:
        import cv2  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        return []
    if path.suffix.lower() == ".braw":
        return []
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return []
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frames <= 1:
        cap.release()
        return []
    imgs = []
    for i in range(frame_samples):
        alpha = 0.08 + (0.84 * i / max(1, frame_samples - 1))
        pos = int(max(0, min(frames - 1, frames * alpha)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imgs.append(Image.fromarray(frame))
    cap.release()
    return imgs

def softmax(xs: list[float]) -> list[float]:
    import math
    if not xs:
        return []
    m = max(xs)
    ex = [math.exp(x - m) for x in xs]
    s = sum(ex) or 1.0
    return [v / s for v in ex]

def l2norm(torch, x):
    return x / x.norm(dim=-1, keepdim=True).clamp(min=1e-12)

def load_clip(model_name: str):
    try:
        import torch  # type: ignore
        from transformers import CLIPModel, CLIPProcessor  # type: ignore
    except Exception as e:
        raise RuntimeError("MISSING_DEPS: python -m pip install -U torch torchvision transformers pillow opencv-python") from e
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(model_name).to(device)
    processor = CLIPProcessor.from_pretrained(model_name)
    model.eval()
    return torch, model, processor, device

def get_text_feats(torch, model, processor, device, texts: list[str]):
    inputs = processor(text=texts, return_tensors="pt", padding=True, truncation=True).to(device)
    with torch.no_grad():
        try:
            feats = model.get_text_features(**inputs)
            if hasattr(feats, "norm"):
                return l2norm(torch, feats)
        except Exception:
            pass
        text_inputs = {k: v for k, v in inputs.items() if k in {"input_ids", "attention_mask", "position_ids"}}
        out = model.text_model(**text_inputs)
        pooled = out.pooler_output if hasattr(out, "pooler_output") else out[1]
        if hasattr(model, "text_projection"):
            pooled = model.text_projection(pooled)
        return l2norm(torch, pooled)

def get_image_feats(torch, model, processor, device, images: list[Any]):
    inputs = processor(images=images, return_tensors="pt").to(device)
    with torch.no_grad():
        try:
            feats = model.get_image_features(**inputs)
            if hasattr(feats, "norm"):
                return l2norm(torch, feats)
        except Exception:
            pass
        out = model.vision_model(pixel_values=inputs["pixel_values"])
        pooled = out.pooler_output if hasattr(out, "pooler_output") else out[1]
        if hasattr(model, "visual_projection"):
            pooled = model.visual_projection(pooled)
        return l2norm(torch, pooled)

def load_beats(project: Path) -> list[dict[str, Any]]:
    d = read_json(project / "stt_precise_beat_grid_v2.json")
    return list(d.get("beats") or [])

def load_music_duration(project: Path) -> float:
    for name in ["stt_precise_beat_grid_v2.json", "stt_music_director_map_v1.json", "stt_music_beat_map_v1.json"]:
        d = read_json(project / name)
        p = str(d.get("music_file") or "")
        if p and Path(p).exists():
            return media_duration(p)
    return 0.0

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
