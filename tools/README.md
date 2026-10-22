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
WAV. `transcribe` sends it to the configured Qwen `input_audio` chat API as a
Base64 data URI, splitting it into 60-second requests to stay below
request-size limits.

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
products, and the product extractor correctly returns no rows. Use the visual
pipeline to create a compact, reviewable collection of the distinct slides:

```text
download_bilibili (optional) -> extract_screenshots
```

`extract_screenshots` samples once per second by default and compares each
sample to the preceding second. The comparison uses the 15%-75% vertical band,
so bottom subtitles and player overlays do not cause duplicate captures. It
saves the first frame and every subsequent frame whose normalized mean pixel
difference is at least `0.08`; full, uncropped JPEGs go in `screenshots/frames`
and `screenshots/manifest.json` records timestamps and difference scores.

To test a video that has already been downloaded, provide `--media` and the
pipeline will skip yt-dlp entirely:

```bash
.venv-tools/bin/python -m tools.screenshot_pipeline \
  --media outputs/season-4951163/videos/BV1zoZiYXEXw/video/BV1zoZiYXEXw.mp4 \
  --work-dir outputs/season-4951163/videos/BV1zoZiYXEXw
```

For an already downloaded season, process every local video with a durable
summary under `batch/screenshot-summary.json`. Existing manifests are skipped;
add `--force` to regenerate them:

```bash
.venv-tools/bin/python -m tools.batch_screenshot_pipeline \
  --work-dir outputs/season-4951163
```

Tune `--threshold` upward to retain fewer, more different slides, or downward
to retain small changes. `--interval`, `--crop-top`, and `--crop-bottom` are
available when a source's timing or subtitle position differs. The screenshots
are visual source artifacts, not CSV rows; OCR or a vision-language stage can
consume the selected frames afterward. Do not treat an empty CSV as valid
product data.

## Daily report: download-only stage

`download_daily_videos` performs only source retrieval for the Daily Toy News
archive, so the expensive ASR/LLM stages can be batched separately later:

```bash
.venv-tools/bin/python -m tools.download_daily_videos \
  --start-date 2026-09-18 --end-date 2026-10-22 \
  --listing /tmp/space_all.json \
  --manifest outputs/daily_download_manifest.json
```

It scores the UP space uploads per calendar day with
`tools.filter_daily_videos`, keeps the best "daily news" candidate, and writes
the established layout without touching `audio/`, `transcript/` or
`daily_report.json`:

```text
outputs/daily_reports/<YYYYMMDD>_<BV ID>/
  video/<BV ID>.mp4
  video/<BV ID>.info.json
```

`tools.daily_pipeline` reads that layout: when `<report>/video/<BV>.mp4` already
exists it reuses the file instead of downloading again, and it always moves the
media out of `_temp` into the report folder. Skipping an already processed video
is decided from the existing `daily_report.json` before any download starts.

Days that already have a report folder are skipped, so the command is
idempotent. `--listing` reuses a cached space listing instead of re-paginating
Bilibili; `--dry-run` prints the selection. Each item records every same-day
candidate in the manifest, so a later stage can swap a rejected pick.

Regenerate the cache with `.venv-tools/bin/python -m tools.fetch_space_videos
--max-items 120 --output /tmp/space_all.json`. Keep `yt-dlp` current: a 2026-07
build returned HTTP 412 from the space API while 2026.10.21 succeeded with no
cookies.

## Daily report: batch ASR stage

`batch_daily_reports` walks `outputs/daily_reports` and runs the audio → ASR →
LLM chain for every folder that has `video/*.mp4` but no `daily_report.json`:

```bash
.venv-tools/bin/python -m tools.batch_daily_reports --interval 5
```

It reuses the downloaded media (no second download), skips days that already
have a report, keeps going after a failure, and records progress in
`outputs/daily_batch_status.json` plus the append-only `outputs/daily_batch.log`.
Re-running the same command retries only the folders that are still missing a
report, so `--start-date`/`--end-date` narrow it down to a date range.

## Daily report v2: mentions and product alignment

The v1 report (`extract_daily_news`) emits one free-form `news_type` per item,
which cannot answer "how did this product move from announcement to shelf".
The v2 pair replaces the post-ASR stage with an event-sourced design:

```bash
.venv-tools/bin/python -m tools.extract_daily_mentions \
  --start-date 20260823 --end-date 20260922

.venv-tools/bin/python -m tools.align_daily_mentions
```

`extract_daily_mentions` turns each transcript into atomic mentions with a
controlled `stage` (rumor → teaser → announced → preorder → released →
reprint/discontinued), an orthogonal `event` (price_change, delay, review,
accessory, payment, expo, recall, info_update), and a split identity
(`brand` / `line` / `model_name` / `variant`). Every mention also carries the
verbatim `stage_cue` that justified the stage.

`align_daily_mentions` folds mentions into product entities and keeps the full
timeline, so the product directory stays one row per product while every
pre-release update is auditable. Matching is exact key first
(brand + grade + normalized name), then fuzzy (≥ 0.90 auto, 0.80–0.90 queued as
`review.json`), with accessory variants kept as separate SKUs, stage
reconciliation for media samples, and flags for stage regressions. Artifacts:
`outputs/daily_v2/mentions/*.json`, `products.json`, `review.json`,
`summary.json`.

## Artifact layout

```text
outputs/<batch>/
  videos/<BV ID>/video/       downloaded media and yt-dlp metadata
  videos/<BV ID>/audio/       normalized WAV
  videos/<BV ID>/transcript/  transcript JSON and joined TXT
  videos/<BV ID>/csv/         title-named product CSV
  videos/<BV ID>/screenshots/ distinct full-frame JPEGs and manifest JSON
  batch/summary.json          batch status and warnings
```

For a Bilibili season/list, use the batch orchestrator. Each video is isolated
under `videos/<BV ID>/`; its CSV is named from the sanitized video title and
the joined ASR text is saved as `transcript/<title>.txt`:

```bash
.venv-tools/bin/python -m tools.batch_pipeline \
  'https://space.bilibili.com/28175471/lists/4951163?type=season' \
  --work-dir artifacts/season-4951163
```

Progress and failures are written to `batch/summary.json`. Resume a subset
with `--start N --limit M`; retry failed and pending entries in a range with
`--retry --start N`.

Install the optional Python tools and the system `ffmpeg` executable:

```bash
python3 -m venv .venv-tools
.venv-tools/bin/pip install -r tools/requirements.txt
```

Provider keys and model defaults are loaded automatically from the repository
root `.env` by `tools.config`; shell environment variables take precedence.
On WSL, credentials are also automatically loaded from the user-only file
`~/.config/model-archive/ingest.env`, before the project `.env`. This keeps
keys off a Windows-mounted project directory, which cannot enforce Unix file
permissions. Start from `.env.example`, then inspect the active non-secret
settings with:

```bash
.venv-tools/bin/python -m tools.config
```

The tool-specific settings are `ASR_API_KEY`/`ASR_BASE_URL` for Qwen ASR,
`LLM_API_KEY`/`LLM_BASE_URL` for product extraction, and the model variables
`ASR_MODEL` and `LLM_MODEL`. The actual key values are never printed by the
diagnostic command; keep `.env` private.

Run the supplied Bilibili example without external LLM credentials (the final
CSV is a reviewable, metadata-only row):

```bash
.venv-tools/bin/python -m tools.pipeline https://www.bilibili.com/video/BV1bJXSYZE3z \
  --work-dir artifacts/bv1bJXSYZE3z --llm-provider none
```

Login-only Bilibili videos can use `--cookies` with a Netscape-format cookie
export.

For the tested DashScope-compatible Qwen ASR endpoint, use:

```bash
export ASR_API_KEY='...'
export ASR_BASE_URL='https://llm-.../compatible-mode/v1'
export LLM_API_KEY='...'
export LLM_BASE_URL='http://api.chinalco.com.cn/aimiddle/v1'
export LLM_MAX_TOKENS=4096
.venv-tools/bin/python -m tools.pipeline VIDEO_URL
```

This provider sends `data:audio/wav;base64,...` in `input_audio.data` and
automatically splits WAV input into 60-second requests. It defaults to
`qwen3-asr-flash`; override it with `--asr-model` or `ASR_MODEL`.

Each stage is independently runnable and writes stable artifacts under the
work directory. The CSV must use exactly the columns
`厂商,产品编号,来源类型,产品线,模型名称,版本/配色,详情,资料来源`; inspect it before
importing:

```bash
docker compose exec api python -m app.scripts.import_products_csv /app/imports/products.csv
```

The downloader uses yt-dlp's Bilibili extractor, which may still require
cookies for restricted videos or fail when Bilibili changes its API. The tools
surface the original command error so a job runner can retry or mark the job
for manual handling.
