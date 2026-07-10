
from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import tempfile
import wave
from array import array
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
import xml.etree.ElementTree as ET
from xml.dom import minidom

DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"
DEFAULT_SOURCE_FOLDER = "D:/5thang5test"

def appdata_dir() -> Path:
    p = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "STT_AI_Editor"
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}

def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

def outdir(project_root: Path, name: str) -> Path:
    p = project_root / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def open_path(path: Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass

def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def inum(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default

def sec_to_frames(sec: float, timebase: int = 25) -> int:
    return int(round(max(0.0, sec) * timebase))

def frames_to_sec(frames: int, timebase: int = 25) -> float:
    return max(0.0, frames / max(1, timebase))

def file_url(path: str | Path) -> str:
    p = str(path).replace("\\", "/")
    return "file://localhost/" + quote(p, safe="/:")

def html_table(title: str, rows: list[dict[str, Any]], cols: list[str], note: str = "") -> str:
    import html
    th = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    tr = "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(c,'')))}</td>" for c in cols) + "</tr>" for r in rows)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:Arial;background:#111;color:#eee;margin:32px}"
        ".card{background:#181818;border:1px solid #333;border-radius:16px;padding:24px}"
        "td,th{border-bottom:1px solid #333;padding:8px;text-align:left;font-size:13px}</style></head>"
        f"<body><div class='card'><h1>{html.escape(title)}</h1><p>{html.escape(note)}</p>"
        f"<table><tr>{th}</tr>{tr}</table></div></body></html>"
    )

def load_selected_music(project_root: Path) -> dict[str, Any]:
    d = read_json(project_root / "stt_selected_music_v1.json") or read_json(appdata_dir() / "stt_selected_music_v1.json")
    if isinstance(d.get("selected"), dict):
        return d["selected"]
    return {}

def load_timeline(project_root: Path) -> list[dict[str, Any]]:
    for name in [
        "stt_beat_locked_timeline_v1.json",
        "stt_music_synced_timeline_v1.json",
        "stt_smart_wedding_timeline_v1.json",
        "stt_wedding_documentary_timeline_v1.json",
        "stt_prewedding_refined_v1.json",
    ]:
        d = read_json(project_root / name)
        if isinstance(d.get("timeline"), list):
            return list(d["timeline"])
    return []

def add_text(parent: ET.Element, tag: str, text: Any = "") -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = str(text)
    return el

def add_rate(parent: ET.Element, timebase: int) -> None:
    rate = ET.SubElement(parent, "rate")
    add_text(rate, "timebase", timebase)
    add_text(rate, "ntsc", "FALSE")

def add_timecode(parent: ET.Element, timebase: int) -> None:
    tc = ET.SubElement(parent, "timecode")
    add_rate(tc, timebase)
    add_text(tc, "string", "00:00:00:00")
    add_text(tc, "frame", 0)
    add_text(tc, "displayformat", "NDF")

def pretty_xml(root: ET.Element) -> str:
    raw = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

def preset_size(preset: str) -> tuple[int, int]:
    low = preset.lower()
    if "vertical" in low or "1080_1920" in low:
        return 1080, 1920
    if "4k" in low:
        return 3840, 2160
    return 1920, 1080

def convert_to_wav_mono_16k(src: Path, dst: Path) -> tuple[bool, str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False, "FFMPEG_NOT_FOUND"
    cmd = [ffmpeg, "-y", "-i", str(src), "-ac", "1", "-ar", "16000", "-vn", str(dst)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            return False, (res.stderr or res.stdout or "ffmpeg failed")[-500:]
        return True, "ok"
    except Exception as exc:
        return False, repr(exc)

def read_wav_samples(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as w:
        channels = w.getnchannels()
        width = w.getsampwidth()
        rate = w.getframerate()
        frames = w.getnframes()
        raw = w.readframes(frames)
    if width != 2:
        raise ValueError("Only 16-bit WAV supported after conversion")
    arr = array("h")
    arr.frombytes(raw)
    if channels > 1:
        mono = []
        for i in range(0, len(arr), channels):
            mono.append(sum(arr[i:i+channels]) / channels / 32768.0)
    else:
        mono = [x / 32768.0 for x in arr]
    return mono, rate

def rms_envelope(samples: list[float], rate: int, window_sec: float = 0.05) -> list[float]:
    win = max(1, int(rate * window_sec))
    env = []
    for i in range(0, len(samples), win):
        chunk = samples[i:i+win]
        if not chunk:
            break
        val = math.sqrt(sum(x*x for x in chunk) / len(chunk))
        env.append(val)
    if not env:
        return []
    mx = max(env) or 1.0
    return [x / mx for x in env]

def smooth(values: list[float], radius: int = 2) -> list[float]:
    if not values:
        return []
    out = []
    for i in range(len(values)):
        lo = max(0, i-radius)
        hi = min(len(values), i+radius+1)
        out.append(sum(values[lo:hi]) / (hi-lo))
    return out

def detect_peaks(env: list[float], step_sec: float, min_gap_sec: float = 0.35, threshold: float = 0.18) -> list[dict[str, Any]]:
    if len(env) < 3:
        return []
    sm = smooth(env, 2)
    peaks = []
    last_t = -999.0
    avg = sum(sm) / len(sm)
    for i in range(1, len(sm)-1):
        if sm[i] >= sm[i-1] and sm[i] > sm[i+1] and sm[i] >= max(threshold, avg * 1.18):
            t = i * step_sec
            if t - last_t >= min_gap_sec:
                peaks.append({"time_sec": round(t, 3), "energy": round(sm[i], 4)})
                last_t = t
    return peaks

def section_for_pos(t: float, duration: float) -> str:
    if t < duration * 0.12:
        return "intro"
    if duration * 0.58 <= t < duration * 0.82:
        return "climax"
    if duration * 0.42 <= t < duration * 0.58:
        return "build"
    if t >= duration * 0.88:
        return "ending"
    return "story"


def create_fallback_cut_points(target_seconds: float, bpm: float = 80.0) -> list[dict[str, Any]]:
    beat = 60.0 / max(40.0, min(180.0, bpm))
    points = []
    t = 0.0
    i = 1
    while t <= target_seconds:
        sec = section_for_pos(t, target_seconds)
        # intro/climax nhanh, emotion sections chậm hơn
        step_beats = 2 if sec in {"intro", "climax"} else (6 if sec == "ending" else 4)
        points.append({"index": i, "time_sec": round(t, 3), "energy": 0.5, "section": sec, "source": "fallback_bpm_grid"})
        t += step_beats * beat
        i += 1
    if not points or points[-1]["time_sec"] < target_seconds:
        points.append({"index": i, "time_sec": round(target_seconds,3), "energy": 0.1, "section": "ending", "source": "fallback_end"})
    return points

def create_real_audio_beat_energy_analyzer(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    target_seconds: float = 180.0,
    timebase: int = 25,
    open_folder: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    project_root = Path(project_root)
    out = outdir(project_root, "real_audio_beat_energy_analyzer")
    music = load_selected_music(project_root)
    plan = read_json(project_root / "stt_music_plan_v1.json") or read_json(appdata_dir() / "stt_music_plan_v1.json")
    if not music:
        res = {"ok": False, "error": "NO_SELECTED_MUSIC", "message": "Run 113 first."}
        write_json(out / "real_audio_beat_error.json", res)
        if open_folder: open_path(out)
        return res

    music_file = Path(str(music.get("file") or ""))
    music_in = fnum(plan.get("music_in_sec"), 0)
    music_out = fnum(plan.get("music_out_sec"), target_seconds)
    analyze_seconds = max(1.0, min(target_seconds, music_out - music_in))
    bpm = fnum(music.get("bpm"), 80.0)

    tmp = out / "_analysis_16k_mono.wav"
    ok, msg = convert_to_wav_mono_16k(music_file, tmp)
    used_real_audio = False
    cut_points: list[dict[str, Any]] = []
    peaks: list[dict[str, Any]] = []
    energy_sections: list[dict[str, Any]] = []

    if ok:
        try:
            samples, rate = read_wav_samples(tmp)
            start_idx = int(music_in * rate)
            end_idx = min(len(samples), int((music_in + analyze_seconds) * rate))
            samples = samples[start_idx:end_idx]
            step_sec = 0.05
            env = rms_envelope(samples, rate, window_sec=step_sec)
            peaks = detect_peaks(env, step_sec=step_sec, min_gap_sec=0.32, threshold=0.16)
            used_real_audio = True

            # Chọn cut points từ peak thật, nhưng không quá sát/quá xa.
            selected = []
            last = 0.0
            selected.append({"index": 1, "time_sec": 0.0, "energy": 0.3, "section": "intro", "source": "start"})
            for p in peaks:
                t = fnum(p.get("time_sec"), 0)
                sec = section_for_pos(t, analyze_seconds)
                min_gap = 0.65 if sec in {"intro","climax"} else 1.1
                max_gap = 4.8 if sec in {"gia_tien","vow_speech"} else 3.5
                if t - last >= min_gap:
                    if t - last > max_gap:
                        # chèn cut ảo ở downbeat gần giữa để tránh clip quá dài
                        mid = last + max_gap
                        selected.append({"index": len(selected)+1, "time_sec": round(mid,3), "energy": 0.25, "section": section_for_pos(mid, analyze_seconds), "source": "max_gap_fill"})
                        last = mid
                    selected.append({"index": len(selected)+1, "time_sec": round(t,3), "energy": p.get("energy"), "section": sec, "source": "real_peak"})
                    last = t
            if selected[-1]["time_sec"] < analyze_seconds:
                selected.append({"index": len(selected)+1, "time_sec": round(analyze_seconds,3), "energy": 0.1, "section": "ending", "source": "end"})
            cut_points = selected

            # section energy summary
            for sec in ["intro","story","build","climax","ending"]:
                vals = [env[i] for i in range(len(env)) if section_for_pos(i*step_sec, analyze_seconds) == sec]
                if vals:
                    energy_sections.append({"section": sec, "avg_energy": round(sum(vals)/len(vals), 4), "max_energy": round(max(vals),4)})
        except Exception as exc:
            cut_points = create_fallback_cut_points(analyze_seconds, bpm=bpm)
            msg = f"REAL_AUDIO_FAILED:{exc!r}"
    else:
        cut_points = create_fallback_cut_points(analyze_seconds, bpm=bpm)

    markers = []
    for i, cp in enumerate(cut_points, start=1):
        markers.append({
            "name": f"CUT {i:03d} {cp.get('section')}",
            "time_sec": cp["time_sec"],
            "frame": sec_to_frames(fnum(cp.get("time_sec"),0), timebase),
            "section": cp.get("section"),
            "source": cp.get("source"),
        })

    data = {
        "ok": True,
        "module": "118_real_audio_beat_energy_analyzer",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "music_file": str(music_file),
        "music_name": music.get("filename"),
        "music_in_sec": music_in,
        "analyze_seconds": round(analyze_seconds,3),
        "used_real_audio": used_real_audio,
        "ffmpeg_status": msg,
        "bpm_hint": bpm,
        "cut_point_count": len(cut_points),
        "peak_count": len(peaks),
        "cut_points": cut_points,
        "markers": markers,
        "energy_sections": energy_sections,
    }
    write_json(project_root / "stt_real_audio_beat_energy_v1.json", data)
    write_json(appdata_dir() / "stt_real_audio_beat_energy_v1.json", data)
    write_json(out / "stt_real_audio_beat_energy_v1.json", data)
    write_csv(out / "REAL_AUDIO_CUT_POINTS.csv", cut_points, ["index","time_sec","energy","section","source"])
    write_csv(out / "REAL_AUDIO_MARKERS.csv", markers, ["name","time_sec","frame","section","source"])
    (out / "REAL_AUDIO_BEAT_ENERGY_REPORT.html").write_text(
        html_table("Real Audio Beat / Energy Analyzer", cut_points[:250], ["index","time_sec","energy","section","source"], f"used_real_audio={used_real_audio} | {msg}"),
        encoding="utf-8",
    )
    if open_folder: open_path(out)
    return {"ok": True, "report_dir": str(out), "used_real_audio": used_real_audio, "cut_point_count": len(cut_points), "peak_count": len(peaks), "fix": "118_real_audio_beat_energy_analyzer"}
