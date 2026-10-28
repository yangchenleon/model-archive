# Model Archive

个人拼装模型产品目录系统。当前阶段只建设产品目录；资产、愿望单和事件功能暂缓。

## Start

```bash
cp .env.example .env
docker compose up --build -d
```

- API documentation: <http://localhost:18000/docs>
- Database browser (Adminer): <http://localhost:18080>
- Product archive frontend: <http://localhost:5173>

Adminer connection details: system `PostgreSQL`, server `db`, and the database/user/password from `.env`.

## Frontend

The Vue frontend reads the product directory through `/api/v1/products`; product filters and the product detail panel therefore use live database data. Three working pages sit beside the catalog: **入库审核** (`/#review`) turns extracted mentions into products (map / create / skip, with video deep links), **后台管理** (`/#admin`) edits/deletes products through transactional API calls (deleting a product returns linked review items to the queue), and **我的资产** (`/#inventory`) records owned kits, their state, and the stickers that go on the storage bags. See [docs/review-workflow.md](docs/review-workflow.md) and [docs/asset-and-labels.md](docs/asset-and-labels.md). Wish list and activity pages are still frontend mockups.

For frontend-only development:

```bash
cd frontend
npm install
npm run dev
```

## Current model

| Table | Purpose |
| --- | --- |
| `products` | The product catalog: maker, code, line, name, detail, source, free-text `price`, `created_at`. No status or history columns. |
| `review_items` | Persistent ingestion audit queue from `outputs/products/products.json`: source video/second/evidence plus `pending / mapped / created / skipped`. Mapping only links the mention to a product; it never edits the product. |
| `assets` | One row per owned kit: `code` (`K7M2QF`, six random Crockford Base32 chars), `state` (pending / keep / displayed / stored / sold), purchase / build / sale facts and the review. |
| `tags` | One physical sticker per bag (`K7M2QF`, `K7M2QF-2`). Codes derive from the asset code and are never reused. |
| `asset_state_changes` | Audit of state transitions; field edits are not recorded. |

## Create products via API

There is no built-in CSV importer. The catalog is written through the API, either
one product at a time or as an atomic batch:

```bash
# single
curl -X POST http://localhost:18000/api/v1/products \
  -H 'Content-Type: application/json' \
  -d '{"kit_name":"MG 1/100 巴扎姆","manufacturer":"万代","source":"手动录入"}'

# batch (all-or-nothing; any duplicate returns 409)
curl -X POST http://localhost:18000/api/v1/products/bulk \
  -H 'Content-Type: application/json' \
  -d '[{"kit_name":"A","source":"手动录入"},{"kit_name":"B","source":"手动录入"}]'
```

CSV/Excel/JSON parsing and format validation belong to the external tool that
produces the payload; this project only accepts clean product fields.

## Source ingestion

The composable video-to-CSV pipeline lives in [`tools/README.md`](tools/README.md).
It downloads a Bilibili source, extracts audio, runs ASR, and asks an optional
OpenAI-compatible LLM to produce reviewable CSV rows. Those rows are not imported
by this project — adapt them to the API above if needed.

## Tests

```bash
cd backend
../.venv/bin/python -m pytest tests -q
```

The suite talks to the dev database on `localhost:15432` and rolls every test
back, so it leaves no rows behind.

## Useful commands

```bash
docker compose logs -f api
docker compose down
docker compose down -v  # also deletes the local PostgreSQL volume
```
