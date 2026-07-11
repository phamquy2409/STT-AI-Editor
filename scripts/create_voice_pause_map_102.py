from rhythm_common import *


VOICE_KEYS = ["vow", "speech", "voice", "mic", "toast", "phat bieu", "phát biểu", "doc loi", "đọc lời", "le", "lễ", "church", "nha tho", "nhà thờ", "gia tien", "gia_tien", "ruoc dau", "ruoc_dau"]


def looks_voice_clip(item: dict[str, Any]) -> bool:
    s = f"{item.get('filename','')} {item.get('file','')} {item.get('target_section','')}".lower()
    return any(k in s for k in VOICE_KEYS) or str(item.get("target_section")) in ["build", "climax"]


def detect_voice_windows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    windows = []
    for it in items:
        if not looks_voice_clip(it):
            continue
        st = fnum(it.get("timeline_start_sec"), 0)
        en = fnum(it.get("timeline_end_sec"), st + fnum(it.get("duration_sec"), 1))
        dur = max(0.1, en - st)
        # hold more in middle of voice-like clips, and leave room for pause before/after
        windows.append({
            "start_sec": round(st, 3),
            "end_sec": round(en, 3),
            "hold_min_sec": round(min(5.0, max(1.8, dur * 0.85)), 3),
            "filename": it.get("filename"),
            "reason": "filename_or_section_voice_like",
        })
    return windows


def main() -> None:
    p = argparse.ArgumentParser(description="102 Voice/pause rhythm map from timeline and filenames.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()
    project = Path(a.project)
    out = outdir(project, "voice_pause_map_102")
    tl = load_timeline(project)
    if not tl:
        res = {"ok": False, "error": "NO_TIMELINE"}
        write_json(out / "voice_pause_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    items = list(tl.get("items") or [])
    windows = detect_voice_windows(items)
    data = {
        "ok": True,
        "module": "102_voice_pause_map",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "timeline_count": len(items),
        "voice_window_count": len(windows),
        "voice_windows": windows,
    }
    write_json(project / "stt_voice_pause_map_v1.json", data)
    write_json(out / "stt_voice_pause_map_v1.json", data)
    write_csv(out / "VOICE_WINDOWS.csv", windows, ["start_sec", "end_sec", "hold_min_sec", "filename", "reason"])
    print(json.dumps({"ok": True, "report_dir": str(out), "timeline_count": len(items), "voice_window_count": len(windows), "fix": "102_voice_pause_map"}, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
