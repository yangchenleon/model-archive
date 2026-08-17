"""Convert downloaded media to a Whisper-friendly mono WAV file."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def extract(media: Path, output: Path, sample_rate: int = 16_000) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is not installed or not on PATH; it is required for audio extraction")
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(media), "-vn", "-ac", "1", "-ar", str(sample_rate), "-c:a", "pcm_s16le", str(output)],
        check=True,
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(extract(args.media, args.output))


if __name__ == "__main__":
    main()
