"""Transcribe audio through the configured Qwen-compatible chat ASR API."""
from __future__ import annotations

import argparse
import base64
import io
import json
import mimetypes
import os
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

from tools.config import load_env

load_env()


def _compatible_chat_request(audio_data: bytes, mime_type: str, model_name: str, language: str | None) -> str:
    api_key = os.getenv("ASR_API_KEY")
    base_url = os.getenv("ASR_BASE_URL")
    if not api_key:
        raise RuntimeError("ASR_API_KEY is required")
    if not base_url:
        raise RuntimeError("ASR_BASE_URL must point to the Qwen-compatible /v1 endpoint")
    data_url = f"data:{mime_type};base64,{base64.b64encode(audio_data).decode('ascii')}"
    payload: dict[str, Any] = {
        "model": model_name,
        "messages": [{"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": data_url}}]}],
        "stream": False,
        "asr_options": {"enable_itn": False},
    }
    request = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(payload).encode(), method="POST", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"compatible ASR request failed ({exc.code}): {detail[-2000:]}") from exc
    return result["choices"][0]["message"].get("content", "").strip()


def transcribe(audio: Path, model_name: str, language: str | None, chunk_seconds: int = 60) -> dict[str, Any]:
    """Call a DashScope-style compatible chat endpoint with data-URI audio.

    The endpoint has a request-size limit, so WAV input is sent in independent
    chunks. The response format has no timestamps; chunks are retained as
    ordered segments for downstream inspection.
    """
    mime_type = mimetypes.guess_type(audio.name)[0] or "audio/wav"
    if audio.suffix.lower() != ".wav":
        text = _compatible_chat_request(audio.read_bytes(), mime_type, model_name, language)
        return {"language": language, "segments": [{"text": text}], "text": text}
    with wave.open(str(audio), "rb") as source:
        channels, sample_width, frame_rate = source.getnchannels(), source.getsampwidth(), source.getframerate()
        frames_per_chunk = frame_rate * chunk_seconds
        segments: list[dict[str, Any]] = []
        while True:
            frames = source.readframes(frames_per_chunk)
            if not frames:
                break
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as chunk:
                chunk.setnchannels(channels)
                chunk.setsampwidth(sample_width)
                chunk.setframerate(frame_rate)
                chunk.writeframes(frames)
            text = _compatible_chat_request(buffer.getvalue(), "audio/wav", model_name, language)
            start = len(segments) * chunk_seconds
            segments.append({"start": start, "end": start + len(frames) / (channels * sample_width * frame_rate), "text": text})
    return {"language": language, "segments": segments, "text": " ".join(item["text"] for item in segments).strip()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=os.getenv("ASR_MODEL", "qwen3-asr-flash"))
    parser.add_argument("--language", default=os.getenv("ASR_LANGUAGE", "zh"))
    args = parser.parse_args()
    payload = transcribe(args.audio, args.model, args.language)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
