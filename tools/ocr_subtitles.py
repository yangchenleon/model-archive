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


def order_boxes(items: list[Any], line_tolerance: float = 40.0) -> list[Any]:
    """Group boxes into visual lines by y, then order each line left to right.

    A subtitle is often split into several coloured segments; sorting purely by
    y interleaves them (the yellow part can sit a few pixels higher), so the
    boxes must be clustered into a line first.
    """
    def center_y(item: Any) -> float:
        return sum(point[1] for point in item[0]) / len(item[0])

    def left_x(item: Any) -> float:
        return min(point[0] for point in item[0])

    lines: list[list[Any]] = []
    for item in sorted(items, key=center_y):
        if lines and abs(center_y(item) - center_y(lines[-1][0])) <= line_tolerance:
            lines[-1].append(item)
        else:
            lines.append([item])
    ordered: list[Any] = []
    for line in lines:
        ordered.extend(sorted(line, key=left_x))
    return ordered


def keep_subtitle_box(box, gray: "np.ndarray", min_white: float = 0.2, min_aspect: float = 1.2, min_width: int = 60) -> bool:
    """Reject boxes that are not subtitle lines.

    Text printed on the model itself (e.g. ``EFSF``, ``RX-BINI``) is short,
    squarish and dark, while subtitles are wide, flat and predominantly white
    with a black outline, so geometry plus white-pixel ratio separates them.
    """
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    width, height = max(xs) - min(xs), max(ys) - min(ys)
    if width < min_width or height <= 0:
        return False
    if width / height < min_aspect:
        return False
    x0, y0 = int(max(0, min(xs))), int(max(0, min(ys)))
    x1, y1 = int(max(xs)), int(max(ys))
    roi = gray[y0:y1, x0:x1]
    if roi.size == 0:
        return False
    return float((roi > 200).mean()) >= min_white


def ocr_frames(frames: list[Path], engine: RapidOCR, threshold: float, min_score: float, use_det: bool) -> tuple[list[tuple[str, float]], int]:
    """OCR the frames whose band changed; returns (texts, ocr_calls)."""
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
            # two-line subtitles can come back bottom-first; restore reading order
            ordered = order_boxes(result or [])
            lines = [
                (text, score)
                for box, text, score in ordered
                if score >= min_score and keep_subtitle_box(box, image)
            ]
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


def outline_rows(image: "np.ndarray", top: float, bottom: float) -> list["np.ndarray"]:
    """Split the subtitle band into line crops using the glyph outline.

    A plain white-pixel projection merges everything when the background is
    bright, so we require white pixels adjacent to dark pixels (the stroke).
    Columns are then trimmed to the detected glyphs, which keeps stray graphics
    out of the recognition input.
    """
    height = image.shape[0]
    band = image[int(height * top):int(height * bottom)]
    white = ((band[:, :, 0] > 200) & (band[:, :, 1] > 200) & (band[:, :, 2] > 200)).astype(np.uint8)
    dark = ((band[:, :, 0] < 70) & (band[:, :, 1] < 70) & (band[:, :, 2] < 70)).astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    outline = cv2.dilate(white, kernel) & cv2.dilate(dark, kernel)
    projection = outline.sum(axis=1)
    threshold = max(10, int(band.shape[1] * 0.03))
    ranges: list[tuple[int, int]] = []
    start = None
    for y, value in enumerate(projection):
        if value > threshold and start is None:
            start = y
        elif value <= threshold and start is not None:
            if y - start >= 18:
                ranges.append((max(0, start - 4), min(band.shape[0], y + 4)))
            start = None
    if start is not None and len(projection) - start >= 18:
        ranges.append((max(0, start - 4), len(projection)))

    crops: list["np.ndarray"] = []
    for y0, y1 in ranges:
        columns = outline[y0:y1].sum(axis=0)
        xs = np.where(columns > 0)[0]
        if len(xs) == 0:
            continue
        x0, x1 = max(0, xs[0] - 8), min(band.shape[1], xs[-1] + 8)
        crop = band[y0:y1, x0:x1]
        if crop.shape[0] >= 18 and crop.shape[1] >= 20:
            crops.append(crop)
    return crops


def make_engine(mode: str) -> RapidOCR:
    """Detection defaults upscale the wide band to a 736px short side (~5000px
    wide), which costs ~5 s/frame. Capping the long side makes it ~1 s/frame
    with the same accuracy."""
    if mode == "det":
        return RapidOCR(det_limit_side_len=736, det_limit_type="max")
    return RapidOCR()


def read_subtitles_rows(
    frames: list[Path],
    engine: RapidOCR,
    top: float,
    bottom: float,
    min_score: float,
) -> list[tuple[str, float]]:
    texts: list[tuple[str, float]] = []
    for frame in frames:
        image = cv2.imread(str(frame))
        if image is None:
            texts.append(("", 0.0))
            continue
        crops = outline_rows(image, top, bottom)
        pieces: list[str] = []
        scores: list[float] = []
        for crop in crops:
            crop = cv2.resize(crop, (1280, max(1, int(crop.shape[0] * 1280 / crop.shape[1]))))
            result, _ = engine(crop, use_det=False, use_cls=False, use_rec=True)
            for item in result or []:
                text, score = item[0], float(item[-1])
                if score >= min_score:
                    pieces.append(text)
                    scores.append(score)
        texts.append((norm_text("".join(pieces)), min(scores) if scores else 0.0))
    return texts


def _containment(a: str, b: str) -> float:
    """Longest common substring relative to the shorter text."""
    if not a or not b:
        return 0.0
    match = difflib.SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b))
    return match.size / max(1, min(len(a), len(b)))


def merge_repeats(cues: list[dict[str, Any]], threshold: float = 0.45) -> list[dict[str, Any]]:
    """Collapse consecutive cues that are the same line plus overlay noise.

    Product graphics change while a subtitle stays on screen, so detection can
    emit the same sentence with different trailing labels; a high longest-common
    substring ratio means one cue, not several.
    """
    def overlap(a: str, b: str) -> float:
        sa, sb = set(a), set(b)
        return len(sa & sb) / max(1, len(sa | sb))

    merged: list[dict[str, Any]] = []
    for cue in cues:
        if merged and (
            _containment(merged[-1]["text"], cue["text"]) >= threshold
            or overlap(merged[-1]["text"], cue["text"]) >= 0.6
        ):
            previous = merged[-1]
            previous["end"] = max(previous["end"], cue["end"])
            if len(cue["text"]) > len(previous["text"]):
                previous["text"] = cue["text"]
            previous["score"] = max(previous["score"], cue["score"])
            continue
        merged.append(dict(cue))
    return merged


def read_subtitles(
    video: Path,
    fps: float = 2.0,
    top: float = 0.82,
    bottom: float = 0.96,
    width: int = 960,
    threshold: float = CHANGE_THRESHOLD,
    use_det: bool = False,
    engine: RapidOCR | None = None,
    mode: str = "band",
) -> dict[str, Any]:
    work = Path(tempfile.mkdtemp(prefix="subs_"))
    try:
        if mode in ("rows", "det"):
            top, bottom, width = 0.72, 0.98, 1920
        if mode == "det":
            use_det = True
        frames = sample_frames(video, work, fps, top, bottom, width)
        if mode == "rows":
            texts = read_subtitles_rows(frames, engine or RapidOCR(), top, bottom, 0.5)
            calls = len(frames)
        else:
            texts, calls = ocr_frames(frames, engine or RapidOCR(), threshold, 0.5, use_det)
        cues = merge_repeats(build_cues(texts, fps))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {
        "video": str(video),
        "fps": fps,
        "crop": [top, bottom],
        "mode": mode,
        "frames": len(frames),
        "ocr_calls": calls,
        "cue_count": len(cues),
        "cues": cues,
        "text": "".join(cue["text"] for cue in cues),
    }


def batch(reports_dir: Path, start: str, end: str, output_dir: Path, fps: float, mode: str = "band") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    engine = make_engine(mode)  # one model load for the whole run
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
        payload = read_subtitles(video, fps=fps, engine=engine, mode=mode)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{folder.name} cues={payload['cue_count']} chars={len(payload['text'])} ocr_calls={payload['ocr_calls']}", flush=True)


RARE_CHARS = set("眞義劵養卽爲祕覈")
SYMBOL_NOISE = re.compile(r"[\"'“”#@]{2,}|[，。！？、]{2,}")


def suspicion(cue: dict[str, Any]) -> list[str]:
    """Cheap heuristics for lines a human should eyeball before trusting OCR."""
    text = cue.get("text", "")
    reasons: list[str] = []
    if cue.get("score", 1.0) < 0.75:
        reasons.append("低置信")
    if len(text) <= 3:
        reasons.append("过短")
    if text and not re.search(r"[\u4e00-\u9fff]", text):
        reasons.append("无汉字")
    if SYMBOL_NOISE.search(text):
        reasons.append("符号噪声")
    if any(char in RARE_CHARS for char in text):
        reasons.append("生僻字")
    if re.search(r"(.)\1{3,}", text):
        reasons.append("重复字符")
    return reasons


def check(output_dir: Path, limit: int) -> None:
    files = sorted(output_dir.glob("*.json"))
    if not files:
        print(f"{output_dir} 下没有字幕 JSON")
        return
    total_cues = 0
    flagged: list[dict[str, Any]] = []
    per_video: list[dict[str, Any]] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cues = payload.get("cues") or []
        total_cues += len(cues)
        scores = [cue["score"] for cue in cues if cue.get("score")]
        per_video.append({
            "file": path.stem,
            "cues": len(cues),
            "chars": len(payload.get("text", "")),
            "avg_score": round(sum(scores) / len(scores), 3) if scores else 0,
        })
        for cue in cues:
            reasons = suspicion(cue)
            if reasons:
                flagged.append({
                    "file": path.stem,
                    "start": cue["start"],
                    "text": cue["text"],
                    "score": cue["score"],
                    "reasons": reasons,
                })
    avg = sum(v["avg_score"] for v in per_video) / len(per_video)
    print(f"视频 {len(per_video)} 个 | 字幕行 {total_cues} 条 | 平均置信 {avg:.3f} | 可疑 {len(flagged)} 条")
    low = sum(1 for v in per_video if v["avg_score"] < 0.9)
    print(f"平均置信 <0.9 的视频: {low} 个")
    print("\n=== 可疑行（前 {limit} 条，按视频顺序） ===".format(limit=limit))
    for item in flagged[:limit]:
        print(f"[{item['file']}] {item['start']:6.1f}s {item['score']:.2f} {','.join(item['reasons']):12s} {item['text']}")

    report = {"videos": len(per_video), "cues": total_cues, "avg_score": round(avg, 3),
              "flagged": len(flagged), "items": flagged, "per_video": per_video}
    (output_dir / "_qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告已写入 {output_dir / '_qa.json'}")


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
    parser.add_argument("--mode", choices=["band", "rows", "det"], default="band",
                        help="band=fast fixed crop, rows=outline-based line split, det=full detection")
    parser.add_argument("--check", action="store_true", help="Audit existing subtitle JSONs instead of OCR")
    parser.add_argument("--check-limit", type=int, default=60)
    args = parser.parse_args()

    if args.check:
        check(args.output_dir, args.check_limit)
        return

    if args.video:
        payload = read_subtitles(args.video, fps=args.fps, use_det=args.use_det, mode=args.mode, engine=make_engine(args.mode))
        target = args.output or Path("outputs/daily_v2/subtitles") / f"{args.video.stem}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{target} cues={payload['cue_count']} chars={len(payload['text'])} ocr_calls={payload['ocr_calls']}")
        return

    batch(args.reports_dir, args.start_date, args.end_date, args.output_dir, args.fps, args.mode)


if __name__ == "__main__":
    main()
