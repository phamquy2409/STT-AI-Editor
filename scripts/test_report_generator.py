from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reporting import generate_report_existing_project


def main() -> None:
    project_root = Path('D:/STT Projects/Wedding_Test_001')

    paths = generate_report_existing_project(
        project_root=project_root,
        limit=200,
        min_keep_score=45.0,
    )

    print()
    print('REPORT FILES:')
    for name, path in paths.items():
        print(f'{name}: {path}')


if __name__ == '__main__':
    main()
