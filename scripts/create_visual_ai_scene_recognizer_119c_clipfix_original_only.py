from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv", ".braw"}

PROMPTS = {
    "intro_beauty": [
        "wedding rings close up",
        "bridal dress close up",
        "wedding flowers bouquet close up",
        "wedding venue decoration",
        "cinematic wedding detail shot",
        "wedding invitation details",
        "beautiful wedding table decoration without people eating",
    ],
    "cdcr": [
        "bride and groom portrait",
        "wedding couple standing together",
        "bride and groom walking together",
        "romantic wedding couple shot",
        "close up of bride and groom",
    ],
    "makeup": [
        "bride getting makeup",
        "makeup artist applying makeup to bride",
        "bride getting ready before wedding",
        "wedding preparation makeup scene",
    ],
    "ceremony_giatien": [
        "traditional wedding ceremony with family",
        "bride and groom at family altar",
        "wedding ceremony altar",
        "bride and groom doing wedding ritual",
        "people giving gifts during wedding ceremony",
    ],
    "ruoc_dau": [
        "wedding procession",
        "groom arrives at bride house",
        "bride and groom entering house",
        "wedding car procession",
        "traditional Vietnamese wedding procession",
    ],
    "reception_stage": [
        "wedding reception stage",
        "bride and groom on wedding stage",
        "wedding speech on stage",
        "wedding cake and champagne tower",
        "wedding banquet stage with lights",
    ],
    "guest_food": [
        "wedding guests eating at dinner table",
        "people eating food at wedding reception",
        "buffet food table at wedding",
        "food plates on banquet table",
        "guests sitting and eating at tables",
    ],
    "party": [
        "people dancing at wedding party",
        "wedding dance floor lights",
        "DJ party lights at wedding",
        "bride groom dancing party",
        "guests dancing at reception",
    ],
    "family": [
        "family group photo at wedding",
        "bride and groom with parents",
        "relatives family wedding photo",
        "parents hugging bride and groom",
    ],
    "ending": [
        "emotional wedding ending",
        "bride and groom walking away",
        "wedding farewell scene",
        "couple hugging at end of wedding",
    ],
    "other": [
        "random video footage",
        "unclear wedding video scene",
    ],
}

PROXY_DIR_NAMES = {
    "proxy", "proxies", "proxy media", "proxy_media", "adobe premiere pro video previews",
    "premiere pro video previews", "encoded files", "encoded_files"
}
PROXY_NAME_TOKENS = ["_proxy", "-proxy", " proxy.", "_proxy.", "-proxy.", "proxy_"]


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
        alpha = 0.12 + (0.76 * i / max(1, frame_samples - 1))
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


def l2norm(torch, x):
    return x / x.norm(dim=-1, keepdim=True).clamp(min=1e-12)


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

        pixel_values = inputs["pixel_values"]
        out = model.vision_model(pixel_values=pixel_values)
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


def classify_images(torch, model, processor, device, text_tags, text_feats, images) -> dict[str, Any]:
    if not images:
        return {"scene_tag": "other", "confidence": 0, "top_tags": "other:0", "frame_count": 0}
    image_feats = get_image_feats(torch, model, processor, device, images)
    logits = (image_feats @ text_feats.T) * 100.0
    tag_scores = {t: [] for t in PROMPTS.keys()}

    for i in range(logits.shape[0]):
        row = logits[i].detach().cpu().tolist()
        probs = softmax(row)
        per_tag = {t: 0.0 for t in PROMPTS.keys()}
        for j, prob in enumerate(probs):
            tag = text_tags[j]
            if prob > per_tag[tag]:
                per_tag[tag] = float(prob)
        for tag, sc in per_tag.items():
            tag_scores[tag].append(sc)

    agg = {}
    for tag, vals in tag_scores.items():
        vals = sorted(vals, reverse=True)
        top = vals[:max(1, min(3, len(vals)))]
        agg[tag] = sum(top) / len(top)

    sorted_tags = sorted(agg.items(), key=lambda x: x[1], reverse=True)
    best, best_score = sorted_tags[0]
    second, second_score = sorted_tags[1] if len(sorted_tags) > 1 else ("other", 0)
    confidence = max(0.0, min(1.0, best_score - second_score + best_score))
    top_tags = ";".join([f"{k}:{v:.4f}" for k, v in sorted_tags[:5]])
    return {
        "scene_tag": best,
        "confidence": round(confidence, 4),
        "top_tags": top_tags,
        "frame_count": len(images),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="119C Visual AI original source only, CLIP output compatibility fix.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--frame-samples", type=int, default=8)
    p.add_argument("--model", default="openai/clip-vit-base-patch32")
    p.add_argument("--max-files", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "visual_ai_original_clipfix_119c")

    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "visual_ai_119c_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    originals, proxies = list_original_files(source)
    if a.max_files and a.max_files > 0:
        originals = originals[:a.max_files]

    if not originals:
        res = {"ok": False, "error": "NO_ORIGINAL_VIDEO_FOUND", "source": str(source), "proxy_found_count": len(proxies)}
        write_json(out / "visual_ai_119c_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    try:
        torch, model, processor, device = load_clip(a.model)
        _, text_tags, text_feats = build_text_bank(torch, model, processor, device)
    except Exception as e:
        res = {
            "ok": False,
            "error": "VISUAL_AI_MODEL_NOT_READY",
            "message": repr(e),
            "install": "python -m pip install -U torch torchvision transformers pillow opencv-python",
        }
        write_json(out / "visual_ai_119c_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    items = []
    total = len(originals)
    for i, f in enumerate(originals, start=1):
        if i == 1 or i % 10 == 0 or i == total:
            print(f"[119C] visual AI original {i}/{total}: {f.name}", flush=True)

        if f.suffix.lower() == ".braw":
            item: dict[str, Any] = {
                "filename": f.name,
                "file": str(f),
                "scene_tag": "other",
                "confidence": 0,
                "top_tags": "braw_not_supported_by_cv2",
                "frame_count": 0,
                "ai_reason": "braw_not_decoded_original_kept",
            }
        else:
            imgs = sample_frames(f, a.frame_samples)
            cls = classify_images(torch, model, processor, device, text_tags, text_feats, imgs)
            item = {
                "filename": f.name,
                "file": str(f),
                **cls,
                "ai_reason": "clip_zero_shot_visual_original_only_119c",
            }

        item["_source_order"] = i - 1
        item["media_duration_sec"] = media_duration(f)
        item["is_proxy"] = False
        items.append(item)

    counts = {t: sum(1 for x in items if x.get("scene_tag") == t) for t in PROMPTS.keys()}
    data = {
        "ok": True,
        "module": "119C_visual_ai_original_clipfix",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "model": a.model,
        "device": device,
        "source": str(source),
        "file_count": len(items),
        "skipped_proxy_count": len(proxies),
        "scene_counts": counts,
        "items": items,
    }

    write_json(project / "stt_visual_ai_scene_tags_v1.json", data)
    write_json(project / "stt_visual_ai_scene_tags_original_clipfix_v1.json", data)
    write_json(out / "stt_visual_ai_scene_tags_original_clipfix_v1.json", data)
    write_csv(out / "VISUAL_AI_ORIGINAL_CLIPFIX_119C.csv", items, [
        "filename", "scene_tag", "confidence", "top_tags", "frame_count", "ai_reason", "media_duration_sec", "is_proxy", "file"
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
        "fix": "119C_visual_ai_original_clipfix",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
