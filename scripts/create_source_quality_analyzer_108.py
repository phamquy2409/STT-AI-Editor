from quality_music_common import *


def analyze_video_cv2(path: Path, sample_count: int = 7) -> dict[str, Any]:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception as e:
        return {
            "ok": False,
            "analyzer": "no_cv2",
            "error": repr(e),
            "duration_sec": media_duration(path),
        }

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {
            "ok": False,
            "analyzer": "cv2_cannot_open",
            "duration_sec": media_duration(path),
        }

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = float(frames / fps) if fps > 0 and frames > 0 else media_duration(path)

    if frames <= 2:
        cap.release()
        return {"ok": False, "analyzer": "too_few_frames", "duration_sec": duration}

    # avoid very beginning/end, where operator may still be moving
    positions = []
    for i in range(sample_count):
        alpha = 0.12 + (0.76 * i / max(1, sample_count - 1))
        positions.append(int(max(0, min(frames - 1, frames * alpha))))

    blurs = []
    brights = []
    contrasts = []
    edge_amounts = []
    diffs = []
    prev_small = None

    for pos in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        small = cv2.resize(frame, (320, 180))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        bright = float(gray.mean())
        contrast = float(gray.std())
        edges = cv2.Canny(gray, 60, 140)
        edge_amt = float((edges > 0).mean())
        blurs.append(blur)
        brights.append(bright)
        contrasts.append(contrast)
        edge_amounts.append(edge_amt)

        if prev_small is not None:
            diff = cv2.absdiff(gray, prev_small)
            diffs.append(float(diff.mean()))
        prev_small = gray

    cap.release()

    if not blurs:
        return {"ok": False, "analyzer": "no_readable_samples", "duration_sec": duration}

    avg_blur = sum(blurs) / len(blurs)
    min_blur = min(blurs)
    avg_bright = sum(brights) / len(brights)
    avg_contrast = sum(contrasts) / len(contrasts)
    avg_edge = sum(edge_amounts) / len(edge_amounts)
    motion_avg = sum(diffs) / len(diffs) if diffs else 0.0
    motion_max = max(diffs) if diffs else 0.0
    shake_index = motion_max - motion_avg

    reject = []
    score = 68.0

    if avg_blur < 35 or min_blur < 15:
        reject.append("blur")
        score -= 32
    elif avg_blur < 70:
        score -= 12
    else:
        score += 8

    if avg_bright < 28:
        reject.append("too_dark")
        score -= 25
    elif avg_bright > 232:
        reject.append("too_bright")
        score -= 20
    elif 55 <= avg_bright <= 190:
        score += 6

    if avg_contrast < 12 or avg_edge < 0.008:
        reject.append("empty_or_low_detail")
        score -= 22
    elif avg_contrast > 24:
        score += 6

    # Motion diff is a proxy for shake/whip pan/lung tung.
    if motion_avg > 34 or motion_max > 58:
        reject.append("whip_pan_or_shaky")
        score -= 35
    elif motion_avg > 23 or shake_index > 28:
        reject.append("unstable_motion")
        score -= 22
    elif 2.0 <= motion_avg <= 16:
        score += 8

    if duration and duration < 0.6:
        reject.append("too_short_media")
        score -= 35

    if motion_avg <= 2:
        motion_class = "static"
    elif motion_avg <= 13:
        motion_class = "stable"
    elif motion_avg <= 23:
        motion_class = "active"
    else:
        motion_class = "shaky_or_whip"

    score = max(0, min(100, round(score, 1)))
    usable = score >= 55 and not any(r in reject for r in ["blur", "too_dark", "too_bright", "empty_or_low_detail", "whip_pan_or_shaky"])

    if usable and score >= 78:
        quality_class = "strong"
    elif usable:
        quality_class = "usable"
    elif score >= 45:
        quality_class = "review"
    else:
        quality_class = "bad"

    return {
        "ok": True,
        "analyzer": "cv2_visual_motion_v3",
        "duration_sec": round(duration, 3),
        "fps": round(fps, 3) if fps else 0,
        "frame_count": frames,
        "sample_count": len(blurs),
        "avg_blur": round(avg_blur, 3),
        "min_blur": round(min_blur, 3),
        "avg_brightness": round(avg_bright, 3),
        "avg_contrast": round(avg_contrast, 3),
        "avg_edge": round(avg_edge, 5),
        "motion_avg": round(motion_avg, 3),
        "motion_max": round(motion_max, 3),
        "shake_index": round(shake_index, 3),
        "motion_class": motion_class,
        "quality_score": score,
        "quality_class": quality_class,
        "usable": usable,
        "reject_reasons": ",".join(reject),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="108 Source Quality Analyzer V3: blur/shake/whip/empty gate.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--sample-count", type=int, default=7)
    p.add_argument("--max-files", type=int, default=0, help="0 = all")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "source_quality_analyzer_108")

    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "source_quality_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    files = []
    for ext in VIDEO_EXTS:
        files.extend(source.rglob(f"*{ext}"))
    files = sorted(set(files), key=lambda x: str(x).lower())
    if a.max_files and a.max_files > 0:
        files = files[:a.max_files]

    items = []
    for idx, path in enumerate(files, start=1):
        row = {
            "index": idx,
            "filename": path.name,
            "file": str(path),
            "ext": path.suffix.lower(),
        }
        if path.suffix.lower() == ".braw":
            d = media_duration(path)
            row.update({
                "ok": False,
                "analyzer": "braw_unreadable_cv2",
                "duration_sec": d,
                "quality_score": 42,
                "quality_class": "review_braw",
                "usable": False,
                "motion_class": "unknown",
                "reject_reasons": "braw_not_analyzed",
            })
        else:
            row.update(analyze_video_cv2(path, sample_count=a.sample_count))
        items.append(row)

    strong = sum(1 for x in items if x.get("quality_class") == "strong")
    usable = sum(1 for x in items if x.get("usable") is True)
    bad = sum(1 for x in items if x.get("quality_class") == "bad")
    review = len(items) - usable - bad

    data = {
        "ok": True,
        "module": "108_source_quality_analyzer_v3",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "file_count": len(items),
        "strong_count": strong,
        "usable_count": usable,
        "review_count": review,
        "bad_count": bad,
        "items": items,
    }
    write_json(project / "stt_source_quality_v3.json", data)
    write_json(out / "stt_source_quality_v3.json", data)
    write_csv(out / "SOURCE_QUALITY_V3.csv", items, [
        "index", "filename", "quality_score", "quality_class", "usable", "reject_reasons",
        "motion_class", "avg_blur", "avg_brightness", "avg_contrast", "motion_avg", "motion_max",
        "shake_index", "duration_sec", "analyzer", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "file_count": len(items),
        "strong_count": strong,
        "usable_count": usable,
        "review_count": review,
        "bad_count": bad,
        "fix": "108_source_quality_analyzer_v3",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
