# CSV Inventory Workflow

Keep the daily diary as a narrative record. Record inventory facts only in the four CSV files below. Copy [`templates/csv`](../templates/csv) into the Git-ignored `data/drafts/<snapshot-name>/` directory before editing.

## 1. `catalog_items.csv`

One row per distinguishable release, not per mobile suit. A different box art, colorway, limited edition, or manufacturer code gets a separate row when you want to collect it separately.

```csv
catalog_key,manufacturer,origin_type,product_line,scale,kit_name,variant_name,manufacturer_code,subject_name,box_art_key,source_note,confidence
bandai.rg.god-gundam,万代,official,RG,,神高达（GOD）,,,,日报：万代资产 / 待拼&收藏,reported
```

`catalog_key` is immutable ASCII identity. Use lowercase words separated by `.` or `-`, for example `star.hg.unicorn-purple`. `confidence` is `reported`, `verified`, or `uncertain`.

## 2. `assets.csv`

One row per physical box or completed model. You may set `quantity` above 1 only when every copy has exactly the same state and location. Otherwise use multiple rows.

```csv
asset_key,catalog_key,status,condition,quantity,storage_location,acquired_on,purchase_price,notes
asset.bandai.rg.god-gundam.001,bandai.rg.god-gundam,owned_unbuilt,sealed,1,家中,,,,
```

Allowed statuses: `wanted`, `ordered`, `owned_unbuilt`, `building`, `built`, `to_sell`, `to_trade`, `sold`, `returned`, `review`.

## 3. `collection_targets.csv`

This is the collection rule in concrete form. A kit can belong to several named collections such as `盒绘收藏`, `星动独角兽`, or `万代资产`.

```csv
collection_name,catalog_key,decision,priority,reason,rule_version
盒绘收藏,bandai.rg.god-gundam,owned,2,当前已拥有,2026-08-14
```

`decision` is one of `collect`, `consider`, `skip`, `owned`, `duplicate`. Priorities are `1` through `5`, where `1` is highest.

## 4. `asset_events.csv`

Only record meaningful changes. Do not manufacture historical precision: use an empty date when the diary does not establish one. If the event changes present state, update `assets.csv` too.

```csv
asset_key,event_type,occurred_at,from_status,to_status,source_note,metadata_json
asset.bandai.rg.god-gundam.001,acquired,2026-08-14T00:00:00+08:00,,owned_unbuilt,购入记录,{}
```

Allowed event types: `acquired`, `opened`, `build_started`, `build_completed`, `listed`, `traded`, `sold`, `returned`, `status_corrected`, `note`.

## Import

Validate the draft by importing it. The importer is idempotent for catalog items, assets, collection targets, and identical events.

```bash
docker compose exec api python -m app.scripts.import_csv /app/data/drafts/current_snapshot
```

The directory must contain all four CSVs, even if some only have their header row. Personal drafts remain under `data/` and are ignored by Git.

## How to rewrite the diary

Use [`templates/daily-log.md`](../templates/daily-log.md) for decisions and context, then link it in `source_note`; do not duplicate inventory lists. A useful entry has only: new arrivals, completed builds, changed collection decisions, and a short free-form note about why. The CSV files become the authoritative current state.
