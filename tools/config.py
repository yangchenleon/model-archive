"""Environment loading and provider settings for the source-ingestion tools.

The repository root ``.env`` is loaded for ``python -m tools.*`` commands.
Explicitly exported environment variables always win over values in the file.
This module intentionally avoids a third-party dotenv dependency.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    # Support the usual `KEY=value # comment` form without treating URL fragments
    # as comments when there is no preceding whitespace.
    return re.sub(r"\s+#.*$", "", value).strip()


def load_env(path: Path | None = None, *, override: bool = False) -> Path | None:
    """Load simple dotenv assignments and return the file used, if any."""
    env_path = (path or ENV_FILE).expanduser()
    if not env_path.is_file():
        return None
    for line_number, line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"Invalid environment assignment at {env_path}:{line_number}")
        key, raw = line.split("=", 1)
        key = key.strip()
        if not _KEY_RE.fullmatch(key):
            raise ValueError(f"Invalid environment key {key!r} at {env_path}:{line_number}")
        if override or key not in os.environ:
            os.environ[key] = _value(raw)
    return env_path


def active_provider_config() -> dict[str, str | bool | None]:
    """Return non-secret provider settings for diagnostics and logs."""
    load_env()
    return {
        "env_file": str(ENV_FILE) if ENV_FILE.is_file() else None,
        "asr_provider": os.getenv("ASR_PROVIDER", "local"),
        "asr_model": os.getenv("COMPATIBLE_ASR_MODEL") or os.getenv("WHISPER_MODEL", "small"),
        "asr_base_url_configured": bool(os.getenv("ASR_BASE_URL")),
        "asr_api_key_configured": bool(os.getenv("ASR_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")),
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "llm_model": os.getenv("LLM_MODEL", "Qwen3.5-35B-A3B"),
        "llm_base_url_configured": bool(os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")),
        "llm_api_key_configured": bool(os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")),
        "llm_max_tokens": os.getenv("LLM_MAX_TOKENS", "4096"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Show active model provider settings without printing secrets")
    parser.add_argument("--env-file", type=Path, help="Load a different dotenv file")
    args = parser.parse_args()
    if args.env_file:
        load_env(args.env_file)
    import json

    print(json.dumps(active_provider_config(), ensure_ascii=False, indent=2))


load_env()


if __name__ == "__main__":
    main()
