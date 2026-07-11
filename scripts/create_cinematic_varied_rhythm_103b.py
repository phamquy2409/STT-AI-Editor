from rhythm_varied_common import *


def main() -> None:
    p = argparse.ArgumentParser(description="103B cinematic varied rhythm timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--target-seconds", type=int, default=480)
    p.add_argument("--target-shots", type=int, default=180)
    p.add_argument("--beat-snap", choices=["soft", "off"], default="soft")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "cinematic_varied_rhythm_103b")

    base = load_base_timeline(project)
    beat = read_json(project / "stt_music_beat_map_v1.json")
    voice = read_json(project / "stt_voice_pause_map_v1.json")

    if not base:
        res = {"ok": False, "error": "NO_BASE_TIMELINE", "message": "Run 096 first."}
        write_json(out / "cinematic_varied_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    base_items = list(base.get("items") or [])
    beats = list(beat.get("beats") or [])
    sections = list(beat.get("sections") or [])
    windows = list(voice.get("voice_windows") or [])

    # choose target shots, but allow fewer if duration gets filled
    source_items = base_items[:max(1, a.target_shots)]

    raw_durations = []
    temp_t = 0.0
    for i, item in enumerate(source_items, start=1):
        section = str(item.get("target_section") or "story")
        energy = energy_at(sections, temp_t)
        vh = voice_window_at(temp_t, windows)
        d, reason = section_duration_recipe(section, i, energy, vh)
        raw_durations.append((d, reason, energy, vh))
        temp_t += d

    raw_total = sum(d for d, _, _, _ in raw_durations) or 1.0
    scale = a.target_seconds / raw_total

    items = []
    t = 0.0
    for i, (item, pack) in enumerate(zip(source_items, raw_durations), start=1):
        if t >= a.target_seconds:
            break
        raw_d, reason, energy, vh = pack
        d = raw_d * scale

        # keep contrast after scale
        if reason == "voice_emotion_hold":
            d = max(3.0, min(9.0, d))
        elif section_duration_recipe(str(item.get("target_section") or "story"), i, energy, vh)[1] == "cinematic_short_long_pattern":
            d = max(0.25, min(8.0, d))

        if t + d > a.target_seconds:
            d = max(0.25, a.target_seconds - t)

        end_t = t + d
        snapped = False
        if a.beat_snap == "soft" and not vh:
            # soft snap only near existing cut, avoids flattening everything to same beat length
            maybe, snapped = nearest_beat(beats, end_t, tolerance=0.12 if d < 1.0 else 0.20)
            if snapped and maybe > t + 0.25:
                end_t = maybe
                d = end_t - t

        row = dict(item)
        row.update({
            "index": len(items) + 1,
            "timeline_start_sec": round(t, 3),
            "timeline_end_sec": round(end_t, 3),
            "duration_sec": round(d, 3),
            "source_in_sec": 0.0,
            "source_out_sec": round(d, 3),
            "source_duration_sec": round(d, 3),
            "rhythm_reason": reason,
            "music_energy": energy,
            "voice_hold": bool(vh),
            "beat_snap": bool(snapped),
            "duration_before_scale": round(raw_d, 3),
        })
        items.append(row)
        t = end_t

    stats = duration_stats(items)
    data = {
        "ok": True,
        "module": "103B_cinematic_varied_rhythm",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "style_profile": a.style_profile,
        "target_seconds": a.target_seconds,
        "target_shots": a.target_shots,
        "timeline_count": len(items),
        "timeline_seconds": round(t, 3),
        "duration_stats": stats,
        "used_real_music_audio": beat.get("used_real_audio"),
        "bpm_estimate": beat.get("bpm_estimate"),
        "items": items,
    }

    write_json(project / "stt_cinematic_varied_rhythm_timeline_v1.json", data)
    # also overwrite the old rhythm file so other tools can use it
    write_json(project / "stt_beat_voice_rhythm_timeline_v1.json", data)
    write_json(out / "stt_cinematic_varied_rhythm_timeline_v1.json", data)
    write_csv(out / "CINEMATIC_VARIED_RHYTHM_TIMELINE.csv", items, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "rhythm_reason", "music_energy", "voice_hold", "beat_snap", "duration_before_scale", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(items),
        "timeline_seconds": round(t, 3),
        "duration_stats": stats,
        "used_real_music_audio": beat.get("used_real_audio"),
        "bpm_estimate": beat.get("bpm_estimate"),
        "fix": "103B_cinematic_varied_rhythm",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
