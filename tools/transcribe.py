"""Transcribe audio locally, through OpenAI, or a compatible chat ASR API."""
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


def transcribe_local(audio: Path, model_name: str, language: str | None) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper is unavailable; install tools/requirements.txt or use --provider openai") from exc
    model = WhisperModel(model_name, device=os.getenv("WHISPER_DEVICE", "auto"), compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"))
    segments, info = model.transcribe(str(audio), language=language, vad_filter=True)
    result = [{"start": segment.start, "end": segment.end, "text": segment.text.strip()} for segment in segments]
    return {"language": info.language, "language_probability": info.language_probability, "segments": result, "text": " ".join(item["text"] for item in result)}


def transcribe_openai(audio: Path, model_name: str, language: str | None) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for --provider openai")
    boundary = "----model-archive-form"
    content = audio.read_bytes()
    # Keep the local model default (`small`) usable when only the provider is
    # switched; hosted transcription endpoints expect an API model name.
    api_model = model_name if model_name in {"whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"} else "whisper-1"
    fields = [("model", api_model), ("response_format", "verbose_json")]
    if language:
        fields.append(("language", language))
    body = bytearray()
    for name, value in fields:
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{audio.name}\"\r\nContent-Type: audio/wav\r\n\r\n".encode())
    body.extend(content)
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    request = urllib.request.Request(os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/audio/transcriptions", data=bytes(body), method="POST", headers={"Authorization": f"Bearer {api_key}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.loads(response.read())
    return {"language": payload.get("language"), "segments": payload.get("segments", []), "text": payload.get("text", "")}


def _compatible_chat_request(audio_data: bytes, mime_type: str, model_name: str, language: str | None) -> str:
    api_key = os.getenv("ASR_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("ASR_BASE_URL")
    if not api_key:
        raise RuntimeError("ASR_API_KEY (or DASHSCOPE_API_KEY) is required for --provider compatible-chat")
    if not base_url:
        raise RuntimeError("ASR_BASE_URL must point to the compatible /v1 endpoint")
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


def transcribe_compatible_chat(audio: Path, model_name: str, language: str | None, chunk_seconds: int = 60) -> dict[str, Any]:
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


def transcribe(audio: Path, provider: str, model_name: str, language: str | None) -> dict[str, Any]:
    if provider == "local":
        return transcribe_local(audio, model_name, language)
    if provider == "openai":
        return transcribe_openai(audio, model_name, language)
    if provider == "compatible-chat":
        local_model_names = {"tiny", "base", "small", "medium", "large-v2", "large-v3"}
        compatible_model = os.getenv("COMPATIBLE_ASR_MODEL", "qwen3-asr-flash") if model_name in local_model_names else model_name
        return transcribe_compatible_chat(audio, compatible_model, language)
    raise ValueError(f"unsupported ASR provider: {provider}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", choices=("local", "openai", "compatible-chat"), default=os.getenv("ASR_PROVIDER", "local"))
    parser.add_argument("--model", default=os.getenv("WHISPER_MODEL", "small"))
    parser.add_argument("--language", default=os.getenv("ASR_LANGUAGE", "zh"))
    args = parser.parse_args()
    payload = transcribe(args.audio, args.provider, args.model, args.language)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
