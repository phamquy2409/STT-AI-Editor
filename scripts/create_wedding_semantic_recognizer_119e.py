from __future__ import annotations
import argparse, json
from pathlib import Path
from wedding_semantic_v3_common import *

PROMPTS = {
    "decor": [
        "wedding venue decoration without people",
        "wedding ceremony flowers arch decoration",
        "wedding reception table decoration no people",
        "cinematic wide shot of wedding decor",
        "banquet hall wedding decoration",
        "wedding stage decoration empty",
    ],
    "detail_beauty": [
        "close up wedding rings",
        "bridal dress hanging",
        "bridal shoes close up",
        "wedding bouquet flowers close up",
        "wedding invitation card detail",
        "cinematic wedding details close up",
    ],
    "getting_ready": [
        "bride getting makeup",
        "bride getting ready before wedding",
        "groom getting ready suit",
        "bride putting on dress",
        "makeup artist applying makeup to bride",
        "hair styling bride preparation",
    ],
    "first_look": [
        "bride and groom first look moment",
        "groom seeing bride for first time",
        "emotional first look wedding couple",
        "bride walks to groom first look",
        "couple holding hands first look",
    ],
    "cdcr_portrait": [
        "bride and groom portrait",
        "wedding couple standing together",
        "bride and groom walking together",
        "romantic newlywed couple portrait",
        "bride and groom posing for photo",
        "close up bride and groom",
    ],
    "ceremony_giatien": [
        "traditional Vietnamese wedding ceremony inside house",
        "bride and groom at family altar",
        "incense altar traditional wedding ceremony",
        "bride and groom receiving gifts from family",
        "wedding ceremony with parents relatives inside home",
    ],
    "church_ceremony": [
        "bride and groom in church wedding ceremony",
        "wedding ceremony inside church",
        "priest officiating wedding ceremony",
        "bride and groom at church altar",
        "church aisle wedding ceremony",
        "Catholic wedding ceremony in church",
    ],
    "vow": [
        "bride reading wedding vow",
        "groom reading wedding vow",
        "bride and groom holding microphone during vow",
        "wedding vow speech emotional",
        "couple speaking vows at ceremony",
    ],
    "ruoc_dau": [
        "Vietnamese wedding procession carrying red gift trays",
        "outdoor wedding procession group walking",
        "groom family arriving with wedding gift trays",
        "traditional wedding procession entering bride house",
        "people carrying red trays Vietnamese wedding",
    ],
    "reception_stage": [
        "wedding reception stage with bride and groom",
        "bride and groom on stage with LED screen",
        "wedding speech on stage",
        "wedding cake champagne tower on stage",
        "banquet hall wedding stage lights",
    ],
    "wedding_game": [
        "wedding reception game on stage at night",
        "people playing party game at wedding reception",
        "guests playing game with bride and groom",
        "night wedding game activity with microphone",
        "fun group activity at wedding reception",
    ],
    "family_photo": [
        "family group photo posing at wedding",
        "large family formal photo with bride and groom",
        "relatives posing for wedding group photo",
        "parents and family standing for group portrait",
        "group photo on wedding stage",
    ],
    "family_emotion": [
        "parents hugging bride and groom",
        "emotional family moment at wedding",
        "bride and groom with parents emotional",
        "family relatives giving blessing wedding",
        "mother father emotional wedding moment",
    ],
    "guest_food": [
        "wedding guests eating dinner at tables",
        "people eating food at banquet table",
        "buffet food table at wedding",
        "plates of food on wedding table",
        "guests sitting and eating at reception",
    ],
    "party": [
        "people dancing at wedding party",
        "wedding dance floor colorful lights",
        "DJ party lights wedding reception",
        "guests dancing at night wedding",
        "bride and groom dancing party",
    ],
    "ending": [
        "emotional wedding ending",
        "bride and groom farewell",
        "couple walking away at end of wedding",
        "final romantic shot bride and groom",
        "wedding ending hug emotional",
    ],
    "other": [
        "unclear random wedding footage",
        "general people standing around",
        "camera test footage",
        "unimportant wedding footage",
    ],
}

STRICT_TAGS = {"ruoc_dau", "vow", "first_look", "ceremony_giatien", "church_ceremony", "guest_food"}
MIN_MARGIN = {
    "ruoc_dau": 0.030,
    "vow": 0.024,
    "first_look": 0.024,
    "ceremony_giatien": 0.022,
    "church_ceremony": 0.022,
    "guest_food": 0.020,
}
MIN_CONF = {
    "ruoc_dau": 0.070,
    "vow": 0.058,
    "first_look": 0.058,
    "ceremony_giatien": 0.058,
    "church_ceremony": 0.058,
    "guest_food": 0.055,
}

def build_text_bank(torch, model, processor, device):
    texts, tags = [], []
    for tag, prompts in PROMPTS.items():
        for p in prompts:
            texts.append("a photo of " + p)
            tags.append(tag)
    return texts, tags, get_text_feats(torch, model, processor, device, texts)

def classify_images(torch, model, processor, device, text_tags, text_feats, images) -> dict:
    if not images:
        return {"scene_tag": "other", "confidence": 0, "margin": 0, "top_tags": "other:0", "frame_count": 0}

    img_feats = get_image_feats(torch, model, processor, device, images)
    logits = (img_feats @ text_feats.T) * 100.0
    tag_scores = {t: [] for t in PROMPTS.keys()}

    for i in range(logits.shape[0]):
        probs = softmax(logits[i].detach().cpu().tolist())
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
    margin = best_score - second_score

    if best in STRICT_TAGS and (best_score < MIN_CONF.get(best, 0.06) or margin < MIN_MARGIN.get(best, 0.02)):
        replacement = None
        for tag, score in sorted_tags[1:7]:
            if tag in {"decor", "detail_beauty", "getting_ready", "cdcr_portrait", "wedding_game", "family_photo", "reception_stage", "family_emotion", "party"} and score > 0.040:
                replacement = (tag, score)
                break
        if replacement:
            best, best_score = replacement
        else:
            best = "other"

    top_tags = ";".join([f"{k}:{v:.4f}" for k, v in sorted_tags[:7]])
    return {
        "scene_tag": best,
        "confidence": round(max(0.0, min(1.0, best_score)), 4),
        "margin": round(margin, 4),
        "top_tags": top_tags,
        "frame_count": len(images),
    }

def main() -> None:
    p = argparse.ArgumentParser(description="119E Wedding semantic V3 recognizer with church ceremony.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--frame-samples", type=int, default=5)
    p.add_argument("--model", default="openai/clip-vit-base-patch32")
    p.add_argument("--max-files", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "wedding_semantic_v3_church_119e")
    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "semantic_v3_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    originals, proxies = list_original_files(source)
    if a.max_files and a.max_files > 0:
        originals = originals[:a.max_files]

    try:
        torch, model, processor, device = load_clip(a.model)
        _, text_tags, text_feats = build_text_bank(torch, model, processor, device)
    except Exception as e:
        res = {"ok": False, "error": "VISUAL_AI_MODEL_NOT_READY", "message": repr(e)}
        write_json(out / "semantic_v3_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    items = []
    total = len(originals)
    for i, f in enumerate(originals, start=1):
        if i == 1 or i % 10 == 0 or i == total:
            print(f"[119E] semantic V3 church {i}/{total}: {f.name}", flush=True)
        if f.suffix.lower() == ".braw":
            item = {
                "filename": f.name, "file": str(f), "scene_tag": "other",
                "confidence": 0, "margin": 0, "top_tags": "braw_not_supported_by_cv2",
                "frame_count": 0, "ai_reason": "braw_not_decoded_original_kept",
            }
        else:
            imgs = sample_frames(f, a.frame_samples)
            cls = classify_images(torch, model, processor, device, text_tags, text_feats, imgs)
            item = {"filename": f.name, "file": str(f), **cls, "ai_reason": "wedding_semantic_v3_church_clip"}

        item["_source_order"] = i - 1
        item["media_duration_sec"] = media_duration(f)
        item["is_proxy"] = False
        items.append(item)

    counts = {t: sum(1 for x in items if x.get("scene_tag") == t) for t in SCENE_TAGS}
    data = {
        "ok": True, "module": "119E_wedding_semantic_v3_church",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "model": a.model, "device": device, "source": str(source),
        "file_count": len(items), "skipped_proxy_count": len(proxies),
        "scene_counts": counts, "items": items,
    }

    write_json(project / "stt_visual_ai_scene_tags_v1.json", data)
    write_json(project / "stt_wedding_semantic_scene_tags_v3.json", data)
    write_json(out / "stt_wedding_semantic_scene_tags_v3.json", data)
    write_csv(out / "WEDDING_SEMANTIC_V3_TAGS.csv", items, [
        "filename", "scene_tag", "confidence", "margin", "top_tags", "frame_count", "ai_reason", "media_duration_sec", "is_proxy", "file"
    ])
    write_csv(out / "SKIPPED_PROXY_FILES.csv", [{"filename": p.name, "file": str(p)} for p in proxies], ["filename", "file"])

    print(json.dumps({
        "ok": True, "report_dir": str(out), "model": a.model, "device": device,
        "file_count": len(items), "skipped_proxy_count": len(proxies),
        "scene_counts": counts, "fix": "119E_wedding_semantic_v3_church",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
