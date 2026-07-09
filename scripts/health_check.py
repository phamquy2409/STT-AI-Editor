from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.app_health import run_health_check


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    repo_root = ROOT

    result = run_health_check(project_root=project_root, repo_root=repo_root)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    report_dir = Path(result["report_dir"])
    if report_dir.exists():
        os.startfile(report_dir)


if __name__ == "__main__":
    main()
