
from __future__ import annotations

import html
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class PremiereXMLValidationConfig:
    xml_path: str
    check_media_exists: bool = True
    max_missing_preview: int = 30


class PremiereXMLValidator:
    # Module 038.
    # Safe XML checker before importing into Premiere.
    #
    # It does not edit the XML.

    def __init__(
        self,
        xml_path: str | Path,
        check_media_exists: bool = True,
        max_missing_preview: int = 30,
    ) -> None:
        self.xml_path = Path(xml_path)
        self.check_media_exists = check_media_exists
        self.max_missing_preview = int(max_missing_preview)

    def validate(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "module": "038_premiere_xml_validator",
            "xml_path": str(self.xml_path),
            "xml_exists": self.xml_path.exists(),
            "xml_size_bytes": self.xml_path.stat().st_size if self.xml_path.exists() else 0,
            "ok": False,
            "status": "fail",
            "errors": [],
            "warnings": [],
            "info": [],
            "counts": {},
            "sequence": {},
            "media": {
                "total_references": 0,
                "unique_references": 0,
                "existing": 0,
                "missing": 0,
                "missing_preview": [],
            },
            "premiere_note": "Cách ổn định nhất: Premiere Pro > File > Import > chọn XML.",
            "audio_note": "XML hiện nên giữ audio dual mono an toàn: A1 = Left, A2 = Right.",
        }

        if not self.xml_path.exists():
            result["errors"].append(f"Không thấy XML: {self.xml_path}")
            return result

        if self.xml_path.stat().st_size <= 0:
            result["errors"].append("XML rỗng.")
            return result

        try:
            tree = ET.parse(self.xml_path)
            root = tree.getroot()
        except Exception as exc:
            result["errors"].append(f"Không parse được XML: {exc!r}")
            return result

        result["info"].append(f"Root tag: {self._strip_ns(root.tag)}")

        all_nodes = list(root.iter())
        tag_counts: dict[str, int] = {}
        for node in all_nodes:
            tag = self._strip_ns(node.tag)
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        result["counts"] = {
            "all_nodes": len(all_nodes),
            "sequence": tag_counts.get("sequence", 0),
            "clipitem": tag_counts.get("clipitem", 0),
            "file": tag_counts.get("file", 0),
            "pathurl": tag_counts.get("pathurl", 0),
            "video": tag_counts.get("video", 0),
            "audio": tag_counts.get("audio", 0),
            "track": tag_counts.get("track", 0),
        }

        sequence_nodes = self._find_all(root, "sequence")
        if not sequence_nodes:
            result["errors"].append("Không thấy node <sequence>. Premiere có thể không tạo sequence.")
        else:
            seq = sequence_nodes[0]
            result["sequence"] = self._extract_sequence_info(seq)
            result["info"].append(f"Sequence: {result['sequence'].get('name') or 'Unknown'}")

        clipitems = self._find_all(root, "clipitem")
        if not clipitems:
            result["errors"].append("Không thấy clipitem nào. XML có thể import rỗng.")
        elif len(clipitems) < 2:
            result["warnings"].append("XML chỉ có rất ít clipitem. Kiểm tra lại nếu sequence bị rỗng.")

        media_refs = self._extract_media_refs(root)
        result["media"]["total_references"] = len(media_refs)
        unique_refs = sorted(set(media_refs))
        result["media"]["unique_references"] = len(unique_refs)

        if not unique_refs:
            result["warnings"].append("Không tìm thấy pathurl media. Premiere có thể import sequence nhưng media có thể offline.")
        elif self.check_media_exists:
            existing = 0
            missing: list[str] = []

            for ref in unique_refs:
                path = self.pathurl_to_path(ref)
                if path and path.exists():
                    existing += 1
                else:
                    missing.append(ref)

            result["media"]["existing"] = existing
            result["media"]["missing"] = len(missing)
            result["media"]["missing_preview"] = missing[: self.max_missing_preview]

            if missing:
                result["warnings"].append(
                    f"Có {len(missing)} media path có thể bị offline/missing. Xem missing_preview trong report."
                )
            else:
                result["info"].append("Tất cả media path kiểm tra được đều tồn tại.")

        audio_clipitems = self._count_clipitems_under_tag(root, "audio")
        video_clipitems = self._count_clipitems_under_tag(root, "video")
        result["counts"]["video_clipitems"] = video_clipitems
        result["counts"]["audio_clipitems"] = audio_clipitems

        if video_clipitems == 0:
            result["errors"].append("Không thấy video clipitem.")
        if audio_clipitems == 0:
            result["warnings"].append("Không thấy audio clipitem. Nếu footage có tiếng, cần kiểm tra XML export.")
        if audio_clipitems > 0 and video_clipitems > 0 and audio_clipitems < video_clipitems:
            result["warnings"].append(
                "Số audio clipitem ít hơn video clipitem. Có thể vẫn đúng, nhưng nên kiểm tra tiếng trong Premiere."
            )

        if audio_clipitems >= video_clipitems * 2 and video_clipitems > 0:
            result["info"].append("Audio có vẻ đang theo hướng dual mono / nhiều kênh. Đây là hướng an toàn hiện tại.")
        else:
            result["info"].append("Không xác nhận chắc được dual mono từ XML. Sau khi import Premiere, kiểm tra A1/A2.")

        if result["errors"]:
            result["status"] = "fail"
            result["ok"] = False
        elif result["warnings"]:
            result["status"] = "warn"
            result["ok"] = True
        else:
            result["status"] = "ok"
            result["ok"] = True

        return result

    def write_reports(self, output_dir: str | Path | None = None) -> dict[str, str]:
        output = Path(output_dir) if output_dir else self.xml_path.parent
        output.mkdir(parents=True, exist_ok=True)

        result = self.validate()

        json_path = output / "XML_VALIDATION_REPORT.json"
        txt_path = output / "XML_VALIDATION_REPORT.txt"
        html_path = output / "XML_VALIDATION_REPORT.html"

        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        txt_path.write_text(self.render_text(result), encoding="utf-8")
        html_path.write_text(self.render_html(result), encoding="utf-8")

        return {
            "json": str(json_path),
            "txt": str(txt_path),
            "html": str(html_path),
            "status": result.get("status", "unknown"),
            "ok": str(bool(result.get("ok"))),
        }

    @staticmethod
    def render_text(result: dict[str, Any]) -> str:
        lines = [
            "STT AI Editor - Premiere XML Validation Report",
            "=" * 76,
            f"Created: {result.get('created_at')}",
            f"Status: {str(result.get('status')).upper()}",
            f"XML: {result.get('xml_path')}",
            f"Size: {result.get('xml_size_bytes')} bytes",
            "",
            "Counts:",
        ]

        for k, v in result.get("counts", {}).items():
            lines.append(f"- {k}: {v}")

        seq = result.get("sequence", {})
        if seq:
            lines += ["", "Sequence:"]
            for k, v in seq.items():
                lines.append(f"- {k}: {v}")

        media = result.get("media", {})
        lines += [
            "",
            "Media:",
            f"- total_references: {media.get('total_references')}",
            f"- unique_references: {media.get('unique_references')}",
            f"- existing: {media.get('existing')}",
            f"- missing: {media.get('missing')}",
        ]

        if media.get("missing_preview"):
            lines += ["", "Missing preview:"]
            for item in media.get("missing_preview", []):
                lines.append(f"- {item}")

        for title, key in [("Errors", "errors"), ("Warnings", "warnings"), ("Info", "info")]:
            lines += ["", f"{title}:"]
            values = result.get(key, [])
            if values:
                for item in values:
                    lines.append(f"- {item}")
            else:
                lines.append("- None")

        lines += [
            "",
            "Premiere import:",
            "- Premiere Pro > File > Import > chọn XML.",
            "",
            "Audio note:",
            f"- {result.get('audio_note')}",
        ]

        return "\n".join(lines)

    @staticmethod
    def render_html(result: dict[str, Any]) -> str:
        status = str(result.get("status", "unknown")).upper()
        xml = html.escape(str(result.get("xml_path", "")))
        counts = result.get("counts", {})
        sequence = result.get("sequence", {})
        media = result.get("media", {})

        def list_items(items: list[str]) -> str:
            if not items:
                return "<li>None</li>"
            return "\n".join(f"<li>{html.escape(str(x))}</li>" for x in items)

        counts_html = "\n".join(
            f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
            for k, v in counts.items()
        )
        seq_html = "\n".join(
            f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
            for k, v in sequence.items()
        )
        media_html = "\n".join(
            f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
            for k, v in media.items()
            if k != "missing_preview"
        )

        missing_preview = media.get("missing_preview", [])

        return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>STT AI Editor - XML Validation Report</title>
<style>
body {{
  font-family: Arial, sans-serif;
  background: #111;
  color: #eee;
  margin: 32px;
  line-height: 1.55;
}}
.card {{
  max-width: 1100px;
  background: #181818;
  border: 1px solid #333;
  border-radius: 16px;
  padding: 24px;
}}
.badge {{
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #666;
  font-weight: 700;
}}
code {{
  display: block;
  background: #000;
  padding: 12px;
  border-radius: 10px;
  overflow-wrap: anywhere;
}}
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0 22px;
}}
td {{
  border-bottom: 1px solid #333;
  padding: 8px;
}}
h2 {{ margin-top: 28px; }}
</style>
</head>
<body>
<div class="card">
  <div class="badge">STATUS: {html.escape(status)}</div>
  <h1>Premiere XML Validation Report</h1>
  <p>XML:</p>
  <code>{xml}</code>

  <h2>Counts</h2>
  <table>{counts_html}</table>

  <h2>Sequence</h2>
  <table>{seq_html or '<tr><td>None</td></tr>'}</table>

  <h2>Media</h2>
  <table>{media_html}</table>

  <h2>Errors</h2>
  <ul>{list_items(result.get("errors", []))}</ul>

  <h2>Warnings</h2>
  <ul>{list_items(result.get("warnings", []))}</ul>

  <h2>Info</h2>
  <ul>{list_items(result.get("info", []))}</ul>

  <h2>Missing media preview</h2>
  <ul>{list_items(missing_preview)}</ul>

  <h2>Premiere Import</h2>
  <p>Premiere Pro &gt; File &gt; Import &gt; chọn XML.</p>
</div>
</body>
</html>
'''

    @staticmethod
    def pathurl_to_path(pathurl: str) -> Path | None:
        value = str(pathurl).strip()
        if not value:
            return None

        value = urllib.parse.unquote(value)

        if value.lower().startswith("file://localhost/"):
            value = value[len("file://localhost/") :]
        elif value.lower().startswith("file:///"):
            value = value[len("file:///") :]
        elif value.lower().startswith("file://"):
            value = value[len("file://") :]

        value = value.replace("/", "\\")
        value = re.sub(r"^\\+([A-Za-z]:\\)", r"\1", value)

        try:
            return Path(value)
        except Exception:
            return None

    @staticmethod
    def _strip_ns(tag: str) -> str:
        return tag.split("}", 1)[-1] if "}" in tag else tag

    def _find_all(self, root: ET.Element, tag_name: str) -> list[ET.Element]:
        return [node for node in root.iter() if self._strip_ns(node.tag) == tag_name]

    def _extract_media_refs(self, root: ET.Element) -> list[str]:
        refs: list[str] = []
        for node in root.iter():
            if self._strip_ns(node.tag) == "pathurl" and node.text:
                refs.append(node.text.strip())
        return refs

    def _extract_sequence_info(self, seq: ET.Element) -> dict[str, Any]:
        info: dict[str, Any] = {}

        name_node = self._find_first_child(seq, "name")
        if name_node is not None and name_node.text:
            info["name"] = name_node.text.strip()

        for node in seq.iter():
            tag = self._strip_ns(node.tag)
            if tag in {"duration", "timebase", "ntsc"} and node.text and tag not in info:
                info[tag] = node.text.strip()

        return info

    def _count_clipitems_under_tag(self, root: ET.Element, parent_tag: str) -> int:
        count = 0
        for parent in self._find_all(root, parent_tag):
            for node in parent.iter():
                if self._strip_ns(node.tag) == "clipitem":
                    count += 1
        return count

    def _find_first_child(self, node: ET.Element, tag_name: str) -> ET.Element | None:
        for child in node:
            if self._strip_ns(child.tag) == tag_name:
                return child
        return None


def validate_premiere_xml(
    xml_path: str | Path,
    output_dir: str | Path | None = None,
    check_media_exists: bool = True,
) -> dict[str, Any]:
    validator = PremiereXMLValidator(xml_path=xml_path, check_media_exists=check_media_exists)
    result = validator.validate()
    if output_dir:
        validator.write_reports(output_dir=output_dir)
    return result
