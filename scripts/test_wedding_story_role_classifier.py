
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.wedding_story_role_classifier.classifier import create_wedding_story_role_classifier

def main() -> None:
    print("Module import OK: 127 Wedding Story Role Classifier")
    print("Function:", create_wedding_story_role_classifier)

if __name__ == "__main__":
    main()
