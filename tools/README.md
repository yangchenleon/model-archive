# Source ingestion pipeline

The pipeline turns a video URL into the product CSV used by the archive:

```text
download_bilibili -> extract_audio -> transcribe -> extract_products
```

## Background and scope

This project uses source videos to populate the existing product-directory CSV
contract. The ingestion tools do not write directly to PostgreSQL: they create
reviewable artifacts first, and the existing CSV importer remains the database
boundary. This keeps source retrieval, speech recognition, LLM extraction and
database writes independently replaceable.

The current source adapter is Bilibili. A single video URL and a Bilibili
season/list URL are both supported. Season enumeration is intentionally done
with yt-dlp's flat-playlist mode, then each video is processed independently so
one unavailable or rate-limited video does not discard the rest of the batch.

## Design

`download_bilibili` uses yt-dlp for the extractor and persists the original
metadata. `extract_audio` uses ffmpeg to merge/normalize media into mono 16 kHz
WAV. `transcribe` supports local faster-whisper, OpenAI-style multipart ASR,
and the tested DashScope-compatible Qwen `input_audio` chat API. The compatible
provider sends WAV data as a Base64 data URI and splits it into 60-second
requests to stay below request-size limits.

`extract_products` sends only useful metadata (title, uploader, description,
and source URL) plus the joined transcript; it deliberately excludes yt-dlp's
large signed format URLs. The LLM must return the archive's eight CSV columns.
Empty product arrays are rejected instead of creating an apparently successful
empty CSV. A video with no product-level speech is recorded as a warning and
should be excluded from database import.

The batch orchestrator writes a durable `batch/summary.json` with completed,
failed and warning entries. `--retry --start N` retries failed and pending
entries in the selected range while preserving successful entries. The output
directory is ignored by git because it contains large downloaded media and
transcripts; only reviewed CSV files should be copied to `imports/`.

## Image-only videos

ASR can only recover spoken content. Some review videos are image slideshows
with little or no narration; their transcript may be too short to identify
products, and the product extractor correctly returns no rows. Handling those
videos requires a separate visual pipeline (frame sampling, OCR and/or a
vision-language model) and is intentionally outside this speech pipeline.
Do not treat an empty CSV as valid product data.

## Artifact layout

```text
outputs/<batch>/
  videos/<BV ID>/video/       downloaded media and yt-dlp metadata
  videos/<BV ID>/audio/       normalized WAV
  videos/<BV ID>/transcript/  transcript JSON and joined TXT
  videos/<BV ID>/csv/         title-named product CSV
  batch/summary.json          batch status and warnings
```

For a Bilibili season/list, use the batch orchestrator. Each video is isolated
under `videos/<BV ID>/`; its CSV is named from the sanitized video title and
the joined ASR text is saved as `transcript/<title>.txt`:

```bash
.venv-tools/bin/python -m tools.batch_pipeline \
  'https://space.bilibili.com/28175471/lists/4951163?type=season' \
  --work-dir artifacts/season-4951163 \
  --asr-provider compatible-chat
```

Progress and failures are written to `batch/summary.json`. Resume a subset
with `--start N --limit M`; retry failed and pending entries in a range with
`--retry --start N`.

Install the optional Python tools and the system `ffmpeg` executable:

```bash
python3 -m venv .venv-tools
.venv-tools/bin/pip install -r tools/requirements.txt
```

Run the supplied Bilibili example without external LLM credentials (the final
CSV is a reviewable, metadata-only row):

```bash
.venv-tools/bin/python -m tools.pipeline https://www.bilibili.com/video/BV1bJXSYZE3z \
  --work-dir artifacts/bv1bJXSYZE3z --llm-provider none
```

For local ASR, `faster-whisper` downloads the selected model on first use. The
default is `small`; use `--asr-model medium` or `large-v3` when accuracy matters.
For a hosted ASR/LLM, set the corresponding API key and use
`--asr-provider openai` and the default `--llm-provider openai`; the hosted ASR
falls back to `whisper-1` unless `--asr-model` is an API transcription model
name. `ASR_BASE_URL` and `LLM_BASE_URL` can point at OpenAI-compatible gateways.
Login-only Bilibili videos can use `--cookies` with a Netscape-format cookie
export.

For the tested DashScope-compatible Qwen ASR endpoint, use:

```bash
export ASR_API_KEY='...'
export ASR_BASE_URL='https://llm-.../compatible-mode/v1'
export LLM_API_KEY='...'
export LLM_BASE_URL='http://api.chinalco.com.cn/aimiddle/v1'
export LLM_MAX_TOKENS=4096
.venv-tools/bin/python -m tools.pipeline VIDEO_URL --asr-provider compatible-chat
```

This provider sends `data:audio/wav;base64,...` in `input_audio.data` and
automatically splits WAV input into 60-second requests. It defaults to
`qwen3-asr-flash`; override it with `--asr-model` or `COMPATIBLE_ASR_MODEL`.

Each stage is independently runnable and writes stable artifacts under the
work directory. The CSV has the exact columns from
`templates/csv/products-manual-template.csv`; inspect it before importing:

```bash
docker compose exec api python -m app.scripts.import_products_csv /app/imports/products.csv
```

The downloader uses yt-dlp's Bilibili extractor, which may still require
cookies for restricted videos or fail when Bilibili changes its API. The tools
surface the original command error so a job runner can retry or mark the job
for manual handling.
