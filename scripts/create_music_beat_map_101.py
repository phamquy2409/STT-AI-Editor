from rhythm_common import *


def detect_music_beats(music_file: str, target_seconds: int, sample_rate: int = 8000) -> dict[str, Any]:
    samples = ffmpeg_pcm_mono(music_file, sample_rate=sample_rate, duration_limit=max(60, target_seconds + 20))
    env = energy_envelope(samples, sr=sample_rate, win_ms=100)
    if not env:
        # fallback cinematic 120bpm grid
        beat_step = 0.5
        beats = [{"time_sec": round(i * beat_step, 3), "strength": 0.5, "type": "fallback_grid"} for i in range(int(target_seconds / beat_step) + 4)]
        return {"used_real_audio": False, "bpm_estimate": 120, "beats": beats, "sections": []}

    rms_vals = [x["rms"] for x in env]
    avg = sum(rms_vals) / max(1, len(rms_vals))
    # local peak detection
    beats = []
    last_t = -1.0
    for i in range(2, len(env) - 2):
        t = env[i]["time_sec"]
        if t > target_seconds + 5:
            break
        v = env[i]["rms"]
        if v > avg * 1.12 and v >= env[i-1]["rms"] and v >= env[i+1]["rms"] and (t - last_t) >= 0.28:
            strength = min(1.0, v / max(avg * 2.8, 0.0001))
            beats.append({"time_sec": round(t, 3), "strength": round(strength, 3), "type": "audio_peak"})
            last_t = t

    # if too few peaks, make grid from estimated energy interval
    if len(beats) < target_seconds * 0.7:
        beat_step = 0.5
        beats = [{"time_sec": round(i * beat_step, 3), "strength": 0.55, "type": "fallback_grid"} for i in range(int(target_seconds / beat_step) + 4)]
        used_real = False
        bpm = 120
    else:
        gaps = [beats[i]["time_sec"] - beats[i-1]["time_sec"] for i in range(1, min(len(beats), 80))]
        good = [g for g in gaps if 0.28 <= g <= 1.2]
        step = sum(good) / len(good) if good else 0.5
        bpm = round(60 / step, 1) if step else 120
        used_real = True

    # music energy sections every 8 seconds
    sections = []
    block = 8.0
    n_blocks = int(max(target_seconds, env[-1]["time_sec"]) / block) + 1
    for b in range(n_blocks):
        st = b * block
        en = st + block
        vals = [x["rms"] for x in env if st <= x["time_sec"] < en]
        e = sum(vals) / len(vals) if vals else avg
        if e > avg * 1.25:
            mood = "high_energy"
        elif e < avg * 0.75:
            mood = "low_energy"
        else:
            mood = "mid_energy"
        sections.append({"start_sec": round(st, 3), "end_sec": round(en, 3), "energy": round(e, 6), "mood": mood})

    return {"used_real_audio": used_real, "bpm_estimate": bpm, "beats": beats, "sections": sections, "env_avg": round(avg, 6)}


def main() -> None:
    p = argparse.ArgumentParser(description="101 Real music beat map.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--music-folder", default="D:/27thang6pschh")
    p.add_argument("--music", default="")
    p.add_argument("--target-seconds", type=int, default=480)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "music_beat_map_101")
    music_file = find_music(project, a.music_folder, a.music)

    if not music_file:
        res = {"ok": False, "error": "MUSIC_NOT_FOUND"}
        write_json(out / "music_beat_map_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    beat = detect_music_beats(music_file, a.target_seconds)
    data = {
        "ok": True,
        "module": "101_music_beat_map",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "music_file": music_file,
        "target_seconds": a.target_seconds,
        **beat,
    }
    write_json(project / "stt_music_beat_map_v1.json", data)
    write_json(out / "stt_music_beat_map_v1.json", data)
    write_csv(out / "MUSIC_BEATS.csv", data["beats"], ["time_sec", "strength", "type"])
    write_csv(out / "MUSIC_SECTIONS.csv", data["sections"], ["start_sec", "end_sec", "energy", "mood"])

    res = {
        "ok": True,
        "report_dir": str(out),
        "music_file": music_file,
        "used_real_audio": data["used_real_audio"],
        "bpm_estimate": data["bpm_estimate"],
        "beat_count": len(data["beats"]),
        "section_count": len(data["sections"]),
        "fix": "101_music_beat_map",
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
