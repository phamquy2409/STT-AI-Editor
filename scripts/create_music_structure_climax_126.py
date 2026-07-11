from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from music_climax_common import *

def locate_music(project: Path, explicit: str) -> str:
    if explicit and Path(explicit).exists():
        return str(Path(explicit))
    for name in [
        "stt_precise_beat_grid_v2.json",
        "stt_music_director_map_v1.json",
        "stt_music_beat_map_v1.json",
    ]:
        d = read_json(project / name)
        p = str(d.get("music_file") or "")
        if p and Path(p).exists():
            return p
    return ""

def energy_envelope(samples: list[float], sr: int, step_sec: float = 0.50) -> list[dict[str, float]]:
    if not samples:
        return []
    win = max(1, int(sr * step_sec))
    rows = []
    prev = 0.0
    for i in range(0, len(samples), win):
        chunk = samples[i:i+win]
        if not chunk:
            continue
        rms = math.sqrt(sum(x*x for x in chunk) / len(chunk))
        peak = max(abs(x) for x in chunk)
        flux = max(0.0, rms - prev)
        rows.append({
            "time_sec": round(i / sr, 4),
            "energy": float(rms),
            "peak": float(peak),
            "flux": float(flux),
        })
        prev = rms
    energies = smooth([x["energy"] for x in rows], 3)
    fluxes = smooth([x["flux"] for x in rows], 2)
    e90 = max(percentile(energies, 0.90), 1e-9)
    f90 = max(percentile(fluxes, 0.90), 1e-9)
    for i, row in enumerate(rows):
        row["energy_smooth"] = round(energies[i], 8)
        row["flux_smooth"] = round(fluxes[i], 8)
        row["energy_norm"] = round(clamp(energies[i] / e90, 0, 1.5), 5)
        row["flux_norm"] = round(clamp(fluxes[i] / f90, 0, 1.5), 5)
        row["impact"] = round(row["energy_norm"] * 0.72 + row["flux_norm"] * 0.28, 5)
    return rows

def nearest_impact(env: list[dict[str, float]], sec: float) -> float:
    if not env:
        return 0.5
    row = min(env, key=lambda x: abs(fnum(x.get("time_sec"), 0) - sec))
    return fnum(row.get("impact"), 0.5)

def top_emphasis_points(
    env: list[dict[str, float]],
    beats: list[dict[str, Any]],
    duration: float,
    count: int = 8,
) -> list[dict[str, Any]]:
    candidates = []
    for b in beats:
        t = fnum(b.get("time_sec"), -1)
        if t < duration * 0.08 or t > duration * 0.94:
            continue
        strength = fnum(b.get("strength"), 0.5)
        impact = nearest_impact(env, t)
        score = impact * 0.68 + strength * 0.32
        candidates.append({
            "time_sec": round(t, 4),
            "score": round(score, 5),
            "energy_impact": round(impact, 5),
            "beat_strength": round(strength, 5),
            "beat_type": str(b.get("type") or ""),
        })
    candidates.sort(key=lambda x: fnum(x.get("score"), 0), reverse=True)
    selected = []
    for c in candidates:
        t = fnum(c.get("time_sec"), 0)
        if any(abs(t - fnum(x.get("time_sec"), 0)) < 6.0 for x in selected):
            continue
        selected.append(c)
        if len(selected) >= count:
            break
    return sorted(selected, key=lambda x: fnum(x.get("time_sec"), 0))

def make_sections(duration: float, main_peak: float) -> list[dict[str, Any]]:
    duration = max(60.0, duration)
    intro_end = clamp(duration * 0.09, 12.0, 22.0)
    ending_len = clamp(duration * 0.075, 10.0, 18.0)
    ending_start = duration - ending_len

    peak = clamp(main_peak, duration * 0.52, duration * 0.84)
    pre_start = max(intro_end + 18.0, peak - clamp(duration * 0.07, 10.0, 17.0))
    build_start = max(intro_end + 10.0, pre_start - clamp(duration * 0.13, 20.0, 34.0))
    climax_start = max(pre_start + 4.0, peak - 2.5)
    climax_end = min(ending_start - 8.0, peak + clamp(duration * 0.055, 9.0, 15.0))
    release_end = ending_start

    points = [
        (0.0, intro_end, "intro", "hold", 0.72),
        (intro_end, build_start, "story", "medium", 0.58),
        (build_start, pre_start, "build", "rising", 0.76),
        (pre_start, climax_start, "pre_climax", "fast", 0.90),
        (climax_start, climax_end, "climax", "hero_mix", 1.00),
        (climax_end, release_end, "release", "medium_hold", 0.68),
        (release_end, duration, "ending", "emotional_hold", 0.88),
    ]

    sections = []
    for i, (st, en, label, rhythm, importance) in enumerate(points, 1):
        if en <= st:
            continue
        sections.append({
            "index": i,
            "label": label,
            "start_sec": round(st, 4),
            "end_sec": round(en, 4),
            "duration_sec": round(en - st, 4),
            "rhythm": rhythm,
            "importance": importance,
            "slow_allowed": label in {"climax", "ending"},
            "hero_required": label == "climax",
        })
    return sections

def main() -> None:
    p = argparse.ArgumentParser(description="126 Music Structure + Climax Map V3.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--music", default="")
    p.add_argument("--target-seconds", type=float, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "music_structure_climax_126")
    tl = current_timeline(project)
    beat_data = read_json(project / "stt_precise_beat_grid_v2.json")
    beats = list(beat_data.get("beats") or [])
    music = locate_music(project, a.music)

    target = a.target_seconds if a.target_seconds > 0 else timeline_duration(tl)
    music_dur = media_duration(music) if music else 0
    if target <= 0:
        target = music_dur or fnum(beat_data.get("target_seconds"), 210)
    if music_dur > 0:
        target = min(target, music_dur)
    target = max(30.0, target)

    sr = 11025
    samples = ffmpeg_pcm(music, sr, target + 2) if music else []
    env = energy_envelope(samples, sr)

    if env:
        search = [
            x for x in env
            if target * 0.42 <= fnum(x.get("time_sec"), 0) <= target * 0.88
        ]
        main_row = max(search or env, key=lambda x: fnum(x.get("impact"), 0))
        main_peak = fnum(main_row.get("time_sec"), target * 0.70)
        used_real_audio = True
    else:
        strong = [
            b for b in beats
            if target * 0.42 <= fnum(b.get("time_sec"), 0) <= target * 0.88
        ]
        main_beat = max(strong or beats or [{"time_sec": target * 0.70}], key=lambda x: fnum(x.get("strength"), 0))
        main_peak = fnum(main_beat.get("time_sec"), target * 0.70)
        used_real_audio = False

    emphasis = top_emphasis_points(env, beats, target, 8)
    if not emphasis:
        emphasis = [{
            "time_sec": round(main_peak, 4),
            "score": 1.0,
            "energy_impact": 1.0,
            "beat_strength": 1.0,
            "beat_type": "fallback_main_climax",
        }]

    main_emphasis = min(emphasis, key=lambda x: abs(fnum(x.get("time_sec"), 0) - main_peak))
    main_peak = fnum(main_emphasis.get("time_sec"), main_peak)
    sections = make_sections(target, main_peak)

    data = {
        "ok": True,
        "module": "126_music_structure_climax_v3",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "music_file": music,
        "target_seconds": round(target, 4),
        "music_duration_sec": round(music_dur, 4),
        "used_real_audio": used_real_audio,
        "main_climax_sec": round(main_peak, 4),
        "sections": sections,
        "emphasis_points": emphasis,
        "energy_envelope": env,
        "rules": {
            "reserve_best_shot_for_main_climax": True,
            "reserve_couple_shot_for_ending": True,
            "slow_minimum_speed_percent": 50,
            "slow_only_at_emphasis": True,
        },
    }

    write_json(project / "stt_music_structure_climax_v3.json", data)
    write_json(out / "stt_music_structure_climax_v3.json", data)
    write_csv(out / "MUSIC_STRUCTURE_SECTIONS.csv", sections, [
        "index", "label", "start_sec", "end_sec", "duration_sec",
        "rhythm", "importance", "slow_allowed", "hero_required"
    ])
    write_csv(out / "MUSIC_EMPHASIS_POINTS.csv", emphasis, [
        "time_sec", "score", "energy_impact", "beat_strength", "beat_type"
    ])
    write_csv(out / "MUSIC_ENERGY_ENVELOPE.csv", env, [
        "time_sec", "energy", "peak", "flux", "energy_smooth",
        "flux_smooth", "energy_norm", "flux_norm", "impact"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "music_file": music,
        "target_seconds": round(target, 3),
        "used_real_audio": used_real_audio,
        "main_climax_sec": round(main_peak, 3),
        "section_count": len(sections),
        "emphasis_count": len(emphasis),
        "fix": "126_music_structure_climax_v3",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)

if __name__ == "__main__":
    main()
