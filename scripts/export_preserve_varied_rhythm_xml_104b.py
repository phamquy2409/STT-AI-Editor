from rhythm_varied_common import *


_duration_cache: dict[str, float] = {}


def media_duration_cached(path: str | Path) -> float:
    key = str(path).lower()
    if key in _duration_cache:
        return _duration_cache[key]
    d = media_duration(path)
    _duration_cache[key] = d
    return d


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


def sanitize_to_frames(items: list[dict[str, Any]], fps: int, preserve_unknown_duration: bool) -> list[dict[str, Any]]:
    rows = []
    current = 0
    for item in items:
        path = str(item.get("file") or "")
        if not path or not Path(path).exists():
            continue
        if Path(path).suffix.lower() not in VIDEO_EXTS:
            continue

        desired_frames = max(1, fr(fnum(item.get("duration_sec"), 1.0), fps))
        real_dur = media_duration_cached(path)
        real_frames = fr(real_dur, fps) if real_dur > 0 else 0

        source_in = 0
        if real_frames > 0:
            dur_frames = min(desired_frames, max(1, real_frames - 1))
            file_duration_frames = max(real_frames, dur_frames + fps)
            duration_status = "measured_preserved"
        else:
            # Important for BRAW/unknown: do NOT force all to 1s.
            # Give Premiere a large virtual duration so long/short rhythm is preserved.
            dur_frames = desired_frames if preserve_unknown_duration else min(desired_frames, fps)
            file_duration_frames = max(dur_frames + fps * 10, fps * 60 * 60)
            duration_status = "unknown_virtual_duration_preserved" if preserve_unknown_duration else "unknown_short_safe"

        start = current
        end = start + dur_frames
        row = dict(item)
        row.update({
            "timeline_start_frame": start,
            "timeline_end_frame": end,
            "duration_frames": dur_frames,
            "source_in_frame": source_in,
            "source_out_frame": source_in + dur_frames,
            "file_duration_frames": file_duration_frames,
            "timeline_start_sec": sec(start, fps),
            "timeline_end_sec": sec(end, fps),
            "duration_sec": sec(dur_frames, fps),
            "source_in_sec": 0.0,
            "source_out_sec": sec(dur_frames, fps),
            "media_duration_sec": round(real_dur, 3),
            "duration_status": duration_status,
        })
        rows.append(row)
        current = end
    return rows


def clip_xml(item: dict[str, Any], idx: int, fps: int, width: int, height: int) -> str:
    path = str(item.get("file"))
    name = str(item.get("filename") or Path(path).name)
    start = int(item["timeline_start_frame"])
    end = int(item["timeline_end_frame"])
    src_in = int(item["source_in_frame"])
    src_out = int(item["source_out_frame"])
    file_duration = int(item["file_duration_frames"])
    file_id = f"file-{idx}"
    clipitem_duration = max(file_duration, src_out + fps)
    return f'''
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


def build_xml(items: list[dict[str, Any]], fps: int, width: int, height: int, sequence_name: str) -> str:
    total_frames = max([int(x.get("timeline_end_frame", 0)) for x in items] + [1])
    video = "\n".join(clip_xml(item, i, fps, width, height) for i, item in enumerate(items, start=1))
    return f'''<?xml version="1.0" encoding="UTF-8"?>
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
{video}
        </track>
      </video>
    </media>
  </sequence>
</xmeml>
'''


def main() -> None:
    p = argparse.ArgumentParser(description="104B preserve varied rhythm XML.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--preserve-unknown-duration", action="store_true")
    p.add_argument("--output-xml", default="")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "preserve_varied_rhythm_xml_104b")

    tl = read_json(project / "stt_cinematic_varied_rhythm_timeline_v1.json") or read_json(project / "stt_beat_voice_rhythm_timeline_v1.json")
    if not tl:
        res = {"ok": False, "error": "NO_VARIED_RHYTHM_TIMELINE", "message": "Run 103B first."}
        write_json(out / "preserve_varied_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    width, height = preset_size(a.preset)
    rows = sanitize_to_frames(list(tl.get("items") or []), a.fps, preserve_unknown_duration=a.preserve_unknown_duration)
    xml = build_xml(rows, a.fps, width, height, f"STT VARIED RHYTHM {a.style_profile}")

    output_xml = Path(a.output_xml) if a.output_xml else project / "stt_varied_rhythm_premiere_import.xml"
    output_xml.write_text(xml, encoding="utf-8")
    (out / output_xml.name).write_text(xml, encoding="utf-8")

    stats = duration_stats(rows)
    data = {
        "ok": True,
        "module": "104B_preserve_varied_rhythm_xml",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "output_xml": str(output_xml),
        "timeline_count": len(rows),
        "timeline_seconds": rows[-1]["timeline_end_sec"] if rows else 0,
        "duration_stats": stats,
        "items": rows,
    }
    write_json(project / "stt_varied_rhythm_xml_v1.json", data)
    write_json(out / "stt_varied_rhythm_xml_v1.json", data)
    write_csv(out / "VARIED_RHYTHM_XML_TIMELINE.csv", rows, [
        "index", "target_section", "filename", "timeline_start_frame", "timeline_end_frame", "duration_frames",
        "timeline_start_sec", "duration_sec", "rhythm_reason", "music_energy", "voice_hold",
        "media_duration_sec", "duration_status", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "output_xml": str(output_xml),
        "timeline_count": len(rows),
        "timeline_seconds": rows[-1]["timeline_end_sec"] if rows else 0,
        "duration_stats": stats,
        "unknown_duration_count": sum(1 for x in rows if fnum(x.get("media_duration_sec"), 0) <= 0),
        "fix": "104B_preserve_varied_rhythm_xml",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
