from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
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

PROMPTS = {
    "decor": [
        "empty wedding venue decoration, flowers and stage, no bride, no groom, no people portrait",
        "wide shot of wedding reception decoration without people eating",
        "wedding ceremony arch and floral decor with no couple",
        "beautiful banquet hall decoration, tables and lights, no couple portrait",
        "empty wedding stage decoration before guests arrive",
        "cinematic wedding venue establishing shot with decorations",
    ],
    "detail_beauty": [
        "close up of wedding rings",
        "close up of bridal dress hanging",
        "close up of bridal shoes",
        "close up of wedding bouquet flowers",
        "wedding invitation and small detail flat lay",
        "cinematic wedding detail close up, no faces",
    ],
    "getting_ready": [
        "bride getting makeup, makeup artist touching bride face",
        "bride getting ready before ceremony",
        "bride putting on wedding dress with bridesmaids",
        "groom putting on suit or tie",
        "hair stylist working on bride hair",
        "preparation room before wedding ceremony",
    ],
    "first_look": [
        "bride and groom first look, couple alone seeing each other for the first time",
        "groom reacts emotionally seeing bride for first time",
        "bride walks to groom for first look, no crowd around",
        "wedding couple holding hands alone before ceremony",
        "emotional private first look moment bride and groom",
    ],
    "cdcr_portrait": [
        "bride and groom portrait only, romantic couple posing",
        "wedding couple walking together alone",
        "newlywed bride and groom posing for cinematic portrait",
        "close up bride and groom smiling together",
        "bride and groom couple session outdoors",
        "romantic couple portrait during wedding day",
    ],
    "ceremony_giatien": [
        "Vietnamese traditional wedding ceremony at family altar",
        "bride and groom in front of ancestor altar inside house",
        "incense ritual during Vietnamese wedding ceremony",
        "families giving gifts during traditional Vietnamese wedding",
        "red Vietnamese wedding gift trays ceremony inside house",
    ],
    "church_ceremony": [
        "bride and groom at church altar",
        "wedding ceremony inside church with priest",
        "Catholic church wedding ceremony",
        "bride walking down church aisle",
        "church wedding vows at altar",
        "priest officiating wedding ceremony",
    ],
    "vow": [
        "bride reading wedding vows with microphone",
        "groom reading wedding vows with microphone",
        "bride and groom holding vow cards",
        "emotional wedding vow speech during ceremony",
        "couple speaking vows to each other, ceremony scene",
    ],
    "ruoc_dau": [
        "Vietnamese wedding procession carrying red gift trays outdoors",
        "groom family carrying traditional red trays to bride house",
        "wedding procession walking outside with gift trays",
        "traditional Vietnamese engagement procession with red boxes",
        "people in traditional wedding procession entering house",
    ],
    "reception_stage": [
        "bride and groom on wedding reception stage",
        "wedding reception stage with LED screen and lights",
        "wedding speech on stage with microphone",
        "wedding cake champagne tower on reception stage",
        "couple standing on banquet stage at night",
    ],
    "wedding_game": [
        "wedding reception game on stage at night",
        "guests playing funny game at wedding reception",
        "people playing group game with microphone at wedding",
        "night wedding game activity on stage",
        "fun reception game with bride and groom",
    ],
    "family_photo": [
        "formal family group photo at wedding",
        "large group photo with bride and groom and relatives",
        "parents and relatives posing for wedding photo",
        "family standing together for posed group photo",
        "wedding family portrait on stage",
    ],
    "family_emotion": [
        "parents hugging bride or groom emotionally",
        "emotional family moment at wedding",
        "mother crying during wedding",
        "parents blessing bride and groom",
        "bride and groom emotional moment with parents",
    ],
    "guest_food": [
        "wedding guests eating dinner at tables",
        "people eating food at banquet table",
        "plates of food on wedding reception table",
        "buffet food table at wedding",
        "guests sitting and eating at reception",
    ],
    "party": [
        "wedding dance floor with colorful lights",
        "people dancing at wedding party",
        "DJ lights at wedding reception party",
        "guests dancing at night wedding party",
        "bride and groom dancing during party",
    ],
    "ending": [
        "final romantic wedding shot bride and groom",
        "bride and groom farewell ending scene",
        "emotional wedding ending montage shot",
        "couple walking away at end of wedding",
        "beautiful leftover couple shot for ending",
    ],
    "other": [
        "unclear random wedding footage",
        "general people standing around not important",
        "camera test or transition shot",
        "unimportant wedding footage",
    ],
}

STRICT_TAGS = {
    "ruoc_dau": (0.050, 0.015),
    "vow": (0.044, 0.012),
    "first_look": (0.044, 0.010),
    "ceremony_giatien": (0.044, 0.012),
    "church_ceremony": (0.044, 0.012),
    "guest_food": (0.044, 0.012),
}

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
    positions = []
    if frame_samples <= 5:
        positions = [0.12, 0.30, 0.50, 0.70, 0.88][:frame_samples]
    else:
        positions = [0.08 + (0.84 * i / max(1, frame_samples - 1)) for i in range(frame_samples)]
    for alpha in positions:
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

def build_text_bank(torch, model, processor, device):
    texts, tags = [], []
    for tag, prompts in PROMPTS.items():
        for p in prompts:
            texts.append("a photo of " + p)
            tags.append(tag)
    feats = get_text_feats(torch, model, processor, device, texts)
    return texts, tags, feats

def aggregate_frame_scores(torch, model, processor, device, text_tags, text_feats, images):
    if not images:
        return {}, []
    img_feats = get_image_feats(torch, model, processor, device, images)
    logits = (img_feats @ text_feats.T) * 100.0

    frame_top = []
    tag_frame_scores = {t: [] for t in PROMPTS.keys()}

    for i in range(logits.shape[0]):
        probs = softmax(logits[i].detach().cpu().tolist())
        per_tag = {t: 0.0 for t in PROMPTS.keys()}
        for j, prob in enumerate(probs):
            tag = text_tags[j]
            if prob > per_tag[tag]:
                per_tag[tag] = float(prob)

        top = sorted(per_tag.items(), key=lambda x: x[1], reverse=True)[:5]
        frame_top.append(";".join([f"{k}:{v:.4f}" for k, v in top]))

        for tag, sc in per_tag.items():
            tag_frame_scores[tag].append(sc)

    agg = {}
    for tag, vals in tag_frame_scores.items():
        vals_sorted = sorted(vals, reverse=True)
        # Use both average and top frames. This helps clips whose scene changes mid-clip.
        top3 = vals_sorted[:max(1, min(3, len(vals_sorted)))]
        avg = sum(vals) / max(1, len(vals))
        topavg = sum(top3) / max(1, len(top3))
        vote_count = sum(1 for v in vals if v >= max(0.035, topavg * 0.65))
        agg[tag] = (topavg * 0.70) + (avg * 0.20) + (vote_count / max(1, len(vals)) * 0.10)

    return agg, frame_top

def refine_tag_by_sequence(best: str, scores: dict[str, float], pos: float) -> tuple[str, str]:
    sorted_tags = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_score = scores.get(best, 0.0)
    second_score = sorted_tags[1][1] if len(sorted_tags) > 1 else 0
    margin = best_score - second_score

    # Strict rare tags need strong confidence. If weak, choose more general or context-safe tag.
    if best in STRICT_TAGS:
        min_conf, min_margin = STRICT_TAGS[best]
        if best_score < min_conf or margin < min_margin:
            for tag, sc in sorted_tags[1:8]:
                if tag in {"decor", "detail_beauty", "getting_ready", "cdcr_portrait", "family_photo", "family_emotion", "reception_stage", "wedding_game", "party", "ending"} and sc >= 0.035:
                    return tag, f"strict_demote_{best}_to_{tag}"

    # Late vow is usually wrong in this source type; prefer game/stage/party/family.
    if best == "vow" and pos > 0.65:
        t, s = max([(t, scores.get(t, 0.0)) for t in ["wedding_game", "reception_stage", "party", "family_photo", "family_emotion", "ending"]], key=lambda x: x[1])
        if s >= 0.030:
            return t, "late_vow_context_demote"

    # Late getting-ready is almost never right.
    if best == "getting_ready" and pos > 0.62:
        t, s = max([(t, scores.get(t, 0.0)) for t in ["cdcr_portrait", "family_photo", "family_emotion", "wedding_game", "reception_stage", "party", "ending"]], key=lambda x: x[1])
        if s >= 0.028:
            return t, "late_getting_ready_context_demote"

    # Decor over-detection: if people/couple/stage score close, choose people tag.
    if best == "decor":
        t, s = max([(t, scores.get(t, 0.0)) for t in ["cdcr_portrait", "getting_ready", "first_look", "family_photo", "family_emotion", "reception_stage", "wedding_game", "party"]], key=lambda x: x[1])
        if s >= best_score * 0.72 and s >= 0.035:
            return t, "decor_overdetect_people_or_stage"

    # First look only early-mid, private couple moment.
    if best == "first_look" and pos > 0.55:
        t, s = max([(t, scores.get(t, 0.0)) for t in ["cdcr_portrait", "family_photo", "reception_stage", "wedding_game"]], key=lambda x: x[1])
        if s >= 0.030:
            return t, "late_first_look_to_context"

    # Rước dâu late is not accepted.
    if best == "ruoc_dau" and pos > 0.58:
        t, s = max([(t, scores.get(t, 0.0)) for t in ["family_photo", "family_emotion", "wedding_game", "reception_stage", "party"]], key=lambda x: x[1])
        if s >= 0.030:
            return t, "late_ruoc_dau_to_context"

    return best, "keep"

def classify_clip(torch, model, processor, device, text_tags, text_feats, images, pos: float) -> dict[str, Any]:
    if not images:
        return {"scene_tag": "other", "confidence": 0, "margin": 0, "top_tags": "other:0", "frame_top_tags": "", "frame_count": 0, "semantic_reason": "no_frames"}

    scores, frame_top = aggregate_frame_scores(torch, model, processor, device, text_tags, text_feats, images)
    sorted_tags = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    raw_best, raw_score = sorted_tags[0]
    second = sorted_tags[1][1] if len(sorted_tags) > 1 else 0
    best, reason = refine_tag_by_sequence(raw_best, scores, pos)
    confidence = scores.get(best, raw_score)
    top_tags = ";".join([f"{k}:{v:.4f}" for k, v in sorted_tags[:8]])

    return {
        "scene_tag": best,
        "raw_scene_tag": raw_best,
        "confidence": round(float(confidence), 4),
        "margin": round(float(raw_score - second), 4),
        "top_tags": top_tags,
        "frame_top_tags": " | ".join(frame_top),
        "frame_count": len(images),
        "semantic_reason": reason,
    }

def main() -> None:
    p = argparse.ArgumentParser(description="119G Strong visual AI recognizer using CLIP large + frame voting.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--frame-samples", type=int, default=7)
    p.add_argument("--model", default="openai/clip-vit-large-patch14")
    p.add_argument("--max-files", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "strong_visual_ai_large_clip_119g")

    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "strong_visual_ai_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    originals, proxies = list_original_files(source)
    if a.max_files and a.max_files > 0:
        originals = originals[:a.max_files]

    try:
        torch, model, processor, device = load_clip(a.model)
        _, text_tags, text_feats = build_text_bank(torch, model, processor, device)
    except Exception as e:
        res = {"ok": False, "error": "STRONG_VISUAL_AI_MODEL_NOT_READY", "message": repr(e)}
        write_json(out / "strong_visual_ai_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    items = []
    total = len(originals)
    for i, f in enumerate(originals, start=1):
        if i == 1 or i % 10 == 0 or i == total:
            print(f"[119G] strong visual AI {i}/{total}: {f.name}", flush=True)

        if f.suffix.lower() == ".braw":
            item: dict[str, Any] = {
                "filename": f.name, "file": str(f), "scene_tag": "other",
                "raw_scene_tag": "other", "confidence": 0, "margin": 0,
                "top_tags": "braw_not_supported_by_cv2", "frame_top_tags": "",
                "frame_count": 0, "semantic_reason": "braw_not_decoded_original_kept",
                "ai_reason": "braw_not_decoded",
            }
        else:
            imgs = sample_frames(f, a.frame_samples)
            cls = classify_clip(torch, model, processor, device, text_tags, text_feats, imgs, (i - 1) / max(1, total))
            item = {"filename": f.name, "file": str(f), **cls, "ai_reason": "strong_clip_large_frame_voting_119g"}

        item["_source_order"] = i - 1
        item["source_order_pos"] = round((i - 1) / max(1, total), 4)
        item["media_duration_sec"] = media_duration(f)
        item["is_proxy"] = False
        items.append(item)

    counts = {t: sum(1 for x in items if x.get("scene_tag") == t) for t in SCENE_TAGS}
    raw_counts = {t: sum(1 for x in items if x.get("raw_scene_tag") == t) for t in SCENE_TAGS}
    data = {
        "ok": True,
        "module": "119G_strong_visual_ai_large_clip",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "model": a.model,
        "device": device,
        "source": str(source),
        "file_count": len(items),
        "skipped_proxy_count": len(proxies),
        "scene_counts": counts,
        "raw_scene_counts": raw_counts,
        "items": items,
    }

    # Overwrite normal input for planners/contact sheets.
    write_json(project / "stt_visual_ai_scene_tags_v1.json", data)
    write_json(project / "stt_strong_visual_ai_scene_tags_119g.json", data)
    write_json(out / "stt_strong_visual_ai_scene_tags_119g.json", data)
    write_csv(out / "STRONG_VISUAL_AI_TAGS_119G.csv", items, [
        "filename", "scene_tag", "raw_scene_tag", "confidence", "margin", "semantic_reason",
        "top_tags", "frame_top_tags", "frame_count", "source_order_pos", "media_duration_sec", "is_proxy", "file"
    ])
    write_csv(out / "SKIPPED_PROXY_FILES.csv", [{"filename": p.name, "file": str(p)} for p in proxies], ["filename", "file"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "model": a.model,
        "device": device,
        "file_count": len(items),
        "skipped_proxy_count": len(proxies),
        "scene_counts": counts,
        "raw_scene_counts": raw_counts,
        "fix": "119G_strong_visual_ai_large_clip",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
