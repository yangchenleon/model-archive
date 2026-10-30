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
  `imports/78dm/341672/products.json`. See
  [docs/78dm-scraping.md](../docs/78dm-scraping.md).
- `import_78dm_mg.py` — dry-run by default; `--apply` replaces `万代 / MG` and
  `万代 / MGEX` from `imports/78dm/2328/products.json`.
- `seed_review_queue.py` — idempotent seed of `review_items` from
  `outputs/products/products.json`. See
  [docs/review-workflow.md](../docs/review-workflow.md).
- `eval_ko_prompt.py` — targeted KO/third-party brand-attribution regression
  check (`python -m tests.eval_ko_prompt`).

Do not assume the other scripts here are safe to run; many are historical
investigations that hit the dev database or local artifacts.
