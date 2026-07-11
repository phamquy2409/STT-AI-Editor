
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.editing_style_memory_builder.builder import create_editing_style_memory_builder

def main() -> None:
    p = argparse.ArgumentParser(description="Build user editing style memory from 091/092 results.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--profile-name", default="user_wedding_style")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    res = create_editing_style_memory_builder(
        project_root=a.project,
        profile_name=a.profile_name,
        open_folder=not a.no_open,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
