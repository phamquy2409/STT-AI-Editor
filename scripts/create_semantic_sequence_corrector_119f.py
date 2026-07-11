from __future__ import annotations
import argparse, json, shutil
from datetime import datetime
from pathlib import Path
from semantic_sequence_common import *

PEOPLE_TAGS = ["cdcr_portrait", "getting_ready", "first_look", "family_photo", "family_emotion", "reception_stage", "wedding_game", "party", "vow"]
DARK_LATE_TAGS = ["wedding_game", "party", "reception_stage", "ending"]
FAMILY_TAGS = ["family_photo", "family_emotion"]
CEREMONY_TAGS = ["ceremony_giatien", "church_ceremony", "vow", "ruoc_dau"]

def maybe_close(a: float, b: float, ratio: float = 0.72, abs_min: float = 0.035) -> bool:
    return a >= abs_min and a >= b * ratio

def choose_people_tag(scores: dict[str, float], fallback: str) -> tuple[str, str]:
    t, s = best_of(scores, PEOPLE_TAGS)
    if s >= 0.038:
        return t, f"people_tag_score_{t}_{s:.4f}"
    return fallback, "no_people_score"

def correct_one(row: dict, pos: float) -> tuple[str, str]:
    old = str(row.get("scene_tag") or "other")
    scores = parse_top_tags(str(row.get("top_tags") or ""))
    conf = fnum(row.get("confidence"), 0)
    margin = fnum(row.get("margin"), 0)
    top_tag, top_score = best_of(scores, list(scores.keys()) or ["other"])

    decor_s = score(scores, "decor")
    cdcr_s = score(scores, "cdcr_portrait")
    gr_s = score(scores, "getting_ready")
    first_s = score(scores, "first_look")
    game_s = score(scores, "wedding_game")
    party_s = score(scores, "party")
    stage_s = score(scores, "reception_stage")
    fam_photo_s = score(scores, "family_photo")
    fam_emotion_s = score(scores, "family_emotion")
    vow_s = score(scores, "vow")
    ruoc_s = score(scores, "ruoc_dau")
    church_s = score(scores, "church_ceremony")
    giatien_s = score(scores, "ceremony_giatien")

    # 1) Decor cannot contain clear people/couple/stage/game.
    if old == "decor":
        people_t, people_s = best_of(scores, PEOPLE_TAGS)
        if maybe_close(people_s, decor_s, ratio=0.60, abs_min=0.038):
            if people_t == "first_look" and pos < 0.55:
                return "first_look", "decor_to_first_look_people_score"
            if people_t in {"cdcr_portrait", "getting_ready"} and pos < 0.58:
                return people_t, "decor_to_cdcr_or_getting_ready_people_score"
            if people_t in {"wedding_game", "party", "reception_stage"} and pos > 0.42:
                return people_t, "decor_to_reception_or_game_late"
            if people_t in {"family_photo", "family_emotion"}:
                return people_t, "decor_to_family_people_score"

    # 2) Rước dâu must be early/mid outdoor/procession; late family/game is not rước dâu.
    if old == "ruoc_dau":
        alt_t, alt_s = best_of(scores, ["family_photo", "family_emotion", "wedding_game", "party", "reception_stage", "cdcr_portrait"])
        if pos > 0.62:
            if alt_s >= 0.030:
                return alt_t, "late_ruoc_dau_to_actual_context"
            return "other", "late_ruoc_dau_uncertain"
        if alt_t in {"family_photo", "family_emotion"} and maybe_close(alt_s, ruoc_s, ratio=0.55, abs_min=0.030):
            return alt_t, "ruoc_dau_to_family_photo_close_score"
        if alt_t in {"wedding_game", "party", "reception_stage"} and maybe_close(alt_s, ruoc_s, ratio=0.55, abs_min=0.030):
            return alt_t, "ruoc_dau_to_reception_game_close_score"

    # 3) Vow is usually ceremony/daytime. Late night/game/party should not be vow.
    if old == "vow":
        late_t, late_s = best_of(scores, DARK_LATE_TAGS)
        people_t, people_s = best_of(scores, ["first_look", "cdcr_portrait", "family_photo", "family_emotion"])
        if pos > 0.68 and late_s >= 0.030:
            return late_t, "late_vow_to_game_party_stage"
        if people_s >= 0.040 and people_s >= vow_s * 0.70:
            if people_t == "first_look" and pos < 0.55:
                return "first_look", "vow_to_first_look_close_score"
            return people_t, "vow_to_people_moment_close_score"

    # 4) First look is not stage/late program.
    if old == "first_look" and pos > 0.58:
        alt_t, alt_s = best_of(scores, ["cdcr_portrait", "reception_stage", "family_photo", "wedding_game", "party"])
        if alt_s >= 0.030:
            return alt_t, "late_first_look_to_context"

    # 5) CDCR portrait on stage should become reception_stage if stage/game is close and late.
    if old == "cdcr_portrait":
        alt_t, alt_s = best_of(scores, ["reception_stage", "wedding_game", "family_photo"])
        if pos > 0.52 and maybe_close(alt_s, cdcr_s, ratio=0.55, abs_min=0.030):
            return alt_t, "late_cdcr_stage_or_family_context"

    # 6) Other can be promoted if CLIP top tags show meaningful wedding scene.
    if old == "other":
        promote_t, promote_s = best_of(scores, [
            "getting_ready", "first_look", "cdcr_portrait", "family_photo", "family_emotion",
            "reception_stage", "wedding_game", "party", "decor", "detail_beauty"
        ])
        if promote_s >= 0.045:
            if promote_t == "first_look" and pos > 0.58:
                return "cdcr_portrait", "other_firstlook_late_to_cdcr"
            return promote_t, f"other_promoted_{promote_t}"

    # 7) Getting ready should not appear near ending / late program.
    if old == "getting_ready" and pos > 0.62:
        alt_t, alt_s = best_of(scores, ["cdcr_portrait", "family_photo", "family_emotion", "wedding_game", "reception_stage", "party"])
        if alt_s >= 0.030:
            return alt_t, "late_getting_ready_to_context"
        return "other", "late_getting_ready_to_other"

    return old, "keep"

def promote_firstlook(items: list[dict]) -> list[dict]:
    # First look is usually earliest strong couple-only moment after getting ready, before ceremony/reception.
    existing = [x for x in items if x.get("scene_tag") == "first_look"]
    if existing:
        return items

    candidates = []
    n = max(1, len(items))
    for i, r in enumerate(items):
        pos = i / n
        if pos > 0.58:
            continue
        scores = parse_top_tags(str(r.get("top_tags") or ""))
        first_s = score(scores, "first_look")
        cdcr_s = score(scores, "cdcr_portrait")
        gr_s = score(scores, "getting_ready")
        tag = str(r.get("scene_tag") or "")
        if tag in {"cdcr_portrait", "getting_ready", "other", "decor"}:
            val = max(first_s * 1.5, cdcr_s, gr_s * 0.55)
            if val >= 0.038:
                candidates.append((pos, -val, i, r))
    if candidates:
        candidates.sort()
        _, _, idx, _ = candidates[0]
        items[idx]["semantic_before_firstlook_promote"] = items[idx].get("scene_tag", "")
        items[idx]["scene_tag"] = "first_look"
        items[idx]["sequence_fix_reason"] = "auto_promote_earliest_couple_candidate_to_first_look"
    return items

def main() -> None:
    p = argparse.ArgumentParser(description="119F Semantic sequence corrector after 119E.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--json", default="", help="default project/stt_visual_ai_scene_tags_v1.json")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    src_json = Path(a.json) if a.json else project / "stt_visual_ai_scene_tags_v1.json"
    out = outdir(project, "semantic_sequence_corrector_119f")

    data = read_json(src_json)
    items = list(data.get("items") or [])
    if not items:
        res = {"ok": False, "error": "NO_ITEMS", "json": str(src_json), "message": "Run 119E first."}
        write_json(out / "semantic_sequence_corrector_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    backup = project / f"stt_visual_ai_scene_tags_v1_BACKUP_before_119f_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        shutil.copy2(src_json, backup)
    except Exception:
        pass

    before_counts = count_tags(items)
    changes = []
    n = max(1, len(items))
    corrected = []
    for i, r in enumerate(items):
        row = dict(r)
        old = str(row.get("scene_tag") or "other")
        new, reason = correct_one(row, i / n)
        row["scene_tag_before_119f"] = old
        row["sequence_fix_reason"] = reason
        row["source_order_pos"] = round(i / n, 4)
        row["scene_tag"] = new
        corrected.append(row)
        if new != old:
            changes.append({
                "filename": row.get("filename", ""),
                "before": old,
                "after": new,
                "reason": reason,
                "source_order_pos": row["source_order_pos"],
                "confidence": row.get("confidence", ""),
                "margin": row.get("margin", ""),
                "top_tags": row.get("top_tags", ""),
                "file": row.get("file", ""),
            })

    corrected = promote_firstlook(corrected)
    # Account firstlook promotion if not counted in changes.
    for r in corrected:
        if r.get("semantic_before_firstlook_promote"):
            changes.append({
                "filename": r.get("filename", ""),
                "before": r.get("semantic_before_firstlook_promote", ""),
                "after": r.get("scene_tag", ""),
                "reason": r.get("sequence_fix_reason", ""),
                "source_order_pos": r.get("source_order_pos", ""),
                "confidence": r.get("confidence", ""),
                "margin": r.get("margin", ""),
                "top_tags": r.get("top_tags", ""),
                "file": r.get("file", ""),
            })

    after_counts = count_tags(corrected)
    data["items"] = corrected
    data["scene_counts_before_119f"] = before_counts
    data["scene_counts"] = after_counts
    data["module"] = "119F_semantic_sequence_corrected"
    data["sequence_corrector"] = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "backup_json": str(backup),
        "changed_count": len(changes),
    }

    write_json(project / "stt_visual_ai_scene_tags_v1.json", data)
    write_json(project / "stt_wedding_semantic_scene_tags_v3_sequence_corrected.json", data)
    write_json(out / "stt_wedding_semantic_scene_tags_v3_sequence_corrected.json", data)
    write_csv(out / "SEMANTIC_SEQUENCE_CORRECTIONS_119F.csv", changes, [
        "filename", "before", "after", "reason", "source_order_pos", "confidence", "margin", "top_tags", "file"
    ])
    write_csv(out / "SEMANTIC_SEQUENCE_COUNTS_119F.csv", [
        {"scene_tag": tag, "before": before_counts.get(tag, 0), "after": after_counts.get(tag, 0)}
        for tag in SCENE_TAGS
    ], ["scene_tag", "before", "after"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "input_json": str(src_json),
        "backup_json": str(backup),
        "file_count": len(corrected),
        "changed_count": len(changes),
        "scene_counts_before": before_counts,
        "scene_counts_after": after_counts,
        "fix": "119F_semantic_sequence_corrector",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
