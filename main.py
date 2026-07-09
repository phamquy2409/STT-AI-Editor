from __future__ import annotations

import argparse
from pathlib import Path

from core.exporter import export_premiere_xml_existing_project
from core.media import scan_existing_project
from core.moment import find_best_moments_existing_project
from core.people_composition import analyze_people_composition_existing_project
from core.project import ProjectManager
from core.reporting import generate_report_existing_project
from core.review import generate_preview_review_existing_project
from core.roughcut import build_roughcut_existing_project
from core.shot_detection import detect_shots_existing_project
from core.vision import analyze_vision_existing_project


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

    vision = sub.add_parser("analyze-vision", help="Analyze segment sharpness/exposure/motion/stability")
    vision.add_argument("--project", required=True)
    vision.add_argument("--limit", type=int, default=None)
    vision.add_argument("--all", action="store_true", help="Analyze all segments, including already analyzed ones")

    report = sub.add_parser("report", help="Export ranked CSV reports")
    report.add_argument("--project", required=True)
    report.add_argument("--limit", type=int, default=200)
    report.add_argument("--min-keep-score", type=float, default=45.0)

    roughcut = sub.add_parser("roughcut", help="Build rough cut plan from best AI scored segments")
    roughcut.add_argument("--project", required=True)
    roughcut.add_argument("--target-duration", type=float, default=60.0)
    roughcut.add_argument("--min-keep-score", type=float, default=45.0)
    roughcut.add_argument("--max-segments-per-video", type=int, default=2)

    premiere = sub.add_parser("premiere-xml", help="Export Premiere/FCP7 XML from rough cut")
    premiere.add_argument("--project", required=True)
    premiere.add_argument("--roughcut-json", required=False)
    premiere.add_argument("--fps", type=int, default=25)
    premiere.add_argument("--width", type=int, default=3840)
    premiere.add_argument("--height", type=int, default=2160)

    review = sub.add_parser("review", help="Generate thumbnail HTML review page")
    review.add_argument("--project", required=True)
    review.add_argument("--roughcut-json", required=False)

    moment = sub.add_parser("best-moments", help="Find best frame/second inside roughcut segments")
    moment.add_argument("--project", required=True)
    moment.add_argument("--roughcut-json", required=False)
    moment.add_argument("--segment-seconds", type=float, default=2.2)
    moment.add_argument("--sample-step", type=float, default=0.25)

    people = sub.add_parser("people-composition", help="Analyze faces/people/composition on selected moments")
    people.add_argument("--project", required=True)
    people.add_argument("--input-json", required=False)

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

    if args.command == "analyze-vision":
        analyze_vision_existing_project(
            project_root=Path(args.project),
            limit=args.limit,
            only_pending=not args.all,
        )
        return

    if args.command == "report":
        generate_report_existing_project(
            project_root=Path(args.project),
            limit=args.limit,
            min_keep_score=args.min_keep_score,
        )
        return

    if args.command == "roughcut":
        build_roughcut_existing_project(
            project_root=Path(args.project),
            target_duration_seconds=args.target_duration,
            min_keep_score=args.min_keep_score,
            max_segments_per_video=args.max_segments_per_video,
        )
        return

    if args.command == "premiere-xml":
        export_premiere_xml_existing_project(
            project_root=Path(args.project),
            roughcut_json=Path(args.roughcut_json) if args.roughcut_json else None,
            sequence_fps=args.fps,
            sequence_width=args.width,
            sequence_height=args.height,
        )
        return

    if args.command == "review":
        generate_preview_review_existing_project(
            project_root=Path(args.project),
            roughcut_json=Path(args.roughcut_json) if args.roughcut_json else None,
        )
        return

    if args.command == "best-moments":
        find_best_moments_existing_project(
            project_root=Path(args.project),
            roughcut_json=Path(args.roughcut_json) if args.roughcut_json else None,
            refined_segment_seconds=args.segment_seconds,
            sample_step_seconds=args.sample_step,
        )
        return

    if args.command == "people-composition":
        analyze_people_composition_existing_project(
            project_root=Path(args.project),
            input_json=Path(args.input_json) if args.input_json else None,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
