from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from core.gui import STTAIEditorWindow

    patched = getattr(STTAIEditorWindow, "_stt_production_gui_patch_applied", False)
    print("Production GUI patch applied:", patched)

    if not patched:
        raise SystemExit("Production GUI patch was not applied.")

    print("OK - Module 036 production GUI patch is installed.")
    print()
    print("Run GUI:")
    print("python scripts/run_gui.py")


if __name__ == "__main__":
    main()
