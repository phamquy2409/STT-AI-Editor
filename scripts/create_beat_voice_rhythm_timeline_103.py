from rhythm_common import *


def nearest_beat_after(beats: list[dict[str, Any]], t: float, min_gap: float, max_gap: float) -> float:
    for b in beats:
        bt = fnum(b.get("time_sec"), 0)
        if bt >= t + min_gap and bt <= t + max_gap:
            return bt
    return t + max_gap


def is_in_voice_window(t: float, windows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for w in windows:
        if fnum(w.get("start_sec"), 0) <= t <= fnum(w.get("end_sec"), 0):
            return w
    return None


def rhythm_duration(section: str, i: int, energy: str, voice: bool) -> tuple[float, str]:
    if voice:
        # long hold for voice/speech/vow
        pattern = [3.2, 4.0, 2.8, 5.0]
        return pattern[i % len(pattern)], "voice_hold_long"
    if section == "intro":
        pattern = [0.55, 0.75, 0.45, 1.1, 0.6, 0.9]
    elif section == "climax":
        pattern = [0.45, 0.55, 0.8, 0.5, 1.2, 0.65]
    elif section == "ending":
        pattern = [1.5, 2.2, 1.1, 2.8, 1.6]
    else:
        pattern = [1.0, 1.4, 0.8, 1.8, 1.2, 2.2]
    d = pattern[i % len(pattern)]
    if energy == "high_energy":
        d *= 0.82
    elif energy == "low_energy":
        d *= 1.25
    return max(0.35, min(5.5, d)), "beat_short_long_pattern"


def energy_at(sections: list[dict[str, Any]], t: float) -> str:
    for s in sections:
        if fnum(s.get("start_sec"), 0) <= t < fnum(s.get("end_sec"), 0):
            return str(s.get("mood") or "mid_energy")
    return "mid_energy"


def main() -> None:
    p = argparse.ArgumentParser(description="103 Beat/voice rhythm timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--target-seconds", type=int, default=480)
    p.add_argument("--target-shots", type=int, default=180)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "beat_voice_rhythm_timeline_103")

    source_tl = read_json(project / "stt_profile_story_timeline_v1.json") or read_json(project / "stt_learned_inout_timeline_v1.json") or load_timeline(project)
    beat = read_json(project / "stt_music_beat_map_v1.json")
    voice = read_json(project / "stt_voice_pause_map_v1.json")
    if not source_tl:
        res = {"ok": False, "error": "NO_SOURCE_TIMELINE"}
        write_json(out / "beat_voice_rhythm_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    base_items = list(source_tl.get("items") or [])[:a.target_shots]
    beats = list(beat.get("beats") or [])
    sections = list(beat.get("sections") or [])
    windows = list(voice.get("voice_windows") or [])

    if not beats:
        beats = [{"time_sec": round(i * 0.5, 3), "strength": 0.5, "type": "fallback"} for i in range(int(a.target_seconds / 0.5) + 5)]

    t = 0.0
    items = []
    for i, raw in enumerate(base_items, start=1):
        if t >= a.target_seconds:
            break
        section = str(raw.get("target_section") or "story")
        vw = is_in_voice_window(t, windows)
        energy = energy_at(sections, t)
        wanted, reason = rhythm_duration(section, i, energy, bool(vw))

        if vw:
            min_gap = min(wanted, fnum(vw.get("hold_min_sec"), wanted))
            cut_t = min(t + min_gap, a.target_seconds)
            snapped = cut_t
            snap_reason = "voice_no_beat_snap"
        else:
            snapped = nearest_beat_after(beats, t, min_gap=max(0.28, wanted * 0.65), max_gap=min(5.5, wanted * 1.45))
            if snapped > a.target_seconds:
                snapped = a.target_seconds
            snap_reason = "cut_on_music_beat"

        dur = max(0.25, snapped - t)
        row = dict(raw)
        row.update({
            "index": len(items) + 1,
            "timeline_start_sec": round(t, 3),
            "timeline_end_sec": round(t + dur, 3),
            "duration_sec": round(dur, 3),
            "source_in_sec": 0.0,
            "source_out_sec": round(dur, 3),
            "source_duration_sec": round(dur, 3),
            "rhythm_reason": reason,
            "snap_reason": snap_reason,
            "music_energy": energy,
            "voice_hold": bool(vw),
        })
        items.append(row)
        t += dur

    data = {
        "ok": True,
        "module": "103_beat_voice_rhythm_timeline",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "style_profile": a.style_profile,
        "target_seconds": a.target_seconds,
        "target_shots": a.target_shots,
        "timeline_count": len(items),
        "timeline_seconds": round(t, 3),
        "used_real_music_audio": beat.get("used_real_audio"),
        "bpm_estimate": beat.get("bpm_estimate"),
        "items": items,
    }
    write_json(project / "stt_beat_voice_rhythm_timeline_v1.json", data)
    write_json(out / "stt_beat_voice_rhythm_timeline_v1.json", data)
    write_csv(out / "BEAT_VOICE_RHYTHM_TIMELINE.csv", items, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "rhythm_reason", "snap_reason", "music_energy", "voice_hold", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "timeline_count": len(items),
        "timeline_seconds": round(t, 3),
        "used_real_music_audio": beat.get("used_real_audio"),
        "bpm_estimate": beat.get("bpm_estimate"),
        "fix": "103_beat_voice_rhythm_timeline",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
