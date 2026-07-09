from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.feedback_learning import apply_feedback_existing_project, learn_feedback_existing_project


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")

    learn = learn_feedback_existing_project(
        project_root=project_root,
        selection_json=None,
        source_json=None,
    )

    print()
    print("LEARN RESULT:")
    print(json.dumps(learn, ensure_ascii=False, indent=2, default=str))

    apply = apply_feedback_existing_project(
        project_root=project_root,
        input_json=None,
        target_duration_seconds=60.0,
        max_segments_per_video=1,
    )

    print()
    print("APPLY RESULT:")
    print(json.dumps(apply, ensure_ascii=False, indent=2, default=str))

    out = Path(apply["output_dir"])
    if out.exists():
        os.startfile(out)


if __name__ == "__main__":
    main()
