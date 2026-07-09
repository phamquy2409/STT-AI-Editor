from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from core.project import ProjectManager, STTProject


@dataclass
class PremiereExportConfig:
    sequence_name: str = "STT AI Rough Cut"
    sequence_fps: int = 25
    sequence_width: int = 3840
    sequence_height: int = 2160
    audio_sample_rate: int = 48000


class PremiereXMLExporter:
    # Build 007 Premiere Exporter.
    # Reads roughcut_plan.json and exports a better Premiere/FCP7 XML:
    # video track, linked stereo audio tracks, source pathurl, sequence duration.

    def __init__(
        self,
        project: STTProject,
        roughcut_json: str | Path | None = None,
        config: PremiereExportConfig | None = None,
    ) -> None:
        self.project = project
        self.roughcut_json = Path(roughcut_json) if roughcut_json else self._find_latest_roughcut_json()
        self.config = config or PremiereExportConfig()

    def export(self) -> dict[str, str]:
        if not self.roughcut_json.exists():
            raise FileNotFoundError(f"roughcut_plan.json not found: {self.roughcut_json}")

        items = json.loads(self.roughcut_json.read_text(encoding="utf-8"))

        output_dir = self.roughcut_json.parent
        xml_path = output_dir / "stt_ai_premiere_import.xml"
        info_path = output_dir / "premiere_import_note.txt"

        xml = self._build_xml(items)
        xml_path.write_text(xml, encoding="utf-8")

        info_path.write_text(
            self._build_note(xml_path),
            encoding="utf-8",
        )

        print("STT AI Premiere XML Exporter")
        print(f"Project: {self.project.name}")
        print(f"Roughcut: {self.roughcut_json}")
        print(f"XML: {xml_path}")
        print("-" * 60)
        print("PREMIERE XML EXPORT COMPLETE")
        print("Import in Premiere: File > Import > select XML")
        print("-" * 60)

        return {
            "xml": str(xml_path),
            "note": str(info_path),
            "roughcut_json": str(self.roughcut_json),
        }

    def _find_latest_roughcut_json(self) -> Path:
        exports_dir = self.project.paths.exports_dir
        candidates = sorted(
            exports_dir.glob("roughcut_*/roughcut_plan.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not candidates:
            return exports_dir / "roughcut_plan.json"

        return candidates[0]

    def _build_xml(self, items: list[dict]) -> str:
        fps = int(self.config.sequence_fps)

        def sec_to_frames(sec: float) -> int:
            return int(round(float(sec) * fps))

        total_frames = 0
        if items:
            total_frames = max(sec_to_frames(float(i["timeline_end_seconds"])) for i in items)

        video_clips = []
        audio1_clips = []
        audio2_clips = []

        for item in items:
            order = int(item["order"])
            file_id = f"file-{order}"
            video_id = f"clipitem-video-{order}"
            audio1_id = f"clipitem-audio1-{order}"
            audio2_id = f"clipitem-audio2-{order}"

            filename = self._xml_escape(item["video_filename"])
            video_path = str(item["video_path"])
            pathurl = self._pathurl(video_path)

            start = sec_to_frames(item["timeline_start_seconds"])
            end = sec_to_frames(item["timeline_end_seconds"])
            in_frame = sec_to_frames(item["source_start_seconds"])
            out_frame = sec_to_frames(item["source_end_seconds"])
            duration = max(1, end - start)

            file_block = f'''            <file id="{file_id}">
              <name>{filename}</name>
              <pathurl>{pathurl}</pathurl>
              <rate>
                <timebase>{fps}</timebase>
                <ntsc>FALSE</ntsc>
              </rate>
              <duration>{out_frame + 1}</duration>
              <media>
                <video>
                  <samplecharacteristics>
                    <rate>
                      <timebase>{fps}</timebase>
                      <ntsc>FALSE</ntsc>
                    </rate>
                    <width>{self.config.sequence_width}</width>
                    <height>{self.config.sequence_height}</height>
                  </samplecharacteristics>
                </video>
                <audio>
                  <samplecharacteristics>
                    <depth>16</depth>
                    <samplerate>{self.config.audio_sample_rate}</samplerate>
                  </samplecharacteristics>
                  <channelcount>2</channelcount>
                </audio>
              </media>
            </file>'''

            video_clips.append(f'''          <clipitem id="{video_id}">
            <masterclipid>masterclip-{order}</masterclipid>
            <name>{filename}</name>
            <enabled>TRUE</enabled>
            <duration>{duration}</duration>
            <rate>
              <timebase>{fps}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <start>{start}</start>
            <end>{end}</end>
            <in>{in_frame}</in>
            <out>{out_frame}</out>
{file_block}
            <link>
              <linkclipref>{video_id}</linkclipref>
              <mediatype>video</mediatype>
              <trackindex>1</trackindex>
              <clipindex>{order}</clipindex>
            </link>
            <link>
              <linkclipref>{audio1_id}</linkclipref>
              <mediatype>audio</mediatype>
              <trackindex>1</trackindex>
              <clipindex>{order}</clipindex>
              <groupindex>1</groupindex>
            </link>
            <link>
              <linkclipref>{audio2_id}</linkclipref>
              <mediatype>audio</mediatype>
              <trackindex>2</trackindex>
              <clipindex>{order}</clipindex>
              <groupindex>1</groupindex>
            </link>
          </clipitem>''')

            audio1_clips.append(self._audio_clip_xml(
                audio_id=audio1_id,
                video_id=video_id,
                filename=filename,
                file_id=file_id,
                start=start,
                end=end,
                in_frame=in_frame,
                out_frame=out_frame,
                duration=duration,
                order=order,
                track_index=1,
                source_channel=1,
            ))

            audio2_clips.append(self._audio_clip_xml(
                audio_id=audio2_id,
                video_id=video_id,
                filename=filename,
                file_id=file_id,
                start=start,
                end=end,
                in_frame=in_frame,
                out_frame=out_frame,
                duration=duration,
                order=order,
                track_index=2,
                source_channel=2,
            ))

        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<xmeml version="4">
  <sequence id="sequence-1">
    <name>{self._xml_escape(self.config.sequence_name)}</name>
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
            <width>{self.config.sequence_width}</width>
            <height>{self.config.sequence_height}</height>
            <anamorphic>FALSE</anamorphic>
            <pixelaspectratio>square</pixelaspectratio>
            <fielddominance>none</fielddominance>
          </samplecharacteristics>
        </format>
        <track>
{chr(10).join(video_clips)}
        </track>
      </video>
      <audio>
        <format>
          <samplecharacteristics>
            <depth>16</depth>
            <samplerate>{self.config.audio_sample_rate}</samplerate>
          </samplecharacteristics>
        </format>
        <track>
{chr(10).join(audio1_clips)}
        </track>
        <track>
{chr(10).join(audio2_clips)}
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>
'''
        return xml

    def _audio_clip_xml(
        self,
        audio_id: str,
        video_id: str,
        filename: str,
        file_id: str,
        start: int,
        end: int,
        in_frame: int,
        out_frame: int,
        duration: int,
        order: int,
        track_index: int,
        source_channel: int,
    ) -> str:
        fps = int(self.config.sequence_fps)

        return f'''          <clipitem id="{audio_id}">
            <masterclipid>masterclip-{order}</masterclipid>
            <name>{filename}</name>
            <enabled>TRUE</enabled>
            <duration>{duration}</duration>
            <rate>
              <timebase>{fps}</timebase>
              <ntsc>FALSE</ntsc>
            </rate>
            <start>{start}</start>
            <end>{end}</end>
            <in>{in_frame}</in>
            <out>{out_frame}</out>
            <file id="{file_id}"/>
            <sourcetrack>
              <mediatype>audio</mediatype>
              <trackindex>{source_channel}</trackindex>
            </sourcetrack>
            <link>
              <linkclipref>{video_id}</linkclipref>
              <mediatype>video</mediatype>
              <trackindex>1</trackindex>
              <clipindex>{order}</clipindex>
            </link>
            <link>
              <linkclipref>{audio_id}</linkclipref>
              <mediatype>audio</mediatype>
              <trackindex>{track_index}</trackindex>
              <clipindex>{order}</clipindex>
              <groupindex>1</groupindex>
            </link>
          </clipitem>'''

    @staticmethod
    def _pathurl(windows_path: str) -> str:
        text = Path(windows_path).as_posix()
        return "file://localhost/" + quote(text, safe="/:")

    @staticmethod
    def _xml_escape(text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _build_note(self, xml_path: Path) -> str:
        return "\\n".join([
            "STT AI Editor - Premiere Import Note",
            "=" * 45,
            f"Created: {datetime.now().isoformat(timespec='seconds')}",
            f"XML: {xml_path}",
            "",
            "Premiere:",
            "1. Open Premiere Pro.",
            "2. File > Import.",
            "3. Select stt_ai_premiere_import.xml.",
            "4. If media is offline, right click > Link Media and point to original source folder.",
            "",
            "Note:",
            "This exporter is Build 007. It includes video + stereo audio tracks.",
            "If Premiere imports wrong FPS/duration, we will adjust source-rate handling next.",
        ])


def export_premiere_xml_existing_project(
    project_root: str | Path,
    roughcut_json: str | Path | None = None,
    sequence_fps: int = 25,
    sequence_width: int = 3840,
    sequence_height: int = 2160,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    exporter = PremiereXMLExporter(
        project=project,
        roughcut_json=roughcut_json,
        config=PremiereExportConfig(
            sequence_fps=sequence_fps,
            sequence_width=sequence_width,
            sequence_height=sequence_height,
        ),
    )

    return exporter.export()
