from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

import cv2

from core.project import ProjectManager, STTProject


@dataclass
class PreviewReviewConfig:
    thumbnail_width: int = 960
    jpg_quality: int = 82
    title: str = "STT AI Rough Cut Review"


class PreviewReviewGenerator:
    # Build 008: create thumbnails and review.html for AI-selected roughcut.

    def __init__(
        self,
        project: STTProject,
        roughcut_json: str | Path | None = None,
        config: PreviewReviewConfig | None = None,
    ) -> None:
        self.project = project
        self.roughcut_json = Path(roughcut_json) if roughcut_json else self._find_latest_roughcut_json()
        self.config = config or PreviewReviewConfig()

    def generate(self) -> dict[str, str]:
        if not self.roughcut_json.exists():
            raise FileNotFoundError(f"roughcut_plan.json not found: {self.roughcut_json}")

        items = json.loads(self.roughcut_json.read_text(encoding="utf-8"))

        output_dir = self.roughcut_json.parent
        thumbs_dir = output_dir / "preview_thumbnails"
        thumbs_dir.mkdir(parents=True, exist_ok=True)

        review_html = output_dir / "review.html"
        review_json = output_dir / "review_data.json"

        print("STT AI Preview Review")
        print(f"Project: {self.project.name}")
        print(f"Roughcut: {self.roughcut_json}")
        print(f"Thumbnails: {thumbs_dir}")
        print("-" * 60)

        review_items: list[dict] = []

        for item in items:
            order = int(item.get("order", len(review_items) + 1))
            thumb_name = f"thumb_{order:03d}.jpg"
            thumb_path = thumbs_dir / thumb_name

            start = float(item.get("source_start_seconds", 0.0))
            end = float(item.get("source_end_seconds", start))
            middle_second = (start + end) / 2.0

            thumb_status = "ok"
            thumb_error = ""

            try:
                self._save_thumbnail(
                    video_path=str(item["video_path"]),
                    second=middle_second,
                    output_path=thumb_path,
                )
            except Exception as exc:
                thumb_status = "error"
                thumb_error = str(exc)

            row = dict(item)
            row["thumbnail"] = f"preview_thumbnails/{thumb_name}"
            row["thumbnail_status"] = thumb_status
            row["thumbnail_error"] = thumb_error
            review_items.append(row)

            print(
                f"[{order}/{len(items)}] {item.get('video_filename')} "
                f"{start:.2f}-{end:.2f}s | {thumb_status}"
            )

        review_json.write_text(
            json.dumps(review_items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        review_html.write_text(
            self._build_html(review_items),
            encoding="utf-8",
        )

        print("-" * 60)
        print("PREVIEW REVIEW COMPLETE")
        print(f"HTML: {review_html}")
        print(f"JSON: {review_json}")
        print("-" * 60)

        return {
            "html": str(review_html),
            "json": str(review_json),
            "thumbnails": str(thumbs_dir),
            "roughcut_json": str(self.roughcut_json),
        }

    def _find_latest_roughcut_json(self) -> Path:
        candidates = sorted(
            self.project.paths.exports_dir.glob("roughcut_*/roughcut_plan.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not candidates:
            return self.project.paths.exports_dir / "roughcut_plan.json"

        return candidates[0]

    def _save_thumbnail(self, video_path: str, second: float, output_path: Path) -> None:
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps <= 0:
                raise RuntimeError("Invalid FPS.")

            frame_index = max(0, int(second * fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError("Cannot read frame.")

            frame = self._resize_frame(frame, self.config.thumbnail_width)

            ok = cv2.imwrite(
                str(output_path),
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), int(self.config.jpg_quality)],
            )

            if not ok:
                raise RuntimeError(f"Cannot write thumbnail: {output_path}")

        finally:
            cap.release()

    @staticmethod
    def _resize_frame(frame, target_width: int):
        h, w = frame.shape[:2]

        if w <= target_width:
            return frame

        scale = target_width / float(w)
        new_w = int(w * scale)
        new_h = int(h * scale)

        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _build_html(self, items: list[dict]) -> str:
        total_duration = sum(float(i.get("duration_seconds", 0.0)) for i in items)
        avg_keep = 0.0

        if items:
            avg_keep = sum(float(i.get("ai_keep_score", 0.0)) for i in items) / len(items)

        cards = "\n".join(self._card_html(item) for item in items)

        return f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{escape(self.config.title)}</title>
  <style>
    :root {{
      --bg:#0b0b0d;
      --card:#17171c;
      --card2:#22222a;
      --text:#f5f5f7;
      --muted:#aaaab4;
      --line:#33333d;
      --green:#8ef0b0;
      --yellow:#ffd166;
      --red:#ff7b7b;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      background:var(--bg);
      color:var(--text);
      font-family:Arial, Helvetica, sans-serif;
    }}
    header {{
      position:sticky;
      top:0;
      z-index:10;
      padding:18px 22px;
      background:rgba(11,11,13,.92);
      backdrop-filter:blur(16px);
      border-bottom:1px solid var(--line);
    }}
    h1 {{ margin:0 0 8px; font-size:24px; }}
    .sub {{ color:var(--muted); font-size:13px; line-height:1.45; }}
    .stats {{
      display:flex;
      gap:10px;
      flex-wrap:wrap;
      margin-top:14px;
    }}
    .stat {{
      padding:8px 12px;
      background:var(--card);
      border:1px solid var(--line);
      border-radius:999px;
      font-size:13px;
    }}
    main {{
      padding:22px;
      display:grid;
      grid-template-columns:repeat(auto-fill,minmax(340px,1fr));
      gap:18px;
    }}
    .card {{
      background:var(--card);
      border:1px solid var(--line);
      border-radius:18px;
      overflow:hidden;
      box-shadow:0 16px 40px rgba(0,0,0,.28);
    }}
    .thumb {{
      width:100%;
      aspect-ratio:16/9;
      object-fit:cover;
      display:block;
      background:#050506;
    }}
    .body {{ padding:14px; }}
    .title {{
      font-weight:700;
      font-size:15px;
      line-height:1.35;
      margin-bottom:8px;
      word-break:break-word;
    }}
    .meta {{
      color:var(--muted);
      font-size:12px;
      line-height:1.55;
    }}
    .scores {{
      display:grid;
      grid-template-columns:repeat(3,1fr);
      gap:8px;
      margin-top:12px;
    }}
    .score {{
      background:var(--card2);
      border:1px solid var(--line);
      border-radius:12px;
      padding:9px;
      font-size:11px;
      color:var(--muted);
    }}
    .score strong {{
      display:block;
      margin-top:3px;
      color:var(--text);
      font-size:18px;
    }}
    .keep strong {{ color:var(--green); }}
    .path {{
      margin-top:10px;
      font-size:11px;
      color:#777783;
      word-break:break-all;
    }}
    .badge {{
      display:inline-block;
      margin-top:10px;
      padding:6px 9px;
      background:rgba(142,240,176,.12);
      color:var(--green);
      border:1px solid rgba(142,240,176,.35);
      border-radius:999px;
      font-size:12px;
      font-weight:700;
    }}
    footer {{
      padding:18px 22px 35px;
      color:var(--muted);
      border-top:1px solid var(--line);
      font-size:12px;
    }}
  </style>
</head>
<body>
<header>
  <h1>{escape(self.config.title)}</h1>
  <div class="sub">
    Project: {escape(self.project.name)}<br>
    Created: {escape(datetime.now().isoformat(timespec="seconds"))}<br>
    Source: {escape(str(self.roughcut_json))}
  </div>
  <div class="stats">
    <div class="stat">Segments: {len(items)}</div>
    <div class="stat">Duration: {total_duration:.2f}s</div>
    <div class="stat">Avg Keep: {avg_keep:.2f}</div>
  </div>
</header>
<main>
{cards}
</main>
<footer>STT AI Editor · Preview Review Build 008</footer>
</body>
</html>'''

    def _card_html(self, item: dict) -> str:
        order = int(item.get("order", 0))
        filename = escape(str(item.get("video_filename", "")))
        thumbnail = escape(str(item.get("thumbnail", "")))
        video_path = escape(str(item.get("video_path", "")))

        start = float(item.get("source_start_seconds", 0.0))
        end = float(item.get("source_end_seconds", 0.0))
        duration = float(item.get("duration_seconds", 0.0))
        timeline_start = float(item.get("timeline_start_seconds", 0.0))
        timeline_end = float(item.get("timeline_end_seconds", 0.0))

        keep = float(item.get("ai_keep_score", 0.0))
        beauty = float(item.get("beauty_score", 0.0))
        sharp = float(item.get("sharpness_score", 0.0))
        stable = float(item.get("stability_score", 0.0))
        exposure = float(item.get("exposure_score", 0.0))
        motion = float(item.get("motion_score", 0.0))

        if item.get("thumbnail_status") == "ok":
            thumb_html = f'<img class="thumb" src="{thumbnail}" alt="{filename}">'
        else:
            err = escape(str(item.get("thumbnail_error", "")))
            thumb_html = f'<div class="thumb" style="display:flex;align-items:center;justify-content:center;color:#ff7b7b;padding:18px;text-align:center;">Thumbnail error<br>{err}</div>'

        return f'''<article class="card">
  {thumb_html}
  <div class="body">
    <div class="title">#{order:03d} · {filename}</div>
    <div class="meta">
      Source: {start:.2f}s → {end:.2f}s · Duration: {duration:.2f}s<br>
      Timeline: {timeline_start:.2f}s → {timeline_end:.2f}s
    </div>
    <div class="scores">
      <div class="score keep">AI Keep<strong>{keep:.1f}</strong></div>
      <div class="score">Beauty<strong>{beauty:.1f}</strong></div>
      <div class="score">Sharp<strong>{sharp:.1f}</strong></div>
      <div class="score">Stable<strong>{stable:.1f}</strong></div>
      <div class="score">Exposure<strong>{exposure:.1f}</strong></div>
      <div class="score">Motion<strong>{motion:.1f}</strong></div>
    </div>
    <div class="badge">KEEP CANDIDATE</div>
    <div class="path">{video_path}</div>
  </div>
</article>'''


def generate_preview_review_existing_project(
    project_root: str | Path,
    roughcut_json: str | Path | None = None,
) -> dict[str, str]:
    manager = ProjectManager()
    project = manager.open_project(project_root)

    generator = PreviewReviewGenerator(
        project=project,
        roughcut_json=roughcut_json,
    )

    return generator.generate()
