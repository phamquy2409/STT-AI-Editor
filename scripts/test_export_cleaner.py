from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export_cleaner import archive_old_exports_existing_project, preview_export_cleanup_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    # Safe default: preview only.
    result = preview_export_cleanup_existing_project(
        project_root=project_root,
        keep_latest_per_prefix=2,
    )

    print("EXPORT CLEANUP PREVIEW")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    report = Path(result["report_json"])
    if report.exists():
        print()
        print(f"Report: {report}")
        os.startfile(report.parent)

    print()
    print("To actually archive old export folders, run:")
    print('python scripts/archive_old_exports.py')


if __name__ == "__main__":
    main()
