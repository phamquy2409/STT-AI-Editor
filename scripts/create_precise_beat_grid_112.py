from precise_beat_beauty_common import *


def onset_envelope(samples: list[float], sr: int, win_ms: int = 46) -> list[dict[str, float]]:
    if not samples:
        return []
    win = max(1, int(sr * win_ms / 1000))
    rows = []
    prev_energy = 0.0
    prev_abs = 0.0
    for i in range(0, len(samples), win):
        chunk = samples[i:i+win]
        if not chunk:
            continue
        energy = math.sqrt(sum(x*x for x in chunk) / len(chunk))
        absavg = sum(abs(x) for x in chunk) / len(chunk)
        flux = max(0.0, energy - prev_energy) + max(0.0, absavg - prev_abs) * 0.7
        rows.append({
            "time_sec": round(i / sr, 4),
            "energy": round(energy, 8),
            "flux": round(flux, 8),
        })
        prev_energy = energy
        prev_abs = absavg
    return rows


def pick_onsets(env: list[dict[str, float]], target_seconds: int) -> list[dict[str, Any]]:
    if not env:
        return []
    fluxes = [x["flux"] for x in env]
    energies = [x["energy"] for x in env]
    f75 = percentile(fluxes, 0.75)
    f90 = percentile(fluxes, 0.90)
    e50 = percentile(energies, 0.50)

    onsets = []
    last = -1.0
    for i in range(2, len(env) - 2):
        t = env[i]["time_sec"]
        if t > target_seconds + 8:
            break
        v = env[i]["flux"]
        e = env[i]["energy"]
        local_peak = v >= env[i-1]["flux"] and v >= env[i+1]["flux"] and v >= env[i-2]["flux"] and v >= env[i+2]["flux"]
        if local_peak and v >= f75 and e >= e50 * 0.55 and (t - last) >= 0.22:
            strength = 0.65
            if v >= f90:
                strength = 1.0
            elif v >= (f75 + f90) / 2:
                strength = 0.82
            onsets.append({"time_sec": round(t, 4), "strength": round(strength, 3), "type": "onset_flux"})
            last = t
    return onsets


def estimate_grid(onsets: list[dict[str, Any]], target_seconds: int) -> tuple[float, float, list[dict[str, Any]]]:
    # Return bpm, beat_step, beat grid.
    if len(onsets) < 8:
        step = 0.5
        grid = [{"time_sec": round(i * step, 4), "strength": 0.5, "type": "fallback_grid"} for i in range(int(target_seconds / step) + 4)]
        return 120.0, step, grid

    times = [fnum(x["time_sec"]) for x in onsets]
    gaps = []
    for i in range(1, min(len(times), 220)):
        g = times[i] - times[i-1]
        if 0.28 <= g <= 1.2:
            gaps.append(g)

    # choose median-ish common beat gap; if onsets are half-beats, this still gives snap points.
    if gaps:
        gaps_sorted = sorted(gaps)
        step = gaps_sorted[len(gaps_sorted)//2]
    else:
        step = 0.5

    # normalize to useful range
    if step < 0.34:
        step *= 2
    if step > 0.85:
        step /= 2
    step = max(0.32, min(0.75, step))
    bpm = round(60.0 / step, 2)

    first = times[0] if times else 0.0
    # estimate offset by trying few onset times, pick most matching onsets.
    candidates = times[:min(24, len(times))]
    best_offset = first
    best_score = -1
    for off in candidates:
        score = 0
        for t in times[:200]:
            k = round((t - off) / step)
            grid_t = off + k * step
            if abs(grid_t - t) <= 0.08:
                score += 1
        if score > best_score:
            best_score = score
            best_offset = off

    while best_offset > 0:
        best_offset -= step

    grid = []
    t = best_offset
    count = 0
    onset_times = [fnum(o["time_sec"]) for o in onsets]
    while t <= target_seconds + 4:
        if t >= 0:
            near = min([abs(t - ot) for ot in onset_times] or [9])
            strength = 0.55
            typ = "tempo_grid"
            if near <= 0.07:
                strength = 0.95
                typ = "grid_on_onset"
            elif near <= 0.14:
                strength = 0.75
                typ = "grid_near_onset"
            if count % 8 == 0:
                strength = max(strength, 0.88)
                typ += "_phrase"
            elif count % 4 == 0:
                strength = max(strength, 0.78)
                typ += "_bar"
            grid.append({"time_sec": round(t, 4), "strength": round(strength, 3), "type": typ})
            count += 1
        t += step

    # add high confidence onsets too
    mixed = {round(g["time_sec"], 3): g for g in grid}
    for o in onsets:
        if o["strength"] >= 0.9:
            mixed.setdefault(round(o["time_sec"], 3), o)
    out = sorted(mixed.values(), key=lambda x: fnum(x["time_sec"]))
    return bpm, step, out


def main() -> None:
    p = argparse.ArgumentParser(description="112 Precise beat grid V2: onset + tempo grid.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--music-folder", default="D:/27thang6pschh")
    p.add_argument("--music", default="")
    p.add_argument("--target-seconds", type=int, default=480)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "precise_beat_grid_112")

    music = find_music(project, a.music_folder, a.music)
    if not music:
        res = {"ok": False, "error": "MUSIC_NOT_FOUND"}
        write_json(out / "precise_beat_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    sr = 11025
    samples = ffmpeg_pcm(music, sample_rate=sr, duration_limit=a.target_seconds + 30)
    env = onset_envelope(samples, sr=sr)
    onsets = pick_onsets(env, a.target_seconds)
    bpm, step, grid = estimate_grid(onsets, a.target_seconds)

    data = {
        "ok": True,
        "module": "112_precise_beat_grid_v2",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "music_file": music,
        "target_seconds": a.target_seconds,
        "used_real_audio": bool(samples),
        "bpm_estimate": bpm,
        "beat_step_sec": round(step, 4),
        "onset_count": len(onsets),
        "beat_count": len(grid),
        "beats": grid,
        "onsets": onsets,
    }
    write_json(project / "stt_precise_beat_grid_v2.json", data)
    write_json(out / "stt_precise_beat_grid_v2.json", data)
    write_csv(out / "PRECISE_BEATS_V2.csv", grid, ["time_sec", "strength", "type"])
    write_csv(out / "ONSETS_V2.csv", onsets, ["time_sec", "strength", "type"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "music_file": music,
        "used_real_audio": bool(samples),
        "bpm_estimate": bpm,
        "beat_step_sec": round(step, 4),
        "onset_count": len(onsets),
        "beat_count": len(grid),
        "fix": "112_precise_beat_grid_v2",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
