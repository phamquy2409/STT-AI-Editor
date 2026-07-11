from rhythm_common import *


_duration_cache: dict[str, float] = {}


def media_duration(path: str | Path) -> float:
    key = str(path).lower()
    if key in _duration_cache:
        return _duration_cache[key]
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0 and (r.stdout or "").strip():
            _duration_cache[key] = float((r.stdout or "").strip())
            return _duration_cache[key]
    except Exception:
        pass
    _duration_cache[key] = 0.0
    return 0.0


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


def clip_xml(item: dict[str, Any], idx: int, fps: int, width: int, height: int, current_frame: int) -> tuple[str, int, dict[str, Any]]:
    path = str(item.get("file") or "")
    name = str(item.get("filename") or Path(path).name)
    dur_frames = max(1, fr(fnum(item.get("duration_sec"), 1.0), fps))
    real_dur = media_duration(path)
    real_frames = fr(real_dur, fps) if real_dur > 0 else 0

    if real_frames > 0:
        dur_frames = min(dur_frames, max(1, real_frames - 1))
        file_duration_frames = max(real_frames, dur_frames + fps)
    else:
        dur_frames = min(dur_frames, fr(1.0, fps))
        file_duration_frames = dur_frames + fps

    start = current_frame
    end = start + dur_frames
    src_in = 0
    src_out = dur_frames
    file_id = f"file-{idx}"
    clipitem_duration = max(file_duration_frames, src_out + fps)
    xml = f'''
          <clipitem id="clipitem-{idx}">
            <name>{escape(name)}</name>
            <enabled>TRUE</enabled>
            <duration>{clipitem_duration}</duration>
            <rate><timebase>{fps}</timebase><ntsc>FALSE</ntsc></rate>
            <start>{start}</start>
            <end>{end}</end>
            <in>{src_in}</in>
            <out>{src_out}</out>
            {file_block(file_id, path, fps, width, height, clipitem_duration)}
            <sourcetrack><mediatype>video</mediatype><trackindex>1</trackindex></sourcetrack>
            <fielddominance>none</fielddominance>
          </clipitem>'''
    row = dict(item)
    row.update({
        "timeline_start_frame": start,
        "timeline_end_frame": end,
        "duration_frames": dur_frames,
        "timeline_start_sec": sec(start, fps),
        "timeline_end_sec": sec(end, fps),
        "duration_sec": sec(dur_frames, fps),
        "source_in_sec": 0.0,
        "source_out_sec": sec(dur_frames, fps),
        "media_duration_sec": round(real_dur, 3),
    })
    return xml, end, row


def build_xml(items: list[dict[str, Any]], fps: int, width: int, height: int, sequence_name: str) -> tuple[str, list[dict[str, Any]]]:
    current = 0
    xmls = []
    rows = []
    idx = 1
    for item in items:
        path = str(item.get("file") or "")
        if not path or not Path(path).exists():
            continue
        if Path(path).suffix.lower() not in VIDEO_EXTS:
            continue
        x, current, row = clip_xml(item, idx, fps, width, height, current)
        xmls.append(x)
        rows.append(row)
        idx += 1
    total_frames = max(1, current)
    video_clips = "\n".join(xmls)
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
  <sequence id="sequence-1">
    <name>{escape(sequence_name)}</name>
    <duration>{total_frames}</duration>
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
{video_clips}
        </track>
      </video>
    </media>
  </sequence>
</xmeml>
'''
    return xml, rows


def main() -> None:
    p = argparse.ArgumentParser(description="104 Export beat/voice gapless XML.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--output-xml", default="")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "beat_voice_gapless_xml_104")
    tl = read_json(project / "stt_beat_voice_rhythm_timeline_v1.json")
    if not tl:
        res = {"ok": False, "error": "NO_BEAT_VOICE_TIMELINE", "message": "Run 103 first."}
        write_json(out / "beat_voice_xml_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    width, height = preset_size(a.preset)
    xml, rows = build_xml(list(tl.get("items") or []), a.fps, width, height, f"STT BEAT VOICE {a.style_profile}")
    output_xml = Path(a.output_xml) if a.output_xml else project / "stt_beat_voice_gapless_premiere_import.xml"
    output_xml.write_text(xml, encoding="utf-8")
    (out / output_xml.name).write_text(xml, encoding="utf-8")

    write_csv(out / "BEAT_VOICE_XML_TIMELINE.csv", rows, [
        "index", "target_section", "filename", "timeline_start_frame", "timeline_end_frame", "duration_frames",
        "timeline_start_sec", "duration_sec", "rhythm_reason", "snap_reason", "music_energy", "voice_hold", "media_duration_sec", "file"
    ])
    data = {
        "ok": True,
        "module": "104_beat_voice_gapless_xml",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "output_xml": str(output_xml),
        "timeline_count": len(rows),
        "timeline_seconds": rows[-1]["timeline_end_sec"] if rows else 0,
        "items": rows,
    }
    write_json(project / "stt_beat_voice_gapless_xml_v1.json", data)
    write_json(out / "stt_beat_voice_gapless_xml_v1.json", data)

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "output_xml": str(output_xml),
        "timeline_count": len(rows),
        "timeline_seconds": rows[-1]["timeline_end_sec"] if rows else 0,
        "fix": "104_beat_voice_gapless_xml",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
