
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.prewedding_doctor import PreweddingPipelineDoctor, REQUIRED_MODULES


def main() -> None:
    project_root = Path("D:/STT Projects/Wedding_Test_001")
    doctor = PreweddingPipelineDoctor(project_root=project_root, repo_root=ROOT)

    print("Module 052 Prewedding Pipeline Doctor import OK.")
    print("Project:", project_root)
    print("Repo:", ROOT)
    print("Exports:", doctor.exports_dir)
    print()
    print("Required modules:")
    for module_no, module_name, label in REQUIRED_MODULES:
        print("-", module_no, module_name, label)
    print()
    print("Run:")
    print("python scripts/check_prewedding_pipeline.py")


if __name__ == "__main__":
    main()
