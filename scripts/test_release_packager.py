
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.release_packager import APP_NAME, RELEASE_VERSION, STTReleasePackager


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    packager = STTReleasePackager(project_root=project_root, repo_root=ROOT)

    print("Module 053 Release Packager import OK.")
    print("App:", APP_NAME)
    print("Version:", RELEASE_VERSION)
    print("Repo:", ROOT)
    print("Dist app dir:", packager.dist_app_dir)
    print("EXE:", packager.exe_path)
    print("Releases:", packager.releases_dir)
    print()
    print("Run after build EXE:")
    print("python scripts/package_release.py")
    print()
    print("Or build + package:")
    print("python scripts/package_release.py --build-first")


if __name__ == "__main__":
    main()
