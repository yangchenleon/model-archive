# One-off task scripts

This directory is for concrete, historical or destructive task scripts. It is
**not** the pytest suite; backend tests live in `backend/tests/` and run with:

```bash
cd backend
../.venv/bin/python -m pytest tests -q
```

Run scripts from the repository root so relative paths and the `backend` import
path resolve correctly.

Current operational scripts:

- `import_78dm_rg.py` — dry-run by default; `--apply` replaces the current
  `万代 / RG` catalog with the 78dm manifest in
  `outputs/78dm/341672/products.json`. See
  [docs/78dm-scraping.md](../docs/78dm-scraping.md).
- `import_78dm_mg.py` — dry-run by default; `--apply` replaces `万代 / MG` and
  `万代 / MGEX` from `outputs/78dm/2328/products.json`.
- `import_78dm_blokees.py` — dry-run by default; `--apply` imports the 45
  `布鲁可 / 传奇版` products from `outputs/78dm/blokees-legendary/products.json`.
- `import_78dm_new_mfgs.py` — dry-run by default; `--apply` imports 116 kit rows
  for 壹理创玩 / 创模玩 / 所罗门模玩 / 圣斯基 / 御模道 from
  `outputs/78dm/new-mfgs/products.json`.
- `split_eva_blindbox.py` — dry-run by default; `--apply` replaces the 圣斯基
  `EVA 超可动拼装盲盒端` row with its 7 known variants (6 regular + hidden).
- `import_78dm_tms.py` — dry-run by default; `--apply` imports 万象聚变 `TMS系列`
  and GM-GODOMO kits from `outputs/78dm/tms/products.json`.
- `import_xiaoxing.py` — dry-run by default; `--apply` adds/completes 哮星
  `机神·星云`, `科拉达`, `仲裁者` (line `机神`).
- `import_78dm_dileike.py` — dry-run by default; `--apply` completes 迪雷克
  `斑鸠` / `翠鸟` / `孔雀` (line `1/100`).
- `seed_review_queue.py` — idempotent seed of `review_items` from
  `outputs/products/products.json`. See
  [docs/review-workflow.md](../docs/review-workflow.md).
- `eval_ko_prompt.py` — targeted KO/third-party brand-attribution regression
  check (`python -m tests.eval_ko_prompt`).

Do not assume the other scripts here are safe to run; many are historical
investigations that hit the dev database or local artifacts.
