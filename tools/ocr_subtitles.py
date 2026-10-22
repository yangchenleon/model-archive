"""Read burned-in subtitles with OCR and turn them into timed cues.

Some reviewers (e.g. 嘟嘟模玩) hard-code subtitles into the video. OCR of the
subtitle band gives text that is complementary to ASR *and* an exact timestamp
per line, so an extracted mention can link back to the video moment.

Pipeline: ffmpeg samples frames -> crop the subtitle band -> skip unchanged
frames -> RapidOCR recognition -> merge consecutive lines into cues.

``--use-det`` switches to full detection (slower, needed when lines wrap).
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

SPACE = re.compile(r"\s+")
CUE_SIMILARITY = 0.80
CHANGE_THRESHOLD = 1.2


def norm_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return SPACE.sub("", text).strip()


def similar(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def sample_frames(video: Path, out_dir: Path, fps: float, top: float, bottom: float, width: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    crop = f"crop=iw:ih*{bottom - top:.4f}:0:ih*{top:.4f}"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps},{crop},scale={width}:-1",
         "-q:v", "2", "-y", str(out_dir / "f_%05d.jpg")],
        check=True,
    )
    return sorted(out_dir.glob("f_*.jpg"))


def ocr_frames(frames: list[Path], threshold: float, min_score: float, use_det: bool) -> tuple[list[tuple[str, float]], int]:
    """OCR the frames whose band changed; returns (texts, ocr_calls)."""
    engine = RapidOCR()
    texts: list[tuple[str, float]] = []
    previous = None
    last_text, last_score = "", 0.0
    calls = 0
    for frame in frames:
        image = cv2.imread(str(frame), cv2.IMREAD_GRAYSCALE)
        if image is None:
            texts.append((last_text, last_score))
            continue
        thumb = cv2.resize(image, (128, 16), interpolation=cv2.INTER_AREA)
        changed = previous is None or float(np.mean(cv2.absdiff(previous, thumb))) > threshold
        previous = thumb
        if not changed:
            texts.append((last_text, last_score))
            continue
        calls += 1
        if use_det:
            result, _ = engine(str(frame))
            lines = [(text, score) for _box, text, score in (result or []) if score >= min_score]
        else:
            result, _ = engine(str(frame), use_det=False, use_cls=False, use_rec=True)
            lines = []
            for item in result or []:
                text, score = item[0], float(item[-1])
                if score >= min_score:
                    lines.append((text, score))
        last_text = norm_text("".join(text for text, _ in lines))
        last_score = min((score for _, score in lines), default=0.0)
        texts.append((last_text, last_score))
    return texts, calls


def build_cues(texts: list[tuple[str, float]], fps: float) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    step = 1.0 / fps
    for index, (text, score) in enumerate(texts):
        stamp = index * step
        if not text:
            continue
        if current and similar(current["text"], text) >= CUE_SIMILARITY:
            current["end"] = round(stamp + step, 2)
            if len(text) > len(current["text"]):
                current["text"] = text
            current["score"] = max(current["score"], score)
            continue
        if current:
            cues.append(current)
        current = {"start": round(stamp, 2), "end": round(stamp + step, 2), "text": text, "score": round(score, 3)}
    if current:
        cues.append(current)
    return cues


def read_subtitles(
    video: Path,
    fps: float = 2.0,
    top: float = 0.82,
    bottom: float = 0.96,
    width: int = 960,
    threshold: float = CHANGE_THRESHOLD,
    use_det: bool = False,
) -> dict[str, Any]:
    work = Path(tempfile.mkdtemp(prefix="subs_"))
    try:
        frames = sample_frames(video, work, fps, top, bottom, width)
        texts, calls = ocr_frames(frames, threshold, 0.5, use_det)
        cues = build_cues(texts, fps)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {
        "video": str(video),
        "fps": fps,
        "crop": [top, bottom],
        "frames": len(frames),
        "ocr_calls": calls,
        "cue_count": len(cues),
        "cues": cues,
        "text": "".join(cue["text"] for cue in cues),
    }


def batch(reports_dir: Path, start: str, end: str, output_dir: Path, fps: float) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for folder in sorted(reports_dir.iterdir()):
        if not folder.is_dir():
            continue
        parts = folder.name.split("_")
        if len(parts) != 2 or not (start <= parts[0] <= end):
            continue
        video = next((folder / "video").glob("*.mp4"), None)
        if not video:
            continue
        out_path = output_dir / f"{folder.name}.json"
        if out_path.exists():
            print(f"{folder.name} 已存在，跳过", flush=True)
            continue
        payload = read_subtitles(video, fps=fps)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{folder.name} cues={payload['cue_count']} chars={len(payload['text'])} ocr_calls={payload['ocr_calls']}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", type=Path, help="Single video file")
    parser.add_argument("--output", type=Path, help="Output JSON for --video")
    parser.add_argument("--reports-dir", type=Path, default=Path("outputs/daily_reports"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_v2/subtitles"))
    parser.add_argument("--start-date", default="00000000")
    parser.add_argument("--end-date", default="99999999")
    parser.add_argument("--fps", type=float, default=2.0)
    parser.add_argument("--use-det", action="store_true", help="Full detection (handles wrapped lines, slower)")
    args = parser.parse_args()

    if args.video:
        payload = read_subtitles(args.video, fps=args.fps, use_det=args.use_det)
        target = args.output or Path("outputs/daily_v2/subtitles") / f"{args.video.stem}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{target} cues={payload['cue_count']} chars={len(payload['text'])} ocr_calls={payload['ocr_calls']}")
        return

    batch(args.reports_dir, args.start_date, args.end_date, args.output_dir, args.fps)


if __name__ == "__main__":
    main()
