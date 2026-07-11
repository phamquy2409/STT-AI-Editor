from storybeat_common import *


def default_blocks(target: int) -> list[dict[str, Any]]:
    # Single-song report. Scene_need is strict semantic requirement.
    ratios = [
        (0.00, 0.09, "intro_beauty", "hold", "intro_beauty", "false", "detail/venue/dress/ring only"),
        (0.09, 0.24, "cdcr_intro", "medium", "cdcr|makeup", "false", "bride groom / couple / prep"),
        (0.24, 0.46, "ceremony_story", "hold", "ceremony_giatien|ruoc_dau|cdcr", "true", "gia tien / ruoc dau / vow"),
        (0.46, 0.64, "reception_build", "medium", "reception_stage|family|cdcr", "true", "stage / speech / family"),
        (0.64, 0.84, "climax", "fast", "party|reception_stage|cdcr", "true", "fast cuts, avoid food unless tagged"),
        (0.84, 1.00, "ending", "hold", "ending|family|cdcr", "true", "ending/emotion/family"),
    ]
    out = []
    for i, (a, b, part, rhythm, need, fallback, note) in enumerate(ratios, start=1):
        out.append({
            "block": i,
            "start_sec": round(target * a, 3),
            "end_sec": round(target * b, 3),
            "story_part": part,
            "rhythm": rhythm,
            "scene_need": need,
            "allow_fallback": fallback,
            "notes": note,
        })
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="116B create/edit music cut map for story + beat.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--target-seconds", type=int, default=0, help="0 = use music duration, capped 240s")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    out = outdir(project, "music_cut_map_116b")
    music_dur = load_music_duration(project)
    target = int(a.target_seconds)
    if target <= 0:
        target = int(max(90, min(240, music_dur - 2))) if music_dur > 0 else 210

    csv_path = project / "stt_music_cut_map_manual.csv"
    blocks = default_blocks(target)
    if a.overwrite or not csv_path.exists():
        write_csv(csv_path, blocks, ["block", "start_sec", "end_sec", "story_part", "rhythm", "scene_need", "allow_fallback", "notes"])

    active_blocks = read_csv(csv_path)
    data = {
        "ok": True,
        "module": "116B_music_cut_map_manual",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "music_duration_sec": round(music_dur, 3),
        "target_seconds": target,
        "manual_csv": str(csv_path),
        "blocks": active_blocks,
    }
    write_json(project / "stt_music_cut_map_v2.json", data)
    write_json(out / "stt_music_cut_map_v2.json", data)
    write_csv(out / "MUSIC_CUT_MAP_ACTIVE.csv", active_blocks, ["block", "start_sec", "end_sec", "story_part", "rhythm", "scene_need", "allow_fallback", "notes"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "music_duration_sec": round(music_dur, 3),
        "target_seconds": target,
        "manual_csv": str(csv_path),
        "block_count": len(active_blocks),
        "fix": "116B_music_cut_map_manual",
    }, ensure_ascii=False, indent=2))
    if not a.no_open:
        open_path(out)
        open_path(csv_path)


if __name__ == "__main__":
    main()
