from __future__ import annotations
import argparse, json
from pathlib import Path
from precision_v4_common import *

PROMPTS = {
    "decor": [
        "empty wedding venue decoration with no people",
        "empty wedding reception hall decoration, no bride, no groom, no guests",
        "wedding ceremony arch flowers with no people",
        "empty wedding stage decoration before ceremony",
        "wide shot of wedding decor and flowers without people",
        "banquet table decoration no guests eating",
    ],
    "detail_beauty": [
        "close up wedding rings",
        "close up bridal dress hanging",
        "close up bridal shoes",
        "close up wedding bouquet flowers",
        "close up wedding invitation flat lay",
        "close up groom cufflinks",
        "close up groom tie and suit detail",
        "close up groom watch wedding detail",
        "close up groom shoes wedding detail",
        "close up perfume and accessories wedding detail",
        "cinematic wedding detail shot no full faces",
    ],
    "getting_ready": [
        "bride getting makeup",
        "bride getting ready before ceremony",
        "groom getting ready putting on suit",
        "groom adjusting tie before wedding",
        "bride putting on wedding dress",
        "makeup artist applying makeup to bride",
    ],
    "first_look": [
        "bride and groom first look, couple alone seeing each other first time",
        "groom reacts seeing bride for first time",
        "bride walks to groom for private first look",
        "couple alone emotional first look moment",
    ],
    "cdcr_portrait": [
        "bride and groom portrait only",
        "wedding couple standing together",
        "bride and groom walking together",
        "romantic newlywed couple portrait",
        "bride and groom posing for photo without stage",
        "couple session portrait wedding day",
    ],
    "ceremony_giatien": [
        "Vietnamese traditional wedding ceremony at family altar",
        "bride and groom at ancestor altar inside house",
        "incense altar traditional Vietnamese wedding ceremony",
        "family giving gifts during Vietnamese wedding ceremony",
    ],
    "church_ceremony": [
        "bride and groom at church altar",
        "wedding ceremony inside church with priest",
        "Catholic church wedding ceremony",
        "church aisle wedding ceremony",
    ],
    "vow": [
        "bride reading wedding vows with microphone during ceremony",
        "groom reading wedding vows with microphone during ceremony",
        "couple speaking vows to each other in ceremony",
        "bride and groom holding vow cards",
    ],
    "ruoc_dau": [
        "Vietnamese wedding procession carrying red gift trays outdoors",
        "groom family carrying traditional red trays to bride house",
        "traditional Vietnamese engagement procession with red boxes",
    ],
    "reception_stage": [
        "bride and groom on wedding reception stage",
        "groom walking onto wedding reception stage",
        "bride walking onto wedding reception stage",
        "wedding reception stage with LED screen and lights",
        "wedding speech on stage with microphone",
        "wedding cake champagne tower on stage",
        "couple standing on banquet stage at night",
    ],
    "wedding_game": [
        "wedding reception game on stage at night",
        "guests playing funny game at wedding reception",
        "people playing group game with microphone at wedding",
        "night wedding game activity on stage",
    ],
    "family_photo": [
        "formal family group photo at wedding",
        "large group photo with bride and groom and relatives",
        "parents and relatives posing for wedding photo",
        "family standing together for posed group photo",
    ],
    "family_emotion": [
        "parents hugging bride or groom emotionally",
        "emotional family moment at wedding",
        "bride and groom with parents emotional",
        "parents blessing bride and groom",
    ],
    "guest_food": [
        "wedding guests eating dinner at tables",
        "people eating food at banquet table",
        "plates of food on wedding reception table",
        "guests sitting and eating at reception",
    ],
    "party": [
        "wedding dance floor with colorful lights",
        "people dancing at wedding party",
        "DJ lights at wedding reception party",
        "guests dancing at night wedding party",
    ],
    "ending": [
        "final romantic shot of bride and groom together",
        "bride and groom together for wedding ending",
        "couple walking away together at end of wedding",
        "beautiful bride and groom couple shot for ending",
        "romantic two person couple shot at wedding end",
    ],
    "other": [
        "unclear random wedding footage",
        "general people standing around not important",
        "unimportant wedding footage",
        "camera test footage",
    ],
}

STRICT_TAGS = {
    "decor": (0.038, 0.004),
    "ending": (0.040, 0.006),
    "ruoc_dau": (0.050, 0.015),
    "vow": (0.044, 0.012),
    "first_look": (0.044, 0.010),
    "ceremony_giatien": (0.044, 0.012),
    "church_ceremony": (0.044, 0.012),
    "guest_food": (0.044, 0.012),
}

PEOPLE_TAGS = ["cdcr_portrait", "getting_ready", "first_look", "family_photo", "family_emotion", "reception_stage", "wedding_game", "party", "vow"]
DETAIL_RELATED = ["detail_beauty", "getting_ready", "decor"]

def build_text_bank(torch, model, processor, device):
    texts, tags = [], []
    for tag, prompts in PROMPTS.items():
        for p in prompts:
            texts.append("a photo of " + p)
            tags.append(tag)
    return texts, tags, get_text_feats(torch, model, processor, device, texts)

def aggregate_scores(torch, model, processor, device, text_tags, text_feats, images):
    if not images:
        return {}, []
    img_feats = get_image_feats(torch, model, processor, device, images)
    logits = (img_feats @ text_feats.T) * 100.0
    tag_frame_scores = {t: [] for t in PROMPTS.keys()}
    frame_top = []
    for i in range(logits.shape[0]):
        probs = softmax(logits[i].detach().cpu().tolist())
        per_tag = {t: 0.0 for t in PROMPTS.keys()}
        for j, prob in enumerate(probs):
            tag = text_tags[j]
            if prob > per_tag[tag]:
                per_tag[tag] = float(prob)
        frame_top.append(";".join([f"{k}:{v:.4f}" for k, v in sorted(per_tag.items(), key=lambda x: x[1], reverse=True)[:6]]))
        for tag, sc in per_tag.items():
            tag_frame_scores[tag].append(sc)
    agg = {}
    for tag, vals in tag_frame_scores.items():
        vals_sorted = sorted(vals, reverse=True)
        top3 = vals_sorted[:max(1, min(3, len(vals_sorted)))]
        avg = sum(vals) / max(1, len(vals))
        topavg = sum(top3) / max(1, len(top3))
        vote = sum(1 for v in vals if v >= max(0.030, topavg * 0.62)) / max(1, len(vals))
        agg[tag] = (topavg * 0.72) + (avg * 0.18) + (vote * 0.10)
    return agg, frame_top

def refine(best: str, scores: dict[str, float], pos: float):
    sorted_tags = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_score = scores.get(best, 0.0)
    second_score = sorted_tags[1][1] if len(sorted_tags) > 1 else 0.0
    margin = best_score - second_score

    # Decor precision: if any people tag is close, it is not decor.
    if best == "decor":
        pt, ps = best_of(scores, PEOPLE_TAGS + ["guest_food"])
        dt = scores.get("detail_beauty", 0.0)
        if dt >= best_score * 0.70 and dt >= 0.030:
            return "detail_beauty", "decor_to_detail_beauty_close"
        if ps >= best_score * 0.58 and ps >= 0.030:
            return pt, "decor_rejected_people_or_guest"
        if pos > 0.55 and scores.get("reception_stage", 0) >= best_score * 0.50:
            return "reception_stage", "late_decor_to_stage"

    # Detail beauty: promote close detail over other/decor/getting_ready.
    if best in {"other", "decor", "getting_ready"}:
        ds = scores.get("detail_beauty", 0.0)
        if ds >= 0.034 and ds >= best_score * 0.62:
            return "detail_beauty", f"{best}_to_detail_beauty_groom_or_accessory"

    # Ending should be couple/two-person. Reject stage/game/party/single context.
    if best == "ending":
        couple_s = max(scores.get("ending", 0), scores.get("cdcr_portrait", 0), scores.get("first_look", 0))
        bad_t, bad_s = best_of(scores, ["reception_stage", "wedding_game", "party", "guest_food", "getting_ready", "family_photo"])
        if bad_s >= couple_s * 0.55 and bad_s >= 0.030:
            return bad_t, "ending_rejected_not_couple"
        if pos < 0.60 and scores.get("cdcr_portrait", 0) >= 0.030:
            return "cdcr_portrait", "early_ending_to_cdcr"

    # Vow should not be late game/party/stage.
    if best == "vow" and pos > 0.64:
        t, s = best_of(scores, ["wedding_game", "reception_stage", "party", "family_photo", "family_emotion"])
        if s >= 0.028:
            return t, "late_vow_demoted"

    # Groom/bride walking to stage is reception_stage, not cdcr/ending.
    if best in {"cdcr_portrait", "ending"} and pos > 0.50:
        ss = scores.get("reception_stage", 0.0)
        if ss >= best_score * 0.55 and ss >= 0.028:
            return "reception_stage", f"{best}_late_stage_context"

    # Ruoc dau must be early/mid and tray/procession-like.
    if best == "ruoc_dau" and pos > 0.58:
        t, s = best_of(scores, ["family_photo", "family_emotion", "wedding_game", "reception_stage", "party"])
        if s >= 0.028:
            return t, "late_ruoc_dau_demoted"

    # Strict rare tag fallback.
    if best in STRICT_TAGS:
        min_conf, min_margin = STRICT_TAGS[best]
        if best_score < min_conf or margin < min_margin:
            for tag, sc in sorted_tags[1:8]:
                if tag in {"detail_beauty", "getting_ready", "cdcr_portrait", "family_photo", "family_emotion", "reception_stage", "wedding_game", "party", "decor", "other"} and sc >= 0.030:
                    return tag, f"strict_demote_{best}_to_{tag}"

    return best, "keep"

def classify_clip(torch, model, processor, device, text_tags, text_feats, images, pos: float):
    if not images:
        return {"scene_tag": "other", "raw_scene_tag": "other", "confidence": 0, "margin": 0, "top_tags": "other:0", "frame_top_tags": "", "frame_count": 0, "semantic_reason": "no_frames"}
    scores, frame_top = aggregate_scores(torch, model, processor, device, text_tags, text_feats, images)
    sorted_tags = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    raw, raw_s = sorted_tags[0]
    second = sorted_tags[1][1] if len(sorted_tags) > 1 else 0.0
    final, reason = refine(raw, scores, pos)
    top_tags = ";".join([f"{k}:{v:.4f}" for k, v in sorted_tags[:9]])
    return {
        "scene_tag": final,
        "raw_scene_tag": raw,
        "confidence": round(float(scores.get(final, raw_s)), 4),
        "margin": round(float(raw_s - second), 4),
        "top_tags": top_tags,
        "frame_top_tags": " | ".join(frame_top),
        "frame_count": len(images),
        "semantic_reason": reason,
    }

def main() -> None:
    p = argparse.ArgumentParser(description="119H Precision semantic V4 recognizer.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--frame-samples", type=int, default=7)
    p.add_argument("--model", default="openai/clip-vit-large-patch14")
    p.add_argument("--max-files", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "precision_semantic_v4_119h")
    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "precision_semantic_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    originals, proxies = list_original_files(source)
    if a.max_files and a.max_files > 0:
        originals = originals[:a.max_files]

    try:
        torch, model, processor, device = load_clip(a.model)
        _, text_tags, text_feats = build_text_bank(torch, model, processor, device)
    except Exception as e:
        res = {"ok": False, "error": "PRECISION_VISUAL_AI_NOT_READY", "message": repr(e)}
        write_json(out / "precision_semantic_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    items = []
    total = len(originals)
    for i, f in enumerate(originals, start=1):
        if i == 1 or i % 10 == 0 or i == total:
            print(f"[119H] precision semantic V4 {i}/{total}: {f.name}", flush=True)
        if f.suffix.lower() == ".braw":
            item = {
                "filename": f.name, "file": str(f), "scene_tag": "other", "raw_scene_tag": "other",
                "confidence": 0, "margin": 0, "top_tags": "braw_not_supported_by_cv2",
                "frame_top_tags": "", "frame_count": 0, "semantic_reason": "braw_not_decoded",
                "ai_reason": "braw_not_decoded",
            }
        else:
            imgs = sample_frames(f, a.frame_samples)
            cls = classify_clip(torch, model, processor, device, text_tags, text_feats, imgs, (i - 1) / max(1, total))
            item = {"filename": f.name, "file": str(f), **cls, "ai_reason": "precision_semantic_v4_119h"}

        item["_source_order"] = i - 1
        item["source_order_pos"] = round((i - 1) / max(1, total), 4)
        item["media_duration_sec"] = media_duration(f)
        item["is_proxy"] = False
        items.append(item)

    counts = count_tags(items)
    raw_counts = {t: sum(1 for x in items if x.get("raw_scene_tag") == t) for t in SCENE_TAGS}
    data = {
        "ok": True, "module": "119H_precision_semantic_v4",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "model": a.model, "device": device, "source": str(source),
        "file_count": len(items), "skipped_proxy_count": len(proxies),
        "scene_counts": counts, "raw_scene_counts": raw_counts, "items": items,
    }
    write_json(project / "stt_visual_ai_scene_tags_v1.json", data)
    write_json(project / "stt_precision_semantic_scene_tags_v4.json", data)
    write_json(out / "stt_precision_semantic_scene_tags_v4.json", data)
    write_csv(out / "PRECISION_SEMANTIC_V4_TAGS.csv", items, [
        "filename", "scene_tag", "raw_scene_tag", "confidence", "margin", "semantic_reason",
        "top_tags", "frame_top_tags", "frame_count", "source_order_pos", "media_duration_sec", "is_proxy", "file"
    ])
    write_csv(out / "SKIPPED_PROXY_FILES.csv", [{"filename": p.name, "file": str(p)} for p in proxies], ["filename", "file"])

    print(json.dumps({
        "ok": True, "report_dir": str(out), "model": a.model, "device": device,
        "file_count": len(items), "skipped_proxy_count": len(proxies),
        "scene_counts": counts, "raw_scene_counts": raw_counts,
        "fix": "119H_precision_semantic_v4",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
