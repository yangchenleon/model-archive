# Model Archive

个人拼装模型档案：产品目录（厂家/系列分类）、资产与标签、收藏集。愿望单和活动记录仍暂缓。

## Start

```bash
cp .env.example .env
docker compose up --build -d
```

- API documentation: <http://localhost:18000/docs>
- Database browser (Adminer): <http://localhost:18080>
- Product archive frontend: <http://localhost:5173>
- Deploy to another host + import a database dump: [docs/deploy-and-restore.md](docs/deploy-and-restore.md)
- One-page deployment handoff for the current dataset: [docs/deployment-handoff.md](docs/deployment-handoff.md)
- Manufacturer directory assessment (historical): [docs/manufacturer-normalization.md](docs/manufacturer-normalization.md)
- Manufacturer/series taxonomy (implemented): [docs/manufacturer-and-line-taxonomy.md](docs/manufacturer-and-line-taxonomy.md)
- 78dm scraping and RG import runbook: [docs/78dm-scraping.md](docs/78dm-scraping.md)
- namu.wiki RG reference (crawl method, data shape, mapping table): [docs/namu-wiki-rg.md](docs/namu-wiki-rg.md)

Adminer connection details: system `PostgreSQL`, server `db`, and the database/user/password from `.env`.

## Frontend

The Vue frontend reads the product directory through `/api/v1/products`; the directory is manufacturer-first (`/#directory` shows a manufacturer menu, then products grouped under that maker, with series as secondary chips). Working pages sit beside the catalog: **入库审核** (`/#review`) turns extracted mentions into products (map / create / skip, with video deep links), **后台管理** (`/#admin`) edits/deletes products through transactional API calls, **厂家管理** (`/#taxonomy`) maintains manufacturer category/tier/sort and their flat series lists, **我的资产** (`/#inventory`) records owned kits, their state, and the stickers that go on the storage bags, and **收藏集** (`/#collections`) compares a human-defined product list against those assets. See [docs/review-workflow.md](docs/review-workflow.md), [docs/manufacturer-and-line-taxonomy.md](docs/manufacturer-and-line-taxonomy.md), [docs/asset-and-labels.md](docs/asset-and-labels.md), and [docs/collection-system.md](docs/collection-system.md). Wish list and activity pages are still frontend mockups.

For frontend-only development:

```bash
cd frontend
npm install
npm run dev
```

## Current model

| Table | Purpose |
| --- | --- |
| `manufacturers` | Canonical maker: name, category (`gundam / guomo / ko`, null = unclassified), tier (1–3, larger sorts later), hidden `sort_order`, description. No alias table: a wrong name is data to fix. |
| `product_lines` | Flat series owned by one manufacturer; `(manufacturer_id, name)` unique. HG, HGUC and HG GTO are separate series. Deleting one sets its products to NULL (shown as 未知); no hierarchy. |
| `products` | The product catalog: `manufacturer_id` (required), `product_line_id` (nullable), `work` (optional IP/work, e.g. EVANGELION), `release_channel` (regular / pb / base / event / limited, NULL = unknown), `edition` (the `<ver>` label shown in parentheses, e.g. `GCP` / `基地配色`), `appearance` (a scalable visual-effect label: `彩透` / `透明` / `电镀` / `特殊涂层` / `未启动` / `环保`…; free text, NULL = none), `release_date` (first release date; reprint notes live in `detail`), `aliases` (source names, semicolon-separated: the 78dm name and any former display name), code, name, detail, source, free-text `price`, `created_at` (internal audit only). `kit_name` is the house display name, written as `name（ver）[appearance]` with `·` joining sub-entities (e.g. `扎古II·高机动型·强尼莱登专用`); it is standardised by hand and deliberately not a copy of the Bandai name. Identity is `(manufacturer_id, product_line_id, kit_name)` at the service layer; the same name in a different series is a different product, and a NULL line is its own bucket. Work, channel, edition and appearance are metadata, not identity. |
| `review_items` | Persistent ingestion audit queue from `outputs/products/products.json`: source video/second/evidence plus `pending / mapped / created / skipped`. Raw `brand` / `line` are kept, plus optional matched manufacturer/line IDs. Mapping only links the mention to a product; it never edits the product. |
| `assets` | One row per owned kit: `code` (`K7M2Q`, five random Crockford Base32 chars), `state` (pending / keep / displayed / stored / sold), purchase / build / sale facts and the review. |
| `tags` | One physical sticker per bag (`R4TB9`). Every sticker has its own random code, never reused. Selling an asset sets `retired_at`: the sticker leaves the print queues and cannot be reprinted, but the row stays as history. |
| `asset_state_changes` | Audit of state transitions; field edits are not recorded. |
| `collections` | A human-defined set: title and description, nothing else. No status, no start/target dates, no difficulty column — completion is derived from assets, and difficulty belongs in the description. |
| `collection_items` | One existing product in a collection, plus a plan note. `product_id` is required and `ON DELETE CASCADE`: there are no placeholder targets. Progress is derived from `assets`; sold rows do not count and multiple copies count once. |

## Create products via API

There is no built-in CSV importer. The catalog is written through the API, either
one product at a time or as an atomic batch:

```bash
# find the manufacturer id (create it in /#taxonomy first if missing)
curl 'http://localhost:18000/api/v1/manufacturers?q=万代'

# single
curl -X POST http://localhost:18000/api/v1/products \
  -H 'Content-Type: application/json' \
  -d '{"kit_name":"MG 1/100 巴扎姆","manufacturer_id":"<manufacturer-uuid>","source":"手动录入"}'

# batch (all-or-nothing; any duplicate returns 409)
curl -X POST http://localhost:18000/api/v1/products/bulk \
  -H 'Content-Type: application/json' \
  -d '[{"kit_name":"A","manufacturer_id":"<manufacturer-uuid>","source":"手动录入"},{"kit_name":"B","manufacturer_id":"<manufacturer-uuid>","source":"手动录入"}]'
```

`product_line_id` is optional; omit it or send `null` for 未知. A line must
belong to the chosen manufacturer. `work` is optional free text for the IP;
for 万代 products the default is `高达`, while non-Gundam works are explicit.
`release_date` is an optional ISO date (`YYYY-MM-DD`) and only the first release
date is stored, with reprint notes kept in `detail`. Both are metadata, not
part of product identity.
`release_channel` is optional too:
`regular` / `pb` / `base` / `event` / `limited`; omit or send `null` for 未知.
`edition` is the `<ver>` label that appears in parentheses in the display name
(free text; `regular` products keep `普通版`). `appearance` is a free-text
visual-effect label (`彩透` / `电镀` / `未启动`…), not a closed enum.
`aliases` keeps source names separated by `;` — the 78dm name plus any former
display name. All are optional metadata, not part of duplicate detection.

> **Re-syncing an external catalogue (78dm etc.) must look products up by
> `aliases`, not by `kit_name`.** Display names are standardised by hand, so a
> 78dm title will usually not match `kit_name` any more; matching on the display
> name creates duplicates. Write the incoming title into `aliases` as well. The digit-only `product_code` for
万代 regular products is a one-off data cleanup for the current 78dm import,
not a general API rule; non-Bandai codes such as `MNP-XH01` are preserved.

CSV/Excel/JSON parsing and format validation belong to the external tool that
produces the payload; this project only accepts clean product fields. The
importer must resolve `manufacturer_id` / optional `product_line_id` first; it
must not rely on free-text maker names or auto-create manufacturers.

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
