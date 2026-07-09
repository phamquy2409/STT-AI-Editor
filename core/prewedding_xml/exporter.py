
from __future__ import annotations

import html
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


PREWEDDING_XML_PRESETS: dict[str, dict[str, Any]] = {
    "vertical_1080_25p": {
        "label": "Vertical 1080x1920 25p",
        "width": 1080,
        "height": 1920,
        "fps": 25,
        "timebase": 25,
        "ntsc": "FALSE",
        "fielddominance": "none",
        "pixelaspectratio": "square",
        "audio_channels": 2,
    },
    "vertical_1080_30p": {
        "label": "Vertical 1080x1920 30p",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "timebase": 30,
        "ntsc": "FALSE",
        "fielddominance": "none",
        "pixelaspectratio": "square",
        "audio_channels": 2,
    },
    "fhd_1080_25p": {
        "label": "FHD 1920x1080 25p",
        "width": 1920,
        "height": 1080,
        "fps": 25,
        "timebase": 25,
        "ntsc": "FALSE",
        "fielddominance": "none",
        "pixelaspectratio": "square",
        "audio_channels": 2,
    },
    "uhd_4k_25p": {
        "label": "UHD 3840x2160 25p",
        "width": 3840,
        "height": 2160,
        "fps": 25,
        "timebase": 25,
        "ntsc": "FALSE",
        "fielddominance": "none",
        "pixelaspectratio": "square",
        "audio_channels": 2,
    },
}


@dataclass
class PreweddingXMLConfig:
    project_root: str = DEFAULT_PROJECT_ROOT
    selection_path: str | None = None
    preset: str | None = None
    sequence_name: str | None = None
    open_folder: bool = True


class PreweddingXMLExporter:
    # Module 049.
    # Exports Premiere-compatible FCP7 XML from Module 047 prewedding selection.
    #
    # Input:
    # - stt_prewedding_selection_v1.json
    #
    # Output:
    # - stt_prewedding_premiere_import.xml
    # - Premiere bridge/package files
    #
    # Notes:
    # - Reel intents default to vertical_1080_25p.
    # - Cinematic/location intents default to fhd_1080_25p.
    # - Audio is exported dual mono style: A1=L, A2=R, to avoid losing right channel.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()

        self.project_selection_path = self.project_root / "stt_prewedding_selection_v1.json"
        self.appdata_selection_path = self.appdata_dir / "stt_prewedding_selection_v1.json"

        self.project_xml_path = self.project_root / "stt_prewedding_premiere_import.xml"
        self.appdata_latest_xml = self.appdata_dir / "premiere_latest_xml.txt"
        self.appdata_latest_xml_json = self.appdata_dir / "premiere_latest_xml.json"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    def export(
        self,
        selection_path: str | Path | None = None,
        preset: str | None = None,
        sequence_name: str | None = None,
        open_folder: bool = True,
    ) -> dict[str, Any]:
        selection_file = Path(selection_path) if selection_path else self.find_selection_file()

        if not selection_file or not selection_file.exists():
            raise FileNotFoundError(
                "Không tìm thấy stt_prewedding_selection_v1.json.\n"
                "Hãy chạy trước: python scripts/build_prewedding_selection.py --intent prewedding_reel_60s"
            )

        selection = self.load_json(selection_file)
        timeline = selection.get("timeline") or []

        if not timeline:
            raise RuntimeError(
                "Selection không có timeline.\n"
                "Hãy chạy lại Module 047: build_prewedding_selection.py"
            )

        intent = str(selection.get("intent") or "prewedding_reel_60s")
        preset_name = preset or self.default_preset_for_selection(selection)

        if preset_name not in PREWEDDING_XML_PRESETS:
            raise ValueError(
                f"Unknown preset: {preset_name}. Available: {', '.join(sorted(PREWEDDING_XML_PRESETS))}"
            )

        preset_data = PREWEDDING_XML_PRESETS[preset_name]
        seq_name = sequence_name or self.default_sequence_name(selection, preset_name)

        clean_timeline = self.clean_timeline(timeline, preset_data)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = self.exports_dir / f"prewedding_xml_{intent}_{preset_name}_{stamp}"
        out_dir.mkdir(parents=True, exist_ok=True)

        xml_path = out_dir / "stt_prewedding_premiere_import.xml"
        xml_text = self.render_xml(clean_timeline, selection, preset_data, seq_name)
        xml_path.write_text(xml_text, encoding="utf-8")

        self.project_xml_path.write_text(xml_text, encoding="utf-8")

        readme_path = out_dir / "README_IMPORT_PREMIERE.txt"
        readme_path.write_text(self.render_readme(selection, preset_name, preset_data, xml_path), encoding="utf-8")

        html_path = out_dir / "PREWEDDING_XML_IMPORT_STEPS.html"
        html_path.write_text(self.render_html(selection, preset_name, preset_data, xml_path), encoding="utf-8")

        jsx_path = out_dir / "premiere_import_prewedding_xml.jsx"
        jsx_path.write_text(self.render_jsx(xml_path), encoding="utf-8")

        copy_bat = out_dir / "Copy_XML_Path_To_Clipboard.bat"
        copy_bat.write_text(
            f'@echo off\necho {xml_path} | clip\necho XML path copied:\necho {xml_path}\npause\n',
            encoding="utf-8",
        )

        open_bat = out_dir / "Open_This_Folder.bat"
        open_bat.write_text(f'@echo off\nstart "" "{out_dir}"\n', encoding="utf-8")

        pointer = self.update_premiere_pointer(xml_path, source="module_049_prewedding_xml_exporter")

        manifest = {
            "ok": True,
            "module": "049_prewedding_xml_exporter",
            "version": "0.49",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(self.project_root),
            "selection_path": str(selection_file),
            "intent": intent,
            "sequence_name": seq_name,
            "preset": preset_name,
            "preset_data": preset_data,
            "timeline_count": len(clean_timeline),
            "timeline_duration_seconds": round(sum(float(x.get("timeline_duration", 0)) for x in clean_timeline), 3),
            "xml": str(xml_path),
            "project_xml": str(self.project_xml_path),
            "readme": str(readme_path),
            "html": str(html_path),
            "jsx": str(jsx_path),
            "premiere_pointer": pointer,
            "audio_note": "Dual mono safe: A1 = Left, A2 = Right.",
            "import_steps": [
                "Premiere Pro > File > Import > chọn stt_prewedding_premiere_import.xml",
                "Hoặc dùng Premiere panel STT AI Editor > Refresh Latest XML > Import Latest XML",
            ],
        }

        manifest_path = out_dir / "prewedding_xml_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        result = {
            "ok": True,
            "intent": intent,
            "preset": preset_name,
            "sequence_name": seq_name,
            "xml": str(xml_path),
            "project_xml": str(self.project_xml_path),
            "report_dir": str(out_dir),
            "timeline_count": len(clean_timeline),
            "duration": manifest["timeline_duration_seconds"],
            "readme": str(readme_path),
            "html": str(html_path),
            "jsx": str(jsx_path),
            "manifest": str(manifest_path),
            "premiere_pointer": pointer,
        }

        (out_dir / "prewedding_xml_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if open_folder:
            try:
                os.startfile(out_dir)
            except Exception:
                pass

        return result

    def find_selection_file(self) -> Path | None:
        for path in [self.project_selection_path, self.appdata_selection_path]:
            if path.exists():
                return path

        if self.exports_dir.exists():
            files = [
                p for p in self.exports_dir.glob("**/stt_prewedding_selection_v1.json")
                if p.is_file() and "_archive" not in p.parts
            ]
            if files:
                return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        return None

    @staticmethod
    def load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def default_preset_for_selection(selection: dict[str, Any]) -> str:
        intent = str(selection.get("intent") or "").lower()
        aspect = str(selection.get("aspect") or "").lower()

        if "reel" in intent or aspect == "9:16":
            return "vertical_1080_25p"

        if "cinematic" in intent or "location" in intent:
            return "fhd_1080_25p"

        return "vertical_1080_25p"

    @staticmethod
    def default_sequence_name(selection: dict[str, Any], preset_name: str) -> str:
        intent = str(selection.get("intent") or "prewedding").replace("_", " ").title()
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        return f"STT {intent} {preset_name} {stamp}"

    @staticmethod
    def clean_timeline(timeline: list[dict[str, Any]], preset_data: dict[str, Any]) -> list[dict[str, Any]]:
        fps = float(preset_data["fps"])
        clean = []
        cursor = 0.0

        for index, item in enumerate(timeline, start=1):
            file_path = str(item.get("file") or item.get("path") or "").strip()

            # Keep item even if path is not absolute; Premiere can relink later.
            source_start = PreweddingXMLExporter.to_float(item.get("source_start"), 0.0)
            duration = PreweddingXMLExporter.to_float(item.get("timeline_duration"), 0.0)

            if duration <= 0:
                source_end = PreweddingXMLExporter.to_float(item.get("source_end"), source_start + 2.5)
                duration = max(1.0, source_end - source_start)

            # Snap to frames.
            source_start = PreweddingXMLExporter.frames_to_seconds(
                PreweddingXMLExporter.seconds_to_frames(source_start, fps), fps
            )
            duration = PreweddingXMLExporter.frames_to_seconds(
                max(1, PreweddingXMLExporter.seconds_to_frames(duration, fps)), fps
            )

            clean_item = dict(item)
            clean_item["timeline_index"] = index
            clean_item["timeline_start"] = round(cursor, 6)
            clean_item["timeline_duration"] = round(duration, 6)
            clean_item["timeline_end"] = round(cursor + duration, 6)
            clean_item["source_start"] = round(source_start, 6)
            clean_item["source_end"] = round(source_start + duration, 6)
            clean_item["file"] = file_path

            clean.append(clean_item)
            cursor += duration

        return clean

    @staticmethod
    def to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def seconds_to_frames(seconds: float, fps: float) -> int:
        return int(round(float(seconds) * float(fps)))

    @staticmethod
    def frames_to_seconds(frames: int, fps: float) -> float:
        if fps <= 0:
            return 0.0
        return float(frames) / float(fps)

    @staticmethod
    def path_to_url(path_text: str) -> str:
        if not path_text:
            return ""

        p = Path(path_text)
        raw = str(p.resolve() if p.exists() else p)
        raw = raw.replace("\\", "/")

        if len(raw) >= 2 and raw[1] == ":":
            # Windows drive.
            return "file://localhost/" + quote(raw)
        if raw.startswith("//"):
            return "file:" + quote(raw)
        return "file://localhost/" + quote(raw)

    def render_xml(
        self,
        timeline: list[dict[str, Any]],
        selection: dict[str, Any],
        preset: dict[str, Any],
        sequence_name: str,
    ) -> str:
        fps = float(preset["fps"])
        timebase = int(preset["timebase"])
        width = int(preset["width"])
        height = int(preset["height"])

        total_frames = sum(
            max(1, self.seconds_to_frames(float(item.get("timeline_duration", 0)), fps))
            for item in timeline
        )

        seq_id = "sequence-" + uuid.uuid4().hex[:12]
        lines: list[str] = []

        lines += [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE xmeml>',
            '<xmeml version="5">',
            f'  <sequence id="{seq_id}">',
            f'    <name>{self.x(sequence_name)}</name>',
            f'    <duration>{total_frames}</duration>',
            '    <rate>',
            f'      <timebase>{timebase}</timebase>',
            f'      <ntsc>{preset["ntsc"]}</ntsc>',
            '    </rate>',
            '    <media>',
            '      <video>',
            '        <format>',
            '          <samplecharacteristics>',
            '            <rate>',
            f'              <timebase>{timebase}</timebase>',
            f'              <ntsc>{preset["ntsc"]}</ntsc>',
            '            </rate>',
            f'            <width>{width}</width>',
            f'            <height>{height}</height>',
            f'            <anamorphic>FALSE</anamorphic>',
            f'            <pixelaspectratio>{preset["pixelaspectratio"]}</pixelaspectratio>',
            f'            <fielddominance>{preset["fielddominance"]}</fielddominance>',
            '          </samplecharacteristics>',
            '        </format>',
            '        <track>',
        ]

        cursor_frames = 0
        file_id_map: dict[str, str] = {}

        for idx, item in enumerate(timeline, start=1):
            file_path = str(item.get("file") or "")
            file_id = file_id_map.get(file_path)
            if not file_id:
                file_id = f"file-{idx}-{uuid.uuid4().hex[:8]}"
                file_id_map[file_path] = file_id

            clip_id = f"clipitem-v-{idx}"
            name = Path(file_path).name if file_path else f"prewedding_clip_{idx}"
            duration_frames = max(1, self.seconds_to_frames(float(item.get("timeline_duration", 0)), fps))
            source_start_frames = max(0, self.seconds_to_frames(float(item.get("source_start", 0)), fps))
            source_end_frames = source_start_frames + duration_frames
            start_frames = cursor_frames
            end_frames = cursor_frames + duration_frames
            cursor_frames = end_frames

            lines += [
                f'          <clipitem id="{clip_id}">',
                f'            <name>{self.x(name)}</name>',
                f'            <duration>{duration_frames}</duration>',
                '            <rate>',
                f'              <timebase>{timebase}</timebase>',
                f'              <ntsc>{preset["ntsc"]}</ntsc>',
                '            </rate>',
                f'            <start>{start_frames}</start>',
                f'            <end>{end_frames}</end>',
                f'            <in>{source_start_frames}</in>',
                f'            <out>{source_end_frames}</out>',
                '            <enabled>TRUE</enabled>',
                '            <file id="' + file_id + '">',
                f'              <name>{self.x(name)}</name>',
                f'              <pathurl>{self.x(self.path_to_url(file_path))}</pathurl>',
                '              <rate>',
                f'                <timebase>{timebase}</timebase>',
                f'                <ntsc>{preset["ntsc"]}</ntsc>',
                '              </rate>',
                f'              <duration>{max(duration_frames, source_end_frames)}</duration>',
                '              <media>',
                '                <video>',
                '                  <samplecharacteristics>',
                '                    <rate>',
                f'                      <timebase>{timebase}</timebase>',
                f'                      <ntsc>{preset["ntsc"]}</ntsc>',
                '                    </rate>',
                f'                    <width>{width}</width>',
                f'                    <height>{height}</height>',
                f'                    <anamorphic>FALSE</anamorphic>',
                f'                    <pixelaspectratio>{preset["pixelaspectratio"]}</pixelaspectratio>',
                f'                    <fielddominance>{preset["fielddominance"]}</fielddominance>',
                '                  </samplecharacteristics>',
                '                </video>',
                '                <audio>',
                '                  <samplecharacteristics>',
                '                    <depth>16</depth>',
                '                    <samplerate>48000</samplerate>',
                '                  </samplecharacteristics>',
                '                  <channelcount>2</channelcount>',
                '                </audio>',
                '              </media>',
                '            </file>',
                '            <link>',
                f'              <linkclipref>{clip_id}</linkclipref>',
                '              <mediatype>video</mediatype>',
                '              <trackindex>1</trackindex>',
                f'              <clipindex>{idx}</clipindex>',
                '            </link>',
                '            <link>',
                f'              <linkclipref>clipitem-a1-{idx}</linkclipref>',
                '              <mediatype>audio</mediatype>',
                '              <trackindex>1</trackindex>',
                f'              <clipindex>{idx}</clipindex>',
                '              <groupindex>1</groupindex>',
                '            </link>',
                '            <link>',
                f'              <linkclipref>clipitem-a2-{idx}</linkclipref>',
                '              <mediatype>audio</mediatype>',
                '              <trackindex>2</trackindex>',
                f'              <clipindex>{idx}</clipindex>',
                '              <groupindex>1</groupindex>',
                '            </link>',
                '          </clipitem>',
            ]

        lines += [
            '        </track>',
            '      </video>',
            '      <audio>',
            '        <format>',
            '          <samplecharacteristics>',
            '            <depth>16</depth>',
            '            <samplerate>48000</samplerate>',
            '          </samplecharacteristics>',
            '        </format>',
        ]

        for audio_track_index in [1, 2]:
            lines.append('        <track>')
            cursor_frames = 0

            for idx, item in enumerate(timeline, start=1):
                file_path = str(item.get("file") or "")
                file_id = file_id_map.get(file_path, f"file-{idx}")
                name = Path(file_path).name if file_path else f"prewedding_clip_{idx}"
                duration_frames = max(1, self.seconds_to_frames(float(item.get("timeline_duration", 0)), fps))
                source_start_frames = max(0, self.seconds_to_frames(float(item.get("source_start", 0)), fps))
                source_end_frames = source_start_frames + duration_frames
                start_frames = cursor_frames
                end_frames = cursor_frames + duration_frames
                cursor_frames = end_frames

                clip_id = f"clipitem-a{audio_track_index}-{idx}"
                channel_index = audio_track_index

                lines += [
                    f'          <clipitem id="{clip_id}">',
                    f'            <name>{self.x(name)} A{audio_track_index}</name>',
                    f'            <duration>{duration_frames}</duration>',
                    '            <rate>',
                    f'              <timebase>{timebase}</timebase>',
                    f'              <ntsc>{preset["ntsc"]}</ntsc>',
                    '            </rate>',
                    f'            <start>{start_frames}</start>',
                    f'            <end>{end_frames}</end>',
                    f'            <in>{source_start_frames}</in>',
                    f'            <out>{source_end_frames}</out>',
                    '            <enabled>TRUE</enabled>',
                    f'            <file id="{file_id}"/>',
                    '            <sourcetrack>',
                    '              <mediatype>audio</mediatype>',
                    f'              <trackindex>{channel_index}</trackindex>',
                    '            </sourcetrack>',
                    '            <link>',
                    f'              <linkclipref>clipitem-v-{idx}</linkclipref>',
                    '              <mediatype>video</mediatype>',
                    '              <trackindex>1</trackindex>',
                    f'              <clipindex>{idx}</clipindex>',
                    '            </link>',
                    '            <link>',
                    f'              <linkclipref>{clip_id}</linkclipref>',
                    '              <mediatype>audio</mediatype>',
                    f'              <trackindex>{audio_track_index}</trackindex>',
                    f'              <clipindex>{idx}</clipindex>',
                    '              <groupindex>1</groupindex>',
                    '            </link>',
                    '          </clipitem>',
                ]

            lines.append('        </track>')

        lines += [
            '      </audio>',
            '    </media>',
            '  </sequence>',
            '</xmeml>',
        ]

        return "\n".join(lines) + "\n"

    @staticmethod
    def x(value: Any) -> str:
        return html.escape(str(value), quote=True)

    def update_premiere_pointer(self, xml_path: Path, source: str) -> dict[str, Any]:
        self.appdata_dir.mkdir(parents=True, exist_ok=True)
        self.appdata_latest_xml.write_text(str(xml_path), encoding="utf-8")

        data = {
            "ok": True,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "source": source,
            "project_root": str(self.project_root),
            "xml": str(xml_path),
            "xml_exists": xml_path.exists(),
            "xml_size_bytes": xml_path.stat().st_size if xml_path.exists() else 0,
            "pointer_txt": str(self.appdata_latest_xml),
            "pointer_json": str(self.appdata_latest_xml_json),
        }

        self.appdata_latest_xml_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    @staticmethod
    def render_readme(
        selection: dict[str, Any],
        preset_name: str,
        preset: dict[str, Any],
        xml_path: Path,
    ) -> str:
        return "\n".join([
            "STT AI Editor - Prewedding Premiere XML",
            "=" * 72,
            "",
            f"Intent: {selection.get('intent')}",
            f"Preset: {preset_name} / {preset.get('label')}",
            f"XML: {xml_path}",
            "",
            "IMPORT VÀO PREMIERE:",
            "",
            "Cách 1:",
            "Premiere Pro > File > Import > chọn:",
            str(xml_path),
            "",
            "Cách 2:",
            "Premiere > Window > Extensions > STT AI Editor",
            "Bấm Refresh Latest XML",
            "Bấm Import Latest XML",
            "",
            "Lưu ý:",
            "- Reel prewedding mặc định 9:16 vertical 1080x1920.",
            "- Audio giữ dual mono an toàn A1=L, A2=R.",
            "- Nếu Premiere hỏi relink, chọn đúng folder source.",
            "",
        ])

    @staticmethod
    def render_html(
        selection: dict[str, Any],
        preset_name: str,
        preset: dict[str, Any],
        xml_path: Path,
    ) -> str:
        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT Prewedding XML Import</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111; color: #eee; margin: 32px; line-height: 1.55; }}
.card {{ max-width: 1000px; background: #181818; border: 1px solid #333; border-radius: 16px; padding: 24px; }}
.badge {{ display: inline-block; border: 1px solid #666; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
code {{ display:block; background:#000; padding:12px; border-radius:10px; overflow-wrap:anywhere; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">Module 049</div>
  <h1>Prewedding Premiere XML</h1>
  <p>Intent: <b>{html.escape(str(selection.get("intent")))}</b></p>
  <p>Preset: <b>{html.escape(preset_name)}</b> / {html.escape(str(preset.get("label")))}</p>
  <p>Import XML này vào Premiere:</p>
  <code>{html.escape(str(xml_path))}</code>

  <h2>Cách import</h2>
  <ol>
    <li>Premiere Pro &gt; File &gt; Import</li>
    <li>Chọn file XML trên</li>
    <li>Hoặc dùng STT AI Editor panel trong Premiere: Refresh Latest XML &gt; Import Latest XML</li>
  </ol>

  <p>Audio giữ dual mono an toàn: A1=L, A2=R.</p>
</div>
</body>
</html>
'''

    @staticmethod
    def render_jsx(xml_path: Path) -> str:
        xml_js = str(xml_path).replace("\\", "/").replace('"', '\\"')
        return f'''(function () {{
    var xmlFile = new File("{xml_js}");
    if (!xmlFile.exists) {{
        alert("Không thấy XML:\\n" + xmlFile.fsName);
        return;
    }}
    try {{
        if (!app.project) app.newProject();
        app.project.importFiles([xmlFile.fsName], false, app.project.rootItem, false);
        alert("Đã gửi lệnh import prewedding XML vào Premiere.");
    }} catch (e) {{
        alert("Import lỗi. Dùng File > Import thủ công.\\n\\n" + e);
    }}
}})();
'''


def export_prewedding_xml(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    selection_path: str | Path | None = None,
    preset: str | None = None,
    sequence_name: str | None = None,
    open_folder: bool = True,
) -> dict[str, Any]:
    return PreweddingXMLExporter(project_root=project_root).export(
        selection_path=selection_path,
        preset=preset,
        sequence_name=sequence_name,
        open_folder=open_folder,
    )
