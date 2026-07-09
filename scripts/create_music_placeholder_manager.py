
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.music_placeholder import create_music_placeholder_manager


def main() -> None:
    parser = argparse.ArgumentParser(description="Create music cue sheet / placeholder manager.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--intent", default="prewedding_reel_60s")
    parser.add_argument("--candidates", default=None, help="CSV danh sách bài đã chọn từ Artlist/Musicbed/YT Audio Library")
    parser.add_argument("--preview-file", default=None, help="File preview/watermark hợp lệ để copy vào project")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = create_music_placeholder_manager(
        project_root=args.project,
        intent=args.intent,
        candidates_csv=args.candidates,
        preview_file=args.preview_file,
        open_folder=not args.no_open,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
