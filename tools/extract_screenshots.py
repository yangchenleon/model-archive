"""Save visually distinct video screenshots using middle-frame comparison."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import BinaryIO


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe must be installed and on PATH")


def _duration(media: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(media)],
        check=True,
        capture_output=True,
        text=True,
    )
    duration = float(json.loads(result.stdout)["format"]["duration"])
    if duration <= 0:
        raise RuntimeError(f"Could not determine a positive duration for {media}")
    return duration


def _read_frame(stream: BinaryIO, size: int) -> bytes | None:
    frame = stream.read(size)
    if not frame:
        return None
    if len(frame) != size:
        raise RuntimeError("ffmpeg returned an incomplete comparison frame")
    return frame


def _difference(current: bytes, previous: bytes) -> float:
    """Return normalized mean absolute pixel difference in the range 0..1."""
    return sum(abs(left - right) for left, right in zip(current, previous)) / (len(current) * 255)


def _save_full_frame(media: Path, timestamp: float, output: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-noaccurate_seek", "-ss", f"{timestamp:.3f}", "-i", str(media), "-frames:v", "1",
            "-q:v", "2", str(output),
        ],
        check=True,
    )


def extract(
    media: Path,
    output_dir: Path,
    interval: float = 1.0,
    threshold: float = 0.08,
    crop_top: float = 0.15,
    crop_bottom: float = 0.75,
    compare_width: int = 96,
    compare_height: int = 96,
) -> dict:
    """Extract the first frame and frames differing from the preceding sample.

    Comparison uses only the central vertical area. This avoids timeline overlays
    and bottom subtitles while preserving the original, uncropped screenshots.
    """
    _require_ffmpeg()
    media = media.resolve()
    if not media.is_file():
        raise FileNotFoundError(f"Media file does not exist: {media}")
    if interval <= 0:
        raise ValueError("interval must be greater than zero")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if not 0 <= crop_top < crop_bottom <= 1:
        raise ValueError("crop_top and crop_bottom must satisfy 0 <= top < bottom <= 1")
    if compare_width <= 0 or compare_height <= 0:
        raise ValueError("comparison dimensions must be positive")

    duration = _duration(media)
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    crop_height = crop_bottom - crop_top
    video_filter = (
        f"fps=1/{interval},"
        f"crop=iw:trunc(ih*{crop_height:.8f}/2)*2:0:trunc(ih*{crop_top:.8f}/2)*2,"
        f"scale={compare_width}:{compare_height}:flags=area,format=gray"
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(media),
        "-vf", video_filter, "-an", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdout is not None
    frame_size = compare_width * compare_height
    previous: bytes | None = None
    selected: list[dict[str, float | str | None]] = []
    samples = 0
    try:
        while (frame := _read_frame(process.stdout, frame_size)) is not None:
            timestamp = samples * interval
            score = None if previous is None else _difference(frame, previous)
            if previous is None or score >= threshold:
                filename = f"{len(selected) + 1:03d}_{timestamp:08.3f}s.jpg"
                destination = frames_dir / filename
                _save_full_frame(media, timestamp, destination)
                selected.append({"timestamp_seconds": round(timestamp, 3), "difference": None if score is None else round(score, 6), "file": str(destination.relative_to(output_dir))})
            previous = frame
            samples += 1
    finally:
        process.stdout.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"ffmpeg comparison pass failed: {stderr.strip()}")
    if not samples:
        raise RuntimeError(f"No video frames could be read from {media}")

    manifest = {
        "media": str(media),
        "duration_seconds": round(duration, 3),
        "sample_interval_seconds": interval,
        "difference_threshold": threshold,
        "comparison_crop": {"top": crop_top, "bottom": crop_bottom},
        "comparison_size": {"width": compare_width, "height": compare_height},
        "samples_examined": samples,
        "screenshots_saved": len(selected),
        "selected_frames": selected,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest"] = str(manifest_path)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between comparison frames")
    parser.add_argument("--threshold", type=float, default=0.08, help="Normalized mean pixel difference, from 0 to 1")
    parser.add_argument("--crop-top", type=float, default=0.15, help="Top fraction of the comparison crop")
    parser.add_argument("--crop-bottom", type=float, default=0.75, help="Bottom fraction of the comparison crop")
    parser.add_argument("--compare-width", type=int, default=96)
    parser.add_argument("--compare-height", type=int, default=96)
    args = parser.parse_args()
    print(json.dumps(extract(args.media, args.output_dir, args.interval, args.threshold, args.crop_top, args.crop_bottom, args.compare_width, args.compare_height), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
