from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.source_media_audit import audit_source_media

def main() -> None:
    parser = argparse.ArgumentParser(description="Source Media Audit.")
    parser.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    result = audit_source_media(project_root=args.project, open_folder=not args.no_open)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
