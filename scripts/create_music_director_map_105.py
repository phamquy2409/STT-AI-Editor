from music_director_common import *


def classify_mode(e: float, flux: float, q20: float, q50: float, q75: float, fq90: float) -> str:
    if e <= q20:
        return "quiet_hold"
    if flux >= fq90:
        return "impact_cut"
    if e >= q75 and flux >= fq90 * 0.65:
        return "climax_fast"
    if e >= q75:
        return "build_fast"
    if e <= q50:
        return "emotion_long"
    return "story_medium"


def smooth_modes(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not blocks:
        return blocks
    merged: list[dict[str, Any]] = []
    for b in blocks:
        if merged and merged[-1]["mode"] == b["mode"]:
            merged[-1]["end_sec"] = b["end_sec"]
            merged[-1]["energy"] = round((fnum(merged[-1]["energy"]) + fnum(b["energy"])) / 2, 7)
            merged[-1]["flux"] = round((fnum(merged[-1]["flux"]) + fnum(b["flux"])) / 2, 7)
        else:
            merged.append(dict(b))

    out: list[dict[str, Any]] = []
    for b in merged:
        dur = fnum(b["end_sec"]) - fnum(b["start_sec"])
        if out and dur < 4.0 and b["mode"] != "impact_cut":
            out[-1]["end_sec"] = b["end_sec"]
            out[-1]["note"] = (out[-1].get("note", "") + " merged_short").strip()
        else:
            out.append(b)
    return out


def build_director_map(env: list[dict[str, float]], target_seconds: int) -> list[dict[str, Any]]:
    if not env:
        sections = [
            (0, 24, "quiet_hold"),
            (24, 80, "story_medium"),
            (80, 150, "emotion_long"),
            (150, 230, "build_fast"),
            (230, 310, "climax_fast"),
            (310, 390, "story_medium"),
            (390, target_seconds, "ending_hold"),
        ]
        return [{"start_sec": s, "end_sec": e, "mode": m, "energy": 0, "flux": 0, "note": "fallback"} for s, e, m in sections if s < target_seconds]

    rms_vals = [x["rms"] for x in env]
    flux_vals = [x["flux"] for x in env]
    q20 = percentile(rms_vals, 0.20)
    q50 = percentile(rms_vals, 0.50)
    q75 = percentile(rms_vals, 0.75)
    fq90 = percentile(flux_vals, 0.90)

    phrase = 12.0
    blocks = []
    n = int(target_seconds / phrase) + 1
    for i in range(n):
        st = i * phrase
        en = min(target_seconds, st + phrase)
        vals = [x for x in env if st <= x["time_sec"] < en]
        if not vals:
            continue
        e = sum(x["rms"] for x in vals) / len(vals)
        fl = max(x["flux"] for x in vals)
        mode = classify_mode(e, fl, q20, q50, q75, fq90)
        if en >= target_seconds - 24:
            mode = "ending_hold" if e <= q75 else "story_medium"
        blocks.append({
            "start_sec": round(st, 3),
            "end_sec": round(en, 3),
            "mode": mode,
            "energy": round(e, 7),
            "flux": round(fl, 7),
            "note": "auto_music_phrase",
        })

    blocks = smooth_modes(blocks)

    for b in blocks:
        st = fnum(b["start_sec"])
        pos = st / max(1, target_seconds)
        if pos < 0.08 and b["mode"] not in {"impact_cut", "climax_fast"}:
            b["mode"] = "quiet_hold"
            b["note"] = b.get("note", "") + " intro_arc"
        elif 0.38 <= pos <= 0.68 and b["mode"] in {"story_medium", "emotion_long"}:
            b["mode"] = "build_fast"
            b["note"] = b.get("note", "") + " mid_build_arc"
        elif 0.68 < pos <= 0.82:
            b["mode"] = "climax_fast"
            b["note"] = b.get("note", "") + " climax_arc"
        elif pos > 0.88:
            b["mode"] = "ending_hold"
            b["note"] = b.get("note", "") + " ending_arc"
    return blocks


def manual_template(project: Path, blocks: list[dict[str, Any]]) -> Path:
    p = project / "stt_music_director_manual.csv"
    if not p.exists():
        write_csv(p, blocks, ["start_sec", "end_sec", "mode", "energy", "flux", "note"])
    return p


def main() -> None:
    p = argparse.ArgumentParser(description="105 music director map: structure/feeling map, not simple beat.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--music-folder", default="D:/27thang6pschh")
    p.add_argument("--music", default="")
    p.add_argument("--target-seconds", type=int, default=480)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "music_director_map_105")

    music = find_music(project, a.music_folder, a.music)
    if not music:
        res = {"ok": False, "error": "MUSIC_NOT_FOUND"}
        write_json(out / "music_director_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    samples = ffmpeg_pcm(music, sample_rate=8000, duration_limit=a.target_seconds + 30)
    env = envelope(samples, sr=8000, win_ms=250)
    blocks = build_director_map(env, a.target_seconds)
    manual_path = manual_template(project, blocks)

    data = {
        "ok": True,
        "module": "105_music_director_map",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "music_file": music,
        "target_seconds": a.target_seconds,
        "used_real_audio": bool(env),
        "director_blocks": blocks,
        "manual_csv": str(manual_path),
        "mode_counts": {m: sum(1 for b in blocks if b["mode"] == m) for m in sorted({b["mode"] for b in blocks})},
    }
    write_json(project / "stt_music_director_map_v1.json", data)
    write_json(out / "stt_music_director_map_v1.json", data)
    write_csv(out / "MUSIC_DIRECTOR_MAP.csv", blocks, ["start_sec", "end_sec", "mode", "energy", "flux", "note"])
    write_csv(out / "AUDIO_ENVELOPE.csv", env, ["time_sec", "rms", "peak", "flux"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "music_file": music,
        "used_real_audio": bool(env),
        "director_block_count": len(blocks),
        "mode_counts": data["mode_counts"],
        "manual_csv": str(manual_path),
        "fix": "105_music_director_map",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
