from music_director_common import *


_dur_cache: dict[str, float] = {}


def media_duration_cached(path: str | Path) -> float:
    key = str(path).lower()
    if key in _dur_cache:
        return _dur_cache[key]
    d = media_duration(path)
    _dur_cache[key] = d
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


def sanitize(items: list[dict[str, Any]], fps: int, preserve_unknown: bool) -> list[dict[str, Any]]:
    rows = []
    current = 0
    for it in items:
        path = str(it.get("file") or "")
        if not path or not Path(path).exists():
            continue
        if Path(path).suffix.lower() not in VIDEO_EXTS:
            continue
        desired = max(1, fr(fnum(it.get("duration_sec"), 1.0), fps))
        real = media_duration_cached(path)
        real_frames = fr(real, fps) if real > 0 else 0
        if real_frames > 0:
            dur_frames = min(desired, max(1, real_frames - 1))
            file_duration = max(real_frames, dur_frames + fps)
            status = "measured"
        else:
            dur_frames = desired if preserve_unknown else min(desired, fps)
            file_duration = max(dur_frames + fps * 10, fps * 60 * 60)
            status = "unknown_virtual_preserved" if preserve_unknown else "unknown_short"

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
    p = argparse.ArgumentParser(description="107 export music directed XML.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--style-profile", default="intimate_7_8min")
    p.add_argument("--preset", default="horizontal_4k")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--preserve-unknown-duration", action="store_true")
    p.add_argument("--output-xml", default="")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "music_directed_xml_107")

    tl = read_json(project / "stt_music_directed_timeline_v1.json")
    if not tl:
        res = {"ok": False, "error": "NO_MUSIC_DIRECTED_TIMELINE", "message": "Run 106 first."}
        write_json(out / "music_directed_xml_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if not a.no_open:
            open_path(out)
        return

    width, height = preset_size(a.preset)
    rows = sanitize(list(tl.get("items") or []), a.fps, a.preserve_unknown_duration)
    xml = build_xml(rows, a.fps, width, height, f"STT MUSIC DIRECTED {a.style_profile}")

    output = Path(a.output_xml) if a.output_xml else project / "stt_music_directed_premiere_import.xml"
    output.write_text(xml, encoding="utf-8")
    (out / output.name).write_text(xml, encoding="utf-8")

    data = {
        "ok": True,
        "module": "107_music_directed_xml",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "output_xml": str(output),
        "timeline_count": len(rows),
        "timeline_seconds": rows[-1]["timeline_end_sec"] if rows else 0,
        "duration_stats": duration_stats(rows),
        "items": rows,
    }
    write_json(project / "stt_music_directed_xml_v1.json", data)
    write_json(out / "stt_music_directed_xml_v1.json", data)
    write_csv(out / "MUSIC_DIRECTED_XML_TIMELINE.csv", rows, [
        "index", "target_section", "filename", "timeline_start_sec", "duration_sec", "timeline_end_sec",
        "music_mode", "rhythm_reason", "media_duration_sec", "duration_status", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "output_xml": str(output),
        "timeline_count": len(rows),
        "timeline_seconds": rows[-1]["timeline_end_sec"] if rows else 0,
        "duration_stats": duration_stats(rows),
        "mode_counts": tl.get("mode_counts"),
        "unknown_duration_count": sum(1 for r in rows if fnum(r.get("media_duration_sec"), 0) <= 0),
        "fix": "107_music_directed_xml",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
