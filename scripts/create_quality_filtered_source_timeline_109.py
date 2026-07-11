from quality_music_common import *


def reject_by_reason(q: dict[str, Any], reject_shaky: bool, reject_blur: bool, reject_empty: bool) -> bool:
    rr = str(q.get("reject_reasons") or "")
    if reject_shaky and any(x in rr for x in ["whip_pan_or_shaky", "unstable_motion"]):
        return True
    if reject_blur and "blur" in rr:
        return True
    if reject_empty and any(x in rr for x in ["empty_or_low_detail", "too_dark", "too_bright"]):
        return True
    return False


def main() -> None:
    p = argparse.ArgumentParser(description="109 Quality Filter Source Timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--min-score", type=float, default=55)
    p.add_argument("--keep-review", action="store_true")
    p.add_argument("--reject-shaky", action="store_true")
    p.add_argument("--reject-blur", action="store_true")
    p.add_argument("--reject-empty", action="store_true")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "quality_filtered_source_timeline_109")

    # IMPORTANT: do not use existing quality-filtered file as input, use original story/rhythm source.
    base = {}
    for name in ["stt_profile_story_timeline_v1.json", "stt_learned_inout_timeline_v1.json", "stt_profile_rhythm_timeline_v1.json"]:
        d = read_json(project / name)
        if d and d.get("items"):
            base = d
            break

    if not base:
        res = {"ok": False, "error": "NO_BASE_TIMELINE", "message": "Run 096 first."}
        write_json(out / "quality_filter_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    by_path, by_name = quality_lookup(project)
    items_in = list(base.get("items") or [])
    kept = []
    rejected = []

    for it in items_in:
        q = get_quality_for_item(it, by_path, by_name)
        score = fnum(q.get("quality_score"), 0)
        usable = bool(q.get("usable", False))
        quality_class = str(q.get("quality_class") or "")
        reject = False
        reason = []

        if score < a.min_score:
            reject = True
            reason.append("score_below_min")
        if not usable and not (a.keep_review and quality_class.startswith("review")):
            reject = True
            reason.append("not_usable")
        if reject_by_reason(q, a.reject_shaky, a.reject_blur, a.reject_empty):
            reject = True
            reason.append("reject_reason_gate")

        row = dict(it)
        row.update({
            "quality_score": score,
            "quality_class": quality_class,
            "quality_usable": usable,
            "quality_reject_reasons": q.get("reject_reasons", ""),
            "motion_class": q.get("motion_class", ""),
            "media_duration_sec": q.get("duration_sec", ""),
        })

        if reject:
            row["filter_status"] = "rejected"
            row["filter_reason"] = ",".join(reason)
            rejected.append(row)
        else:
            row["filter_status"] = "kept"
            row["filter_reason"] = ""
            kept.append(row)

    # If too strict and kept too few, add best review/usable-by-score items back.
    min_keep = min(120, max(40, int(len(items_in) * 0.35)))
    if len(kept) < min_keep:
        pool = sorted(rejected, key=lambda x: fnum(x.get("quality_score"), 0), reverse=True)
        need = min_keep - len(kept)
        rescue = pool[:need]
        for r in rescue:
            r["filter_status"] = "kept_rescue"
            r["filter_reason"] = "rescued_best_available"
        kept.extend(rescue)
        rejected = pool[need:]

    for i, it in enumerate(kept, start=1):
        it["index"] = i

    data = {
        "ok": True,
        "module": "109_quality_filtered_source_timeline",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "base_timeline_count": len(items_in),
        "kept_count": len(kept),
        "rejected_count": len(rejected),
        "min_score": a.min_score,
        "items": kept,
        "rejected_items": rejected[:300],
    }
    write_json(project / "stt_quality_filtered_source_timeline_v1.json", data)
    write_json(out / "stt_quality_filtered_source_timeline_v1.json", data)
    write_csv(out / "QUALITY_FILTERED_KEPT.csv", kept, [
        "index", "target_section", "filename", "quality_score", "quality_class", "quality_reject_reasons",
        "motion_class", "media_duration_sec", "filter_status", "filter_reason", "file"
    ])
    write_csv(out / "QUALITY_FILTERED_REJECTED.csv", rejected, [
        "index", "target_section", "filename", "quality_score", "quality_class", "quality_reject_reasons",
        "motion_class", "media_duration_sec", "filter_status", "filter_reason", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "base_timeline_count": len(items_in),
        "kept_count": len(kept),
        "rejected_count": len(rejected),
        "min_score": a.min_score,
        "fix": "109_quality_filtered_source_timeline",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
