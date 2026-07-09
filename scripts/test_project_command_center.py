
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.project_command_center import COMMANDS, create_project_command_center


def main() -> None:
    print("Module 061 Project Command Center import OK.")
    print("Commands:", len(COMMANDS))
    print("Function:", create_project_command_center)
    print()
    print("Run:")
    print("python scripts/create_project_command_center.py")


if __name__ == "__main__":
    main()
