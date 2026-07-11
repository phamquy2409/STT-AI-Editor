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


def outdir(project: Path) -> Path:
    p = project / "exports" / f"gapless_premiere_safe_xml_100c_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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


def ffprobe_duration(path: Path) -> float:
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0:
            val = (r.stdout or "").strip()
            if val:
                return float(val)
    except Exception:
        pass
    return 0.0


def cv2_duration(path: Path) -> float:
    try:
        import cv2  # type: ignore
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return 0.0
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        cap.release()
        if fps > 0 and frames > 0:
            return float(frames / fps)
    except Exception:
        pass
    return 0.0


_duration_cache: dict[str, float] = {}


def media_duration(path: str | Path) -> float:
    p = Path(path)
    key = str(p).lower()
    if key in _duration_cache:
        return _duration_cache[key]
    dur = ffprobe_duration(p)
    if dur <= 0:
        dur = cv2_duration(p)
    _duration_cache[key] = round(dur, 3) if dur > 0 else 0.0
    return _duration_cache[key]


def load_timeline(project: Path) -> dict[str, Any]:
    for name in [
        "stt_learned_inout_timeline_v1.json",
        "stt_profile_rhythm_timeline_v1.json",
        "stt_profile_story_timeline_v1.json",
    ]:
        d = read_json(project / name)
        if d:
            return d
    return {}


def sanitize_frame_contiguous_items(
    raw_items: list[dict[str, Any]],
    fps: int,
    unknown_duration_sec: float,
    min_duration_sec: float,
    max_duration_sec: float,
    force_source_zero: bool,
) -> list[dict[str, Any]]:
    safe = []
    current_frame = 0

    for raw in raw_items:
        path = str(raw.get("file") or "")
        if not path or not Path(path).exists():
            continue
        ext = Path(path).suffix.lower()
        if ext not in VIDEO_EXTS:
            continue

        filename = str(raw.get("filename") or Path(path).name)
        wanted_sec = fnum(raw.get("duration_sec"), fnum(raw.get("source_duration_sec"), 2.0))
        wanted_sec = max(min_duration_sec, min(max_duration_sec, wanted_sec))
        wanted_frames = max(1, fr(wanted_sec, fps))

        real_dur_sec = media_duration(path)
        real_dur_frames = fr(real_dur_sec, fps) if real_dur_sec > 0 else 0

        if force_source_zero:
            source_in_frames = 0
        else:
            source_in_frames = fr(max(0.0, fnum(raw.get("source_in_sec"), 0.0)), fps)

        if real_dur_frames > 0:
            source_in_frames = min(source_in_frames, max(0, real_dur_frames - fr(min_duration_sec, fps) - 1))
            possible_frames = max(1, real_dur_frames - source_in_frames - 1)
            dur_frames = min(wanted_frames, possible_frames)
            if dur_frames < fr(min_duration_sec, fps):
                source_in_frames = 0
                dur_frames = min(max(fr(min_duration_sec, fps), real_dur_frames - 1), fr(max_duration_sec, fps))
            file_duration_frames = max(real_dur_frames, source_in_frames + dur_frames + fps)
            status = "measured_gapless_clamped"
        else:
            source_in_frames = 0
            dur_frames = min(wanted_frames, max(1, fr(unknown_duration_sec, fps)))
            file_duration_frames = source_in_frames + dur_frames + fps
            status = "unknown_gapless_short_safe"

        start_frame = current_frame
        end_frame = start_frame + dur_frames
        source_out_frames = source_in_frames + dur_frames

        row = dict(raw)
        row.update({
            "filename": filename,
            "file": path,
            "timeline_start_frame": start_frame,
            "timeline_end_frame": end_frame,
            "duration_frames": dur_frames,
            "source_in_frame": source_in_frames,
            "source_out_frame": source_out_frames,
            "file_duration_frames": file_duration_frames,
            "timeline_start_sec": round(start_frame / fps, 3),
            "timeline_end_sec": round(end_frame / fps, 3),
            "duration_sec": round(dur_frames / fps, 3),
            "source_in_sec": round(source_in_frames / fps, 3),
            "source_out_sec": round(source_out_frames / fps, 3),
            "source_duration_sec": round(dur_frames / fps, 3),
            "media_duration_sec": round(real_dur_sec, 3),
            "duration_status": status,
        })
        safe.append(row)
        current_frame = end_frame

    return safe


def file_block(file_id: str, path: str, fps: int, width: int, height: int, file_duration_frames: int) -> str:
    name = Path(path).name
    return f'''
              <file id="{escape(file_id)}">
                <name>{escape(name)}</name>
                <pathurl>{escape(pathurl_for(path))}</pathurl>
                <rate>
                  <timebase>{fps}</timebase>
                  <ntsc>FALSE</ntsc>
                </rate>
                <duration>{max(file_duration_frames, 1)}</duration>
                <media>
                  <video>
                    <samplecharacteristics>
                      <rate>
                        <timebase>{fps}</timebase>
                        <ntsc>FALSE</ntsc>
                      </rate>
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
    duration_frames = int(item["file_duration_frames"])
    src_in = int(item["source_in_frame"])
    src_out = int(item["source_out_frame"])
    file_id = f"file-{idx}"

    clipitem_duration = max(duration_frames, src_out + fps)

    return f'''
          <clipitem id="clipitem-{idx}">
            <name>{escape(name)}</name>
            <enabled>TRUE</enabled>
            <duration>{clipitem_duration}</duration>
            <rate>
              <timebase>{fps}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <start>{start}</start>
            <end>{end}</end>
            <in>{src_in}</in>
            <out>{src_out}</out>
            {file_block(file_id, path, fps, width, height, clipitem_duration)}
            <sourcetrack>
              <mediatype>video</mediatype>
              <trackindex>1</trackindex>
            </sourcetrack>
            <fielddominance>none</fielddominance>
          </clipitem>'''


def build_xml(items: list[dict[str, Any]], sequence_name: str, fps: int, width: int, height: int) -> str:
    total_frames = max([int(x.get("timeline_end_frame", 0)) for x in items] + [1])
    video_clips = "\n".join(clip_xml(it, i, fps, width, height) for i, it in enumerate(items, start=1))
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
  <sequence id="sequence-1">
    <name>{escape(sequence_name)}</name>
    <duration>{total_frames}</duration>
    <rate>
      <timebase>{fps}</timebase>
      <ntsc>FALSE</ntsc>
    </rate>
    <timecode>
      <rate>
        <timebase>{fps}</timebase>
        <ntsc>FALSE</ntsc>
      </rate>
      <string>00:00:00:00</string>
      <frame>0</frame>
      <displayformat>NDF</displayformat>
    </timecode>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <rate>
              <timebase>{fps}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <width>{width}</width>
            <height>{height}</height>
            <anamorphic>FALSE</anamorphic>
            <pixelaspectratio>square</pixelaspectratio>
            <fielddominance>none</fielddominance>
          </samplecharacteristics>
        </format>
        <track>
{video_clips}
        </track>
      </video>
    </media>
  </sequence>
</xmeml>
'''


def main() -> None:
    p = argparse.ArgumentParser(description="100C gapless Premiere-safe video-only XML exporter.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--unknown-duration", type=float, default=1.0)
    p.add_argument("--min-duration", type=float, default=0.45)
    p.add_argument("--max-duration", type=float, default=3.0)
    p.add_argument("--force-source-zero", action="store_true")
    p.add_argument("--output-xml", default="")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project)

    tl = load_timeline(project)
    if not tl:
        res = {"ok": False, "error": "NO_TIMELINE", "message": "Run 097/098 first."}
        write_json(out / "gapless_premiere_safe_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    raw_items = list(tl.get("items") or [])
    width, height = preset_size(a.preset)
    safe_items = sanitize_frame_contiguous_items(
        raw_items=raw_items,
        fps=a.fps,
        unknown_duration_sec=a.unknown_duration,
        min_duration_sec=a.min_duration,
        max_duration_sec=a.max_duration,
        force_source_zero=a.force_source_zero,
    )

    output_xml = Path(a.output_xml) if a.output_xml else project / "stt_learned_profile_premiere_import_GAPLESS_SAFE.xml"
    output_xml.parent.mkdir(parents=True, exist_ok=True)

    xml = build_xml(
        safe_items,
        sequence_name=f"STT GAPLESS SAFE {a.style_profile}",
        fps=a.fps,
        width=width,
        height=height,
    )
    output_xml.write_text(xml, encoding="utf-8")
    (out / output_xml.name).write_text(xml, encoding="utf-8")

    total_frames = max([int(x.get("timeline_end_frame", 0)) for x in safe_items] + [0])
    summary = {
        "ok": True,
        "module": "100C_gapless_premiere_safe_xml",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project),
        "style_profile": a.style_profile,
        "preset": a.preset,
        "fps": a.fps,
        "width": width,
        "height": height,
        "timeline_count": len(safe_items),
        "timeline_frames": total_frames,
        "timeline_seconds": round(total_frames / a.fps, 3) if a.fps else 0,
        "force_source_zero": a.force_source_zero,
        "output_xml": str(output_xml),
        "items": safe_items,
    }
    write_json(project / "stt_gapless_safe_timeline_v1.json", summary)
    write_json(out / "stt_gapless_safe_timeline_v1.json", summary)
    write_csv(out / "GAPLESS_SAFE_TIMELINE.csv", safe_items, [
        "index", "target_section", "filename",
        "timeline_start_frame", "timeline_end_frame", "duration_frames",
        "source_in_frame", "source_out_frame", "file_duration_frames",
        "timeline_start_sec", "duration_sec", "source_in_sec", "source_out_sec",
        "media_duration_sec", "duration_status", "file"
    ])

    gaps = []
    prev = None
    for item in safe_items:
        st = int(item["timeline_start_frame"])
        en = int(item["timeline_end_frame"])
        if prev is not None and st != prev:
            gaps.append({"prev_end": prev, "start": st, "gap": st - prev})
        prev = en

    res = {
        "ok": True,
        "report_dir": str(out),
        "output_xml": str(output_xml),
        "timeline_count": len(safe_items),
        "timeline_frames": total_frames,
        "timeline_seconds": round(total_frames / a.fps, 3) if a.fps else 0,
        "gap_count": len(gaps),
        "measured_duration_count": sum(1 for x in safe_items if fnum(x.get("media_duration_sec"), 0) > 0),
        "unknown_duration_count": sum(1 for x in safe_items if fnum(x.get("media_duration_sec"), 0) <= 0),
        "fix": "100C_gapless_premiere_safe_xml",
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
