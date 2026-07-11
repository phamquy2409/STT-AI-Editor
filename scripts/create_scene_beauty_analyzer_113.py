from precise_beat_beauty_common import *


def analyze_file(path: Path, sample_windows: int, preview: bool = False) -> dict[str, Any]:
    if path.suffix.lower() == ".braw":
        return {
            "filename": path.name,
            "file": str(path),
            "beauty_score": 35,
            "best_source_in_sec": 0.0,
            "best_window_sec": 1.0,
            "beauty_class": "braw_not_analyzed",
            "usable_for_long": False,
            "usable_for_fast": True,
            "reject_reasons": "braw_not_analyzed",
            "motion_class": "unknown",
            "duration_sec": 0,
        }

    try:
        import cv2  # type: ignore
    except Exception as e:
        return {
            "filename": path.name,
            "file": str(path),
            "beauty_score": 45,
            "best_source_in_sec": 0.0,
            "best_window_sec": 1.0,
            "beauty_class": "no_cv2",
            "usable_for_long": False,
            "usable_for_fast": True,
            "reject_reasons": repr(e),
            "motion_class": "unknown",
            "duration_sec": media_duration(path),
        }

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {
            "filename": path.name,
            "file": str(path),
            "beauty_score": 30,
            "best_source_in_sec": 0.0,
            "best_window_sec": 1.0,
            "beauty_class": "cannot_open",
            "usable_for_long": False,
            "usable_for_fast": False,
            "reject_reasons": "cannot_open",
            "motion_class": "unknown",
            "duration_sec": media_duration(path),
        }

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = float(frames / fps) if fps > 0 and frames > 0 else media_duration(path)
    if duration <= 0 or frames <= 2:
        cap.release()
        return {
            "filename": path.name,
            "file": str(path),
            "beauty_score": 25,
            "best_source_in_sec": 0.0,
            "best_window_sec": 1.0,
            "beauty_class": "bad_duration",
            "usable_for_long": False,
            "usable_for_fast": False,
            "reject_reasons": "bad_duration",
            "motion_class": "unknown",
            "duration_sec": round(duration, 3),
        }

    # Test windows inside clip, not only file-level.
    window_len = min(2.4, max(0.7, duration * 0.35))
    starts = []
    if duration <= window_len + 0.3:
        starts = [0.0]
    else:
        for i in range(sample_windows):
            a = i / max(1, sample_windows - 1)
            starts.append(round(0.08 * duration + a * max(0.1, duration * 0.84 - window_len), 3))

    best = None
    all_scores = []
    for st in starts:
        frame_positions = []
        for alpha in [0.0, 0.35, 0.7, 1.0]:
            t = min(duration - 0.05, st + window_len * alpha)
            frame_positions.append(int(max(0, min(frames - 1, t * fps))))

        blurs = []
        brights = []
        contrasts = []
        edge_amounts = []
        diffs = []
        prev_gray = None

        for pos in frame_positions:
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

            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                diffs.append(float(diff.mean()))
            prev_gray = gray

        if not blurs:
            continue

        avg_blur = sum(blurs) / len(blurs)
        min_blur = min(blurs)
        bright = sum(brights) / len(brights)
        contrast = sum(contrasts) / len(contrasts)
        edge = sum(edge_amounts) / len(edge_amounts)
        motion = sum(diffs) / len(diffs) if diffs else 0
        motion_max = max(diffs) if diffs else 0

        score = 50.0
        reasons = []

        # sharp
        if avg_blur >= 110:
            score += 18
        elif avg_blur >= 70:
            score += 10
        elif avg_blur < 35:
            score -= 30
            reasons.append("blur")

        # exposure
        if 55 <= bright <= 185:
            score += 12
        elif bright < 30:
            score -= 25
            reasons.append("too_dark")
        elif bright > 230:
            score -= 22
            reasons.append("too_bright")
        else:
            score -= 4

        # detail/composition proxy
        if contrast >= 25 and edge >= 0.015:
            score += 12
        elif contrast < 12 or edge < 0.006:
            score -= 24
            reasons.append("empty_low_detail")
        else:
            score += 4

        # motion: stable cinematic better for long; active okay only for fast.
        if 2 <= motion <= 14 and motion_max <= 28:
            score += 15
            motion_class = "stable"
        elif motion <= 2:
            score += 6
            motion_class = "static"
        elif motion <= 24 and motion_max <= 40:
            score += 3
            motion_class = "active"
        else:
            score -= 30
            motion_class = "shaky_or_whip"
            reasons.append("shaky_or_whip")

        # avoid first/last handle a bit
        if st < 0.25:
            score -= 4
        if st + window_len > duration - 0.20:
            score -= 4

        score = max(0, min(100, round(score, 1)))
        row = {
            "start": st,
            "window": round(window_len, 3),
            "score": score,
            "avg_blur": round(avg_blur, 3),
            "min_blur": round(min_blur, 3),
            "brightness": round(bright, 3),
            "contrast": round(contrast, 3),
            "edge": round(edge, 5),
            "motion": round(motion, 3),
            "motion_max": round(motion_max, 3),
            "motion_class": motion_class,
            "reasons": ",".join(reasons),
        }
        all_scores.append(row)
        if best is None or row["score"] > best["score"]:
            best = row

    cap.release()

    if best is None:
        return {
            "filename": path.name,
            "file": str(path),
            "beauty_score": 30,
            "best_source_in_sec": 0.0,
            "best_window_sec": 1.0,
            "beauty_class": "no_good_window",
            "usable_for_long": False,
            "usable_for_fast": False,
            "reject_reasons": "no_good_window",
            "motion_class": "unknown",
            "duration_sec": round(duration, 3),
        }

    cls = "beautiful" if best["score"] >= 78 else "good" if best["score"] >= 65 else "review" if best["score"] >= 48 else "bad"
    usable_long = best["score"] >= 68 and best["motion_class"] in {"stable", "static"}
    usable_fast = best["score"] >= 50 and best["motion_class"] != "shaky_or_whip"

    return {
        "filename": path.name,
        "file": str(path),
        "duration_sec": round(duration, 3),
        "beauty_score": best["score"],
        "beauty_class": cls,
        "best_source_in_sec": best["start"],
        "best_window_sec": best["window"],
        "usable_for_long": usable_long,
        "usable_for_fast": usable_fast,
        "reject_reasons": best["reasons"],
        "motion_class": best["motion_class"],
        "avg_blur": best["avg_blur"],
        "brightness": best["brightness"],
        "contrast": best["contrast"],
        "motion": best["motion"],
        "motion_max": best["motion_max"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="113 Scene Beauty Analyzer: find đẹp/stable window inside source.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--sample-windows", type=int, default=6)
    p.add_argument("--max-files", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "scene_beauty_analyzer_113")

    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "scene_beauty_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    files = []
    for ext in VIDEO_EXTS:
        files.extend(source.rglob(f"*{ext}"))
    files = sorted(set(files), key=lambda p: str(p).lower())
    if a.max_files and a.max_files > 0:
        files = files[:a.max_files]

    items = []
    total = len(files)
    for i, path in enumerate(files, start=1):
        if i == 1 or i % 20 == 0 or i == total:
            print(f"[113] analyzing {i}/{total}: {path.name}", flush=True)
        items.append(analyze_file(path, sample_windows=a.sample_windows))

    data = {
        "ok": True,
        "module": "113_scene_beauty_analyzer",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "file_count": len(items),
        "beautiful_count": sum(1 for x in items if x.get("beauty_class") == "beautiful"),
        "good_count": sum(1 for x in items if x.get("beauty_class") == "good"),
        "review_count": sum(1 for x in items if x.get("beauty_class") == "review"),
        "bad_count": sum(1 for x in items if x.get("beauty_class") == "bad"),
        "items": items,
    }
    write_json(project / "stt_scene_beauty_v1.json", data)
    write_json(out / "stt_scene_beauty_v1.json", data)
    write_csv(out / "SCENE_BEAUTY_V1.csv", items, [
        "filename", "beauty_score", "beauty_class", "best_source_in_sec", "best_window_sec",
        "usable_for_long", "usable_for_fast", "motion_class", "reject_reasons",
        "avg_blur", "brightness", "contrast", "motion", "motion_max", "duration_sec", "file"
    ])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "file_count": len(items),
        "beautiful_count": data["beautiful_count"],
        "good_count": data["good_count"],
        "review_count": data["review_count"],
        "bad_count": data["bad_count"],
        "fix": "113_scene_beauty_analyzer",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
