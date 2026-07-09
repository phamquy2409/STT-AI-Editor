from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.final_replace_checker import check_final_replacements

def main() -> None:
    print("Module import OK: Final Replace Checker")
    print("Function:", check_final_replacements)
    print("Run script in scripts folder.")

if __name__ == "__main__":
    main()
