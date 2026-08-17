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

The Vue frontend reads the product directory through `/api/v1/products`; product filters and the product detail panel therefore use live database data. Asset inventory, wish list, and activity pages are explicitly marked frontend mockups until those modules are designed.

For frontend-only development:

```bash
cd frontend
npm install
npm run dev
```

## Current model

| Table | Purpose |
| --- | --- |
| `products` | One distinguishable product release: maker, type, line, version, detail and source. |
| `assets` | Reserved for future physical-inventory work; currently no user import flow. |
| `asset_events` | Reserved for future asset history. |

## Import products

Follow [`docs/csv-workflow.md`](docs/csv-workflow.md), then run:

```bash
docker compose exec api python -m app.scripts.import_products_csv /app/imports/products.csv --source 初始化测试
```

## Source ingestion

The composable video-to-CSV pipeline lives in [`tools/README.md`](tools/README.md).
It downloads a Bilibili source, extracts audio, runs ASR, and asks an optional
OpenAI-compatible LLM to produce the same CSV columns used by the importer.
Generated CSV files should be reviewed before copying them to `imports/`.

## Useful commands

```bash
docker compose logs -f api
docker compose down
docker compose down -v  # also deletes the local PostgreSQL volume
```
