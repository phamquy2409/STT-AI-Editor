
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = "D:/STT Projects/Wedding_Test_001"


@dataclass
class PremierePointerResult:
    ok: bool
    xml: str
    pointer: str
    json_pointer: str


class PremiereXMLPointer:
    # Module 042.
    # Central latest-XML pointer for Premiere script/panel.
    #
    # Text pointer:
    #   %APPDATA%/STT_AI_Editor/premiere_latest_xml.txt
    #
    # JSON pointer:
    #   %APPDATA%/STT_AI_Editor/premiere_latest_xml.json
    #
    # Premiere CEP/JSX reads the txt file for maximum compatibility.

    def __init__(self, project_root: str | Path = DEFAULT_PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.exports_dir = self.project_root / "exports"
        self.appdata_dir = self.get_appdata_dir()
        self.pointer_txt = self.appdata_dir / "premiere_latest_xml.txt"
        self.pointer_json = self.appdata_dir / "premiere_latest_xml.json"

    @staticmethod
    def get_appdata_dir() -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "STT_AI_Editor"
        return Path.home() / "AppData" / "Roaming" / "STT_AI_Editor"

    def find_latest_xml(self) -> Path | None:
        if not self.exports_dir.exists():
            return None

        preferred_names = [
            "stt_ai_premiere_import.xml",
            "01_STT_AI_Premiere_Import.xml",
        ]

        all_found: list[Path] = []

        for name in preferred_names:
            found = [
                p for p in self.exports_dir.glob(f"**/{name}")
                if p.is_file() and "_archive" not in p.parts
            ]
            all_found.extend(found)

        if all_found:
            return sorted(all_found, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        fallback = [
            p for p in self.exports_dir.glob("**/*.xml")
            if p.is_file() and "_archive" not in p.parts
        ]

        if fallback:
            return sorted(fallback, key=lambda p: p.stat().st_mtime, reverse=True)[0]

        return None

    def update(self, xml_path: str | Path | None = None, source: str = "stt_ai_editor") -> dict[str, Any]:
        xml = Path(xml_path) if xml_path else self.find_latest_xml()

        if not xml or not xml.exists():
            raise FileNotFoundError(
                "Không tìm thấy XML để update Premiere pointer.\n"
                "Hãy Export Latest Manual XML trước."
            )

        self.appdata_dir.mkdir(parents=True, exist_ok=True)

        xml = xml.resolve()
        self.pointer_txt.write_text(str(xml), encoding="utf-8")

        data = {
            "ok": True,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "source": source,
            "project_root": str(self.project_root),
            "xml": str(xml),
            "xml_exists": xml.exists(),
            "xml_size_bytes": xml.stat().st_size if xml.exists() else 0,
            "pointer_txt": str(self.pointer_txt),
            "pointer_json": str(self.pointer_json),
        }

        self.pointer_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def read(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ok": False,
            "pointer_txt": str(self.pointer_txt),
            "pointer_json": str(self.pointer_json),
            "xml": "",
            "xml_exists": False,
        }

        if self.pointer_txt.exists():
            xml_text = self.pointer_txt.read_text(encoding="utf-8").strip()
            data["xml"] = xml_text
            data["xml_exists"] = Path(xml_text).exists() if xml_text else False
            data["ok"] = bool(xml_text)

        if self.pointer_json.exists():
            try:
                data["json"] = json.loads(self.pointer_json.read_text(encoding="utf-8"))
            except Exception:
                pass

        return data


def update_premiere_xml_pointer(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
    xml_path: str | Path | None = None,
    source: str = "stt_ai_editor",
) -> dict[str, Any]:
    return PremiereXMLPointer(project_root=project_root).update(xml_path=xml_path, source=source)


def read_premiere_xml_pointer(
    project_root: str | Path = DEFAULT_PROJECT_ROOT,
) -> dict[str, Any]:
    return PremiereXMLPointer(project_root=project_root).read()
