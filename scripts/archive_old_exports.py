from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export_cleaner import archive_old_exports_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    result = archive_old_exports_existing_project(
        project_root=project_root,
        keep_latest_per_prefix=2,
    )

    print("EXPORT CLEANUP ARCHIVE DONE")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    archive_dir = Path(result["archive_run_dir"])
    if archive_dir.exists():
        os.startfile(archive_dir)


if __name__ == "__main__":
    main()
