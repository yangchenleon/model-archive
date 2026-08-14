# Model Archive
个人拼装模型资产库的最小可用版本。发行物目录与实际拥有的盒装资产分开记录，并保留收藏决策和状态履历。
## Start
```bash
cp .env.example .env
docker compose up --build -d
```
- API documentation: <http://localhost:18000/docs>
- Database browser (Adminer): <http://localhost:18080>
Adminer connection details: system `PostgreSQL`, server `db`, and the database/user/password from `.env`.
## Data model
| Table | Purpose |
| --- | --- |
| `catalog_items` | A concrete, distinguishable release: maker, line, scale, box-art/version and kit details. |
| `assets` | One physical box or built model in the collection. Multiple assets may point to the same catalog item. |
| `collection_targets` | Per-collection decision for a catalog item: collect, consider, skip, or owned. |
| `asset_events` | Append-only lifecycle events such as acquisition, build completion, return, or trade. |
The initial four-table boundary is intentional. Later migrations can introduce makers, source references, storage locations, build sessions, media, and a normalized collection-definition table without changing asset identities.
## Import personal data
Personal data is ignored by Git. Put a seed JSON file in `data/seed/`, then run:
```bash
docker compose exec api python -m app.scripts.import_seed /app/data/seed/initial_snapshot.json
```
The importer is idempotent on `catalog_key` and `asset_key`. Its supported JSON format is defined by [`backend/app/scripts/import_seed.py`](backend/app/scripts/import_seed.py).
For the supplied diary, start from the explicit current snapshot sections (`万代资产`, `待定/收藏`, `回收`, `待置换`), not historical plans or strikethrough markers. Preserve those as source notes and backfill them later as events.
## Useful commands
```bash
docker compose logs -f api
docker compose down
docker compose down -v  # also deletes the local PostgreSQL volume
```
