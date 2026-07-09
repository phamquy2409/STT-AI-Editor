from __future__ import annotations

import os
import shutil
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    targets = [
        repo_root / "build",
        repo_root / "dist" / "STT AI Editor Console",
    ]

    for spec in repo_root.glob("*.spec"):
        targets.append(spec)

    for path in targets:
        if path.is_dir():
            print(f"Remove folder: {path}")
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            print(f"Remove file: {path}")
            path.unlink(missing_ok=True)

    print()
    print("Cleanup done.")
    print("Note: dist\\STT AI Editor is kept.")


if __name__ == "__main__":
    main()
