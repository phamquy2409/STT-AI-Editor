from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Reuse visual AI functions from 119 if available.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from visual_ai_common import VIDEO_EXTS, write_json, write_csv, outdir, open_path, media_duration  # noqa
from create_visual_ai_scene_recognizer_119 import load_clip, build_text_bank, sample_frames, classify_images, PROMPTS  # noqa


PROXY_DIR_NAMES = {
    "proxy", "proxies", "proxy media", "proxy_media", "adobe premiere pro video previews",
    "premiere pro video previews", "encoded files", "encoded_files"
}

PROXY_NAME_TOKENS = [
    "_proxy", "-proxy", " proxy.", "_proxy.", "-proxy.", "proxy_",
    "_low", "_720", "_1080_proxy"
]


def is_proxy_path(path: Path) -> bool:
    parts = [p.strip().lower() for p in path.parts]
    for part in parts:
        if part in PROXY_DIR_NAMES:
            return True
    name = path.name.lower()
    stem = path.stem.lower()
    if stem.endswith("_proxy") or stem.endswith("-proxy") or stem.endswith(" proxy"):
        return True
    return any(tok in name for tok in PROXY_NAME_TOKENS)


def original_key(path: Path) -> str:
    s = path.stem.lower()
    for tok in ["_proxy", "-proxy", " proxy"]:
        if s.endswith(tok):
            s = s[: -len(tok)]
    return s


def list_original_files(source: Path) -> tuple[list[Path], list[Path]]:
    all_files = []
    for ext in VIDEO_EXTS:
        all_files.extend(source.rglob(f"*{ext}"))
    all_files = sorted(set(all_files), key=lambda p: str(p).lower())

    proxy_files = [p for p in all_files if is_proxy_path(p)]
    original_files = [p for p in all_files if not is_proxy_path(p)]

    # If original and proxy share same base key, keep original only.
    seen = set()
    cleaned = []
    for p in original_files:
        k = original_key(p)
        if k in seen:
            # keep first by folder/name order
            continue
        seen.add(k)
        cleaned.append(p)
    return cleaned, proxy_files


def main() -> None:
    p = argparse.ArgumentParser(description="119B Visual AI scene recognizer, original source only, skip proxies.")
    p.add_argument("--project", default="D:/STT Projects/Wedding_Test_001")
    p.add_argument("--source", default="D:/27thang6pschh/souce")
    p.add_argument("--frame-samples", type=int, default=8)
    p.add_argument("--model", default="openai/clip-vit-base-patch32")
    p.add_argument("--max-files", type=int, default=0)
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    project = Path(a.project)
    source = Path(a.source)
    out = outdir(project, "visual_ai_original_source_only_119b")

    if not source.exists():
        res = {"ok": False, "error": "SOURCE_NOT_FOUND", "source": str(source)}
        write_json(out / "visual_ai_original_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    originals, proxies = list_original_files(source)
    if a.max_files and a.max_files > 0:
        originals = originals[:a.max_files]

    if not originals:
        res = {
            "ok": False,
            "error": "NO_ORIGINAL_VIDEO_FOUND",
            "source": str(source),
            "proxy_found_count": len(proxies),
            "message": "Only proxy files were found. Point --source to folder containing original media, not Proxies.",
        }
        write_json(out / "visual_ai_original_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    try:
        torch, model, processor, device = load_clip(a.model)
        texts, text_tags, text_feats = build_text_bank(torch, model, processor, device)
    except Exception as e:
        res = {
            "ok": False,
            "error": "VISUAL_AI_MODEL_NOT_READY",
            "message": str(e),
            "install": "python -m pip install -U torch torchvision transformers pillow opencv-python",
        }
        write_json(out / "visual_ai_original_error.json", res)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    items = []
    total = len(originals)
    for i, f in enumerate(originals, start=1):
        if i == 1 or i % 10 == 0 or i == total:
            print(f"[119B] visual AI original {i}/{total}: {f.name}", flush=True)

        if f.suffix.lower() == ".braw":
            item: dict[str, Any] = {
                "filename": f.name,
                "file": str(f),
                "scene_tag": "other",
                "confidence": 0,
                "top_tags": "braw_not_supported_by_cv2",
                "frame_count": 0,
                "ai_reason": "braw_not_decoded_original_kept",
            }
        else:
            imgs = sample_frames(f, a.frame_samples)
            cls = classify_images(torch, model, processor, device, text_tags, text_feats, imgs)
            item = {
                "filename": f.name,
                "file": str(f),
                **cls,
                "ai_reason": "clip_zero_shot_visual_original_only",
            }

        item["_source_order"] = i - 1
        item["media_duration_sec"] = media_duration(f)
        item["is_proxy"] = False
        items.append(item)

    counts = {t: sum(1 for x in items if x.get("scene_tag") == t) for t in PROMPTS.keys()}
    data = {
        "ok": True,
        "module": "119B_visual_ai_original_source_only",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "model": a.model,
        "device": device,
        "source": str(source),
        "file_count": len(items),
        "skipped_proxy_count": len(proxies),
        "scene_counts": counts,
        "items": items,
    }

    # IMPORTANT: overwrite normal 119 output so 120/115 use originals.
    write_json(project / "stt_visual_ai_scene_tags_v1.json", data)
    write_json(project / "stt_visual_ai_scene_tags_original_only_v1.json", data)
    write_json(out / "stt_visual_ai_scene_tags_original_only_v1.json", data)
    write_csv(out / "VISUAL_AI_ORIGINAL_SOURCE_ONLY_V1.csv", items, [
        "filename", "scene_tag", "confidence", "top_tags", "frame_count", "ai_reason", "media_duration_sec", "is_proxy", "file"
    ])
    write_csv(out / "SKIPPED_PROXY_FILES.csv", [{"filename": p.name, "file": str(p)} for p in proxies], ["filename", "file"])

    print(json.dumps({
        "ok": True,
        "report_dir": str(out),
        "model": a.model,
        "device": device,
        "file_count": len(items),
        "skipped_proxy_count": len(proxies),
        "scene_counts": counts,
        "fix": "119B_visual_ai_original_source_only",
    }, ensure_ascii=False, indent=2))

    if not a.no_open:
        open_path(out)


if __name__ == "__main__":
    main()
