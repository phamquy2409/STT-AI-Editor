from __future__ import annotations

import argparse
from pathlib import Path

from core.media import scan_existing_project
from core.project import ProjectManager
from core.shot_detection import detect_shots_existing_project


def main() -> None:
    parser = argparse.ArgumentParser(description="STT AI Editor CLI")
    sub = parser.add_subparsers(dest="command")

    new_project = sub.add_parser("new-project", help="Create a new STT AI project")
    new_project.add_argument("--projects-root", required=True)
    new_project.add_argument("--name", required=True)
    new_project.add_argument("--source-folder", required=False)
    new_project.add_argument("--overwrite", action="store_true")

    scan = sub.add_parser("scan", help="Scan video files into project database")
    scan.add_argument("--project", required=True)
    scan.add_argument("--source-folder", required=False)

    shots = sub.add_parser("detect-shots", help="Create shot segments from scanned videos")
    shots.add_argument("--project", required=True)
    shots.add_argument("--segment-seconds", type=float, default=3.0)
    shots.add_argument("--keep-existing", action="store_true")

    args = parser.parse_args()

    if args.command == "new-project":
        manager = ProjectManager()
        project = manager.create_project(
            projects_root=Path(args.projects_root),
            name=args.name,
            source_folder=Path(args.source_folder) if args.source_folder else None,
            overwrite=args.overwrite,
        )
        print("PROJECT CREATED")
        print(project.root)
        return

    if args.command == "scan":
        scan_existing_project(
            project_root=Path(args.project),
            source_folder=Path(args.source_folder) if args.source_folder else None,
        )
        return

    if args.command == "detect-shots":
        detect_shots_existing_project(
            project_root=Path(args.project),
            segment_seconds=args.segment_seconds,
            reset_existing=not args.keep_existing,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
