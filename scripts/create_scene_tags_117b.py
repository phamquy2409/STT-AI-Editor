from storybeat_common import *


def beauty_lookup(project: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    d = read_json(project / "stt_scene_beauty_v1.json")
    by_path, by_name = {}, {}
    for row in d.get("items", []):
        p = norm(row.get("file", ""))
        n = str(row.get("filename") or "").lower()
        if p:
            by_path[p] = row
        if n:
            by_name.setdefault(n, row)
    return by_path, by_name


def guess_tag(path: Path, order_pos: float) -> tuple[str, str]:
    s = str(path).replace("\\", "/").lower()

    # Strong negative / guest-food tags.
    if any(k in s for k in ["food", "buffet", "eat", "eating", "an uong", "ăn", "uong", "uống", "ban tiec", "bàn tiệc", "table", "guest", "khach", "khách"]):
        return "guest_food", "keyword_guest_food"

    if any(k in s for k in ["dress", "ring", "nhan", "nhẫn", "flower", "bouquet", "shoe", "shoes", "decor", "venue", "hotel", "setup", "detail", "makeup detail"]):
        return "intro_beauty", "keyword_intro_beauty"

    if any(k in s for k in ["bride", "groom", "couple", "cdcr", "co dau", "cô dâu", "chu re", "chú rể", "firstlook", "first look", "portrait"]):
        return "cdcr", "keyword_cdcr"

    if any(k in s for k in ["makeup", "make up", "trang diem", "trang điểm", "prep", "getting ready"]):
        return "makeup", "keyword_makeup"

    if any(k in s for k in ["gia tien", "gia_tien", "gia-tien", "le gia", "lễ gia", "altar", "ceremony", "church", "nha tho", "nhà thờ"]):
        return "ceremony_giatien", "keyword_ceremony"

    if any(k in s for k in ["ruoc dau", "rước dâu", "ruoc_dau", "ruoc-dau", "pickup"]):
        return "ruoc_dau", "keyword_ruoc_dau"

    if any(k in s for k in ["reception", "stage", "sân khấu", "san khau", "speech", "toast", "cake", "champagne"]):
        return "reception_stage", "keyword_reception_stage"

    if any(k in s for k in ["dance", "party", "dj", "club", "after party", "nhay", "nhảy"]):
        return "party", "keyword_party"

    if any(k in s for k in ["family", "parents", "ba me", "bố mẹ", "bo me", "group", "relatives"]):
        return "family", "keyword_family"

    if any(k in s for k in ["ending", "thank", "bye", "outro", "final"]):
        return "ending", "keyword_ending"

    # Chronology fallback, but do NOT call early generic clips CDCR. Unknown means needs manual.
    if order_pos < 0.10:
        return "intro_beauty", "chrono_weak_intro"
    if order_pos < 0.35:
        return "cdcr", "chrono_weak_cdcr"
    if order_pos < 0.62:
        return "ceremony_giatien", "chrono_weak_ceremony"
    if order_pos < 0.82:
        return "reception_stage", "chrono_weak_reception"
    return "ending", "chrono_weak_ending"


def load_manual(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    m = {}
    for r in rows:
        fn = str(r.get("filename") or "").lower().strip()
        if fn:
            m[fn] = r
    return m


def main() -> None:
    p = argparse.ArgumentParser(description="117B scene semantic tags for wedding story.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--overwrite-template", action="store_true")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "scene_tags_117b")
    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "scene_tags_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    by_path, by_name = beauty_lookup(project)

    files = []
    for ext in VIDEO_EXTS:
        files.extend(source.rglob(f"*{ext}"))
    files = sorted(set(files), key=lambda p: str(p).lower())
    total = max(1, len(files))

    template = project / "stt_scene_tags_manual.csv"
    manual = load_manual(template)

    rows = []
    for i, f in enumerate(files):
        pos = i / total
        auto_tag, reason = guess_tag(f, pos)
        b = by_path.get(norm(f)) or by_name.get(f.name.lower()) or {}
        m = manual.get(f.name.lower(), {})

        final_tag = str(m.get("scene_tag") or auto_tag).strip()
        priority = str(m.get("priority") or "").strip()
        exclude = boolish(m.get("exclude", ""))
        note = str(m.get("note") or "").strip()

        # If user leaves impossible/blank tag, keep other.
        if final_tag not in SECTION_ORDER:
            final_tag = "other"

        rows.append({
            "filename": f.name,
            "scene_tag": final_tag,
            "auto_tag": auto_tag,
            "tag_reason": reason,
            "priority": priority,
            "exclude": "true" if exclude else "",
            "note": note,
            "beauty_score": fnum(b.get("beauty_score"), 0),
            "beauty_class": b.get("beauty_class", ""),
            "motion_class": b.get("motion_class", ""),
            "best_source_in_sec": fnum(b.get("best_source_in_sec"), 0),
            "media_duration_sec": fnum(b.get("duration_sec"), 0),
            "file": str(f),
            "_source_order": i,
        })

    # Create editable CSV if missing or forced. Keep same columns user can edit.
    if a.overwrite_template or not template.exists():
        write_csv(template, rows, [
            "filename", "scene_tag", "auto_tag", "tag_reason", "priority", "exclude", "note",
            "beauty_score", "beauty_class", "motion_class", "best_source_in_sec", "media_duration_sec", "file"
        ])

    counts = {s: sum(1 for r in rows if r["scene_tag"] == s and not boolish(r.get("exclude"))) for s in SECTION_ORDER}
    data = {
        "ok": True,
        "module": "117B_scene_tags",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "manual_csv": str(template),
        "file_count": len(rows),
        "scene_counts": counts,
        "items": rows,
    }
    write_json(project / "stt_scene_tags_v2.json", data)
    write_json(out / "stt_scene_tags_v2.json", data)
    write_csv(out / "SCENE_TAGS_ACTIVE_V2.csv", rows, [
        "filename", "scene_tag", "auto_tag", "tag_reason", "priority", "exclude", "note",
        "beauty_score", "beauty_class", "motion_class", "best_source_in_sec", "media_duration_sec", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "manual_csv": str(template),
        "file_count": len(rows),
        "scene_counts": counts,
        "fix": "117B_scene_tags",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)
        open_path(template)


if __name__ == "__main__":
    main()
