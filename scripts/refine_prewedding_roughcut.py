
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_refiner import REFINER_RULES, refine_prewedding_roughcut


def main() -> None:
    parser = argparse.ArgumentParser(description="Refine prewedding roughcut before Premiere XML export.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--intent", default=None, choices=[None] + sorted(REFINER_RULES))
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--no-compat", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    result = refine_prewedding_roughcut(
        project_root=args.project,
        intent=args.intent,
        target_duration=args.duration,
        write_selection_compat=not args.no_compat,
        open_folder=not args.no_open,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
