
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.style_profile import WeddingStyleProfile


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    profile = WeddingStyleProfile(project_root)

    print("Module 044 Wedding Style Profile import OK.")
    print("Project:", project_root)
    print("Profile path:", profile.profile_path)
    print("AppData profile:", profile.appdata_profile_path)
    print()
    print("Create/update profile:")
    print("python scripts/create_wedding_style_profile.py")


if __name__ == "__main__":
    main()
