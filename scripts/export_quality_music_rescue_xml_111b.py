from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.sax.saxutils import escape

VIDEO_EXTS = {".mp4", ".mov", ".mxf", ".mts", ".m2ts", ".avi", ".mpg", ".mpeg", ".insv", ".braw"}


def read_json(path: str | Path) -> dict[str, Any]:
    try:
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: str | Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def open_path(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def outdir(project: Path, name: str) -> Path:
    p = project / "exports" / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def fnum(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def fr(sec: float, fps: int) -> int:
    return max(0, int(round(float(sec) * fps)))


def sec(frames: int, fps: int) -> float:
    return round(frames / fps, 3) if fps else 0.0


def pathurl_for(path: str | Path) -> str:
    p = str(path).replace("\\", "/")
    return "file://localhost/" + quote(p, safe="/:")


def preset_size(preset: str) -> tuple[int, int]:
    p = preset.lower()
    if "vertical" in p or "9x16" in p:
        return 1080, 1920
    if "1080" in p:
        return 1920, 1080
    return 3840, 2160


def media_duration(path: str | Path) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and (r.stdout or "").strip():
            return float((r.stdout or "").strip())
    except Exception:
        pass
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(str(path))
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            if fps > 0 and frames > 0:
                return float(frames / fps)
    except Exception:
        pass
    return 0.0


def duration_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [fnum(x.get("duration_sec"), 0) for x in items if fnum(x.get("duration_sec"), 0) > 0]
    if not vals:
        return {}
    xs = sorted(vals)
    def pct(p: float) -> float:
        return round(xs[int(round((len(xs)-1)*p))], 3)
    return {
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "avg": round(sum(vals)/len(vals), 3),
        "p10": pct(0.10),
        "p50": pct(0.50),
        "p90": pct(0.90),
        "under_0_7s": sum(1 for v in vals if v < 0.7),
        "over_3s": sum(1 for v in vals if v > 3.0),
        "over_5s": sum(1 for v in vals if v > 5.0),
    }


def load_timeline(project: Path) -> dict[str, Any]:
    for name in [
        "stt_quality_music_rescue_timeline_v2.json",
        "stt_music_directed_quality_timeline_v2.json",
        "stt_music_directed_timeline_v1.json",
    ]:
        d = read_json(project / name)
        if d and d.get("items"):
            return d
    return {}


def file_block(file_id: str, path: str, fps: int, width: int, height: int, file_duration_frames: int) -> str:
    name = Path(path).name
    return f'''
              <file id="{escape(file_id)}">
                <name>{escape(name)}</name>
                <pathurl>{escape(pathurl_for(path))}</pathurl>
                <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
                <duration>{max(file_duration_frames, 1)}</duration>
                <media>
                  <video>
                    <samplecharacteristics>
                      <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
                      <width>{width}</width>
                      <height>{height}</height>
                      <anamorphic>FALSE</anamorphic>
                      <pixelaspectratio>square</pixelaspectratio>
                      <fielddominance>none</fielddominance>
                    </samplecharacteristics>
                  </video>
                </media>
              </file>'''


def clip_xml(item: dict[str, Any], idx: int, fps: int, width: int, height: int) -> str:
    path = str(item.get("file"))
    name = str(item.get("filename") or Path(path).name)
    start = int(item["timeline_start_frame"])
    end = int(item["timeline_end_frame"])
    source_in = int(item["source_in_frame"])
    source_out = int(item["source_out_frame"])
    file_duration = int(item["file_duration_frames"])
    clip_duration = max(file_duration, source_out + fps)
    file_id = f"file-{idx}"

    return f'''
          <clipitem id="clipitem-{idx}">
            <name>{escape(name)}</name>
            <enabled>TRUE</enabled>
            <duration>{clip_duration}</duration>
            <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
            <start>{start}</start>
            <end>{end}</end>
            <in>{source_in}</in>
            <out>{source_out}</out>
            {file_block(file_id, path, fps, width, height, clip_duration)}
            <sourcetrack><mediatype>video</mediatype><trackindex>1</trackindex></sourcetrack>
            <fielddominance>none</fielddominance>
          </clipitem>'''


def sanitize(items: list[dict[str, Any]], fps: int, unknown_max_sec: float, preserve_unknown: bool) -> list[dict[str, Any]]:
    rows = []
    current = 0
    for it in items:
        path = str(it.get("file") or "")
        if not path or not Path(path).exists():
            continue
        if Path(path).suffix.lower() not in VIDEO_EXTS:
            continue

        desired = max(1, fr(fnum(it.get("duration_sec"), 1.0), fps))
        real = fnum(it.get("media_duration_sec"), 0)
        if real <= 0:
            real = media_duration(path)
        real_frames = fr(real, fps) if real > 0 else 0

        if real_frames > 0:
            dur_frames = min(desired, max(1, real_frames - 1))
            file_duration = max(real_frames, dur_frames + fps)
            status = "measured_clamped"
        else:
            if preserve_unknown:
                dur_frames = desired
                file_duration = max(dur_frames + fps * 10, fps * 60 * 60)
                status = "unknown_virtual_preserved"
            else:
                dur_frames = min(desired, max(1, fr(unknown_max_sec, fps)))
                file_duration = max(dur_frames + fps * 3, fps * 30)
                status = "unknown_short_to_avoid_stripes"

        row = dict(it)
        row.update({
            "timeline_start_frame": current,
            "timeline_end_frame": current + dur_frames,
            "duration_frames": dur_frames,
            "source_in_frame": 0,
            "source_out_frame": dur_frames,
            "file_duration_frames": file_duration,
            "timeline_start_sec": sec(current, fps),
            "timeline_end_sec": sec(current + dur_frames, fps),
            "duration_sec": sec(dur_frames, fps),
            "source_in_sec": 0.0,
            "source_out_sec": sec(dur_frames, fps),
            "media_duration_sec": round(real, 3),
            "duration_status": status,
        })
        rows.append(row)
        current += dur_frames
    return rows


def build_xml(rows: list[dict[str, Any]], fps: int, width: int, height: int, sequence_name: str) -> str:
    total = max([int(x.get("timeline_end_frame", 0)) for x in rows] + [1])
    clips = "\n".join(clip_xml(r, i, fps, width, height) for i, r in enumerate(rows, start=1))
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
  <sequence id="sequence-1">
    <name>{escape(sequence_name)}</name>
    <duration>{total}</duration>
    <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
    <timecode>
      <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
      <string>00:00:00:00</string>
      <frame>0</frame>
      <displayformat>NDF</displayformat>
    </timecode>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
            <width>{width}</width>
            <height>{height}</height>
            <anamorphic>FALSE</anamorphic>
            <pixelaspectratio>square</pixelaspectratio>
            <fielddominance>none</fielddominance>
          </samplecharacteristics>
        </format>
        <track>
{clips}
        </track>
      </video>
    </media>
  </sequence>
</xmeml>
'''


def main() -> None:
    p = argparse.ArgumentParser(description="111B Rescue XML exporter from non-empty rescue timeline.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--unknown-max-sec", type=float, default=0.8)
    p.add_argument("--preserve-unknown-duration", action="store_true")
    p.add_argument("--output-xml", default="")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "quality_music_rescue_xml_111b")

    tl = load_timeline(project)
    if not tl:
        res = {"ok": False, "error": "NO_NONEMPTY_TIMELINE", "message": "Run 110B first."}
        write_json(out / "rescue_xml_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    width, height = preset_size(a.preset)
    rows = sanitize(list(tl.get("items") or []), a.fps, a.unknown_max_sec, a.preserve_unknown_duration)

    output = Path(a.output_xml) if a.output_xml else project / "stt_quality_music_rescue_premiere_import.xml"
    xml = build_xml(rows, a.fps, width, height, f"STT QUALITY MUSIC RESCUE {a.style_profile}")
    output.write_text(xml, encoding="utf-8")
    (out / output.name).write_text(xml, encoding="utf-8")

    gaps = []
    prev = None
    for r in rows:
        st = int(r.get("timeline_start_frame", 0))
        en = int(r.get("timeline_end_frame", 0))
        if prev is not None and st != prev:
            gaps.append({"prev_end": prev, "start": st, "gap": st - prev})
        prev = en

    data = {
        "ok": True,
        "module": "111B_quality_music_rescue_xml",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "output_xml": str(output),
        "input_timeline_count": len(tl.get("items") or []),
        "timeline_count": len(rows),
        "timeline_seconds": rows[-1]["timeline_end_sec"] if rows else 0,
        "duration_stats": duration_stats(rows),
        "gap_count": len(gaps),
        "items": rows,
    }
    write_json(project / "stt_quality_music_rescue_xml_v2.json", data)
    write_json(out / "stt_quality_music_rescue_xml_v2.json", data)
    write_csv(out / "QUALITY_MUSIC_RESCUE_XML_111B.csv", rows, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "music_mode", "visual_bucket", "quality_score", "quality_class", "motion_class",
        "media_duration_sec", "duration_status", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "output_xml": str(output),
        "input_timeline_count": len(tl.get("items") or []),
        "timeline_count": len(rows),
        "timeline_seconds": rows[-1]["timeline_end_sec"] if rows else 0,
        "duration_stats": duration_stats(rows),
        "gap_count": len(gaps),
        "unknown_duration_count": sum(1 for r in rows if fnum(r.get("media_duration_sec"), 0) <= 0),
        "fix": "111B_quality_music_rescue_xml",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
