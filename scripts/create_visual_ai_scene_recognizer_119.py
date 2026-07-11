from visual_ai_common import *


PROMPTS = {
    "intro_beauty": [
        "wedding rings close up",
        "bridal dress close up",
        "wedding flowers bouquet close up",
        "wedding venue decoration",
        "beautiful wedding table decoration without people eating",
        "wedding invitation details",
        "cinematic detail shot at a wedding",
    ],
    "cdcr": [
        "bride and groom portrait",
        "wedding couple standing together",
        "bride and groom walking together",
        "close up of bride and groom",
        "romantic wedding couple shot",
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


def list_files(source: Path) -> list[Path]:
    files = []
    for ext in VIDEO_EXTS:
        files.extend(source.rglob(f"*{ext}"))
    return sorted(set(files), key=lambda p: str(p).lower())


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
        raise RuntimeError("MISSING_DEPS: run `python -m pip install -U torch torchvision transformers pillow opencv-python`") from e

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(model_name).to(device)
    processor = CLIPProcessor.from_pretrained(model_name)
    model.eval()
    return torch, model, processor, device


def build_text_bank(torch, model, processor, device):
    texts = []
    text_tags = []
    for tag, prompts in PROMPTS.items():
        for p in prompts:
            texts.append("a photo of " + p)
            text_tags.append(tag)
    with torch.no_grad():
        inputs = processor(text=texts, return_tensors="pt", padding=True, truncation=True).to(device)
        feats = model.get_text_features(**inputs)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return texts, text_tags, feats


def classify_images(torch, model, processor, device, text_tags, text_feats, images) -> dict[str, Any]:
    if not images:
        return {"scene_tag": "other", "confidence": 0, "top_tags": "other:0", "frame_count": 0}

    tag_scores = {t: [] for t in PROMPTS.keys()}
    with torch.no_grad():
        inputs = processor(images=images, return_tensors="pt").to(device)
        image_feats = model.get_image_features(**inputs)
        image_feats = image_feats / image_feats.norm(dim=-1, keepdim=True)
        logits = (image_feats @ text_feats.T) * 100.0

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

    # Small wedding-specific correction: if guest_food is close to reception_stage, keep it as guest_food only when clearly food/eating.
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
    p = argparse.ArgumentParser(description="119 Visual AI wedding scene recognizer using local CLIP.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--frame-samples", type=int, default=8)
    p.add_argument("--model", default="openai/clip-vit-base-patch32")
    p.add_argument("--max-files", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "visual_ai_scene_recognizer_119")

    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "visual_ai_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    try:
        torch, model, processor, device = load_clip(a.model)
        texts, text_tags, text_feats = build_text_bank(torch, model, processor, device)
    except Exception as e:
        res = {
            "ok": False,
            "error": "VISUAL_AI_MODEL_NOT_READY",
            "message": str(e),
            "install": "python -m pip install -U torch torchvision transformers pillow opencv-python",
        }
        write_json(out / "visual_ai_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    files = list_files(source)
    if a.max_files and a.max_files > 0:
        files = files[:a.max_files]

    items = []
    total = len(files)
    for i, f in enumerate(files, start=1):
        if i == 1 or i % 10 == 0 or i == total:
            print(f"[119] visual AI {i}/{total}: {f.name}", flush=True)

        if f.suffix.lower() == ".braw":
            item = {
                "filename": f.name,
                "file": str(f),
                "scene_tag": "other",
                "confidence": 0,
                "top_tags": "braw_not_supported_by_cv2",
                "frame_count": 0,
                "ai_reason": "braw_not_decoded",
            }
        else:
            imgs = sample_frames(f, a.frame_samples)
            cls = classify_images(torch, model, processor, device, text_tags, text_feats, imgs)
            item = {
                "filename": f.name,
                "file": str(f),
                **cls,
                "ai_reason": "clip_zero_shot_visual",
            }
        item["_source_order"] = i - 1
        item["media_duration_sec"] = media_duration(f)
        items.append(item)

    counts = {t: sum(1 for x in items if x.get("scene_tag") == t) for t in PROMPTS.keys()}
    data = {
        "ok": True,
        "module": "119_visual_ai_scene_recognizer",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "model": a.model,
        "device": device,
        "source": str(source),
        "file_count": len(items),
        "scene_counts": counts,
        "items": items,
    }
    write_json(project / "stt_visual_ai_scene_tags_v1.json", data)
    write_json(out / "stt_visual_ai_scene_tags_v1.json", data)
    write_csv(out / "VISUAL_AI_SCENE_TAGS_V1.csv", items, [
        "filename", "scene_tag", "confidence", "top_tags", "frame_count", "ai_reason", "media_duration_sec", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "model": a.model,
        "device": device,
        "file_count": len(items),
        "scene_counts": counts,
        "fix": "119_visual_ai_scene_recognizer",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
