from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.source_media_audit import audit_source_media

def main() -> None:
    print("Module import OK: Source Media Audit")
    print("Function:", audit_source_media)
    print("Run script in scripts folder.")

if __name__ == "__main__":
    main()
