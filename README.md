# Model Archive

个人拼装模型产品目录系统。当前阶段只建设产品目录；资产、愿望单和事件功能暂缓。

## Start

```bash
cp .env.example .env
docker compose up --build -d
```

- API documentation: <http://localhost:18000/docs>
- Database browser (Adminer): <http://localhost:18080>

Adminer connection details: system `PostgreSQL`, server `db`, and the database/user/password from `.env`.

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

## Useful commands

```bash
docker compose logs -f api
docker compose down
docker compose down -v  # also deletes the local PostgreSQL volume
```
