# Driftwatch

Change intelligence for public SaaS pricing pages. Every scrape answers one question: **did the content change, or did the page break the scraper?**

A price moving $29 → $39 is news (insight). A price moving $29 → empty because a class name moved is breakage (incident + heal). One engine emits both.

**Event:** Into the Scrape-Verse (WeMakeDevs × Bright Data), 17–23 Aug 2026.  
**Repo created:** 20 Aug 2026 (contest week; prep notes lived in a separate private repo).

## How Bright Data Scraper Studio is used

This is load-bearing. Remove Scraper Studio and there is no product.

1. **Create** — `brightdata scraper create` from this repo using `contracts/create_prompt.txt` (Discovery scraper, one URL → N tier rows). Collector ID is pinned in `.cursor/rules/collector.mdc`. The Hacker News throwaway collector `c_msm3xrpc7r50hnnob` is **not** reused.
2. **Collection API** — `POST /dca/trigger` with the ten-URL body in `contracts/day1_urls.json`, then poll `GET /dca/dataset?id=j_*`. All HTTP lives in `backend/app/brightdata/client.py`.
3. **AI Flow** — `brightdata scraper heal` / `approve` / `approve --reject`. Preview is **one row** and **omits `input`**, so we never join anchors on URL.
4. **Fixture replay** — `FIXTURE_MODE=true` replays JSON captured before kickoff (`backend/tests/fixtures/`). Those files are API responses, not contest application code.

## Detection methodology

For field `f` on host `h`, fill rate = present-and-conformant rows / n.

- Baseline: EWMA, `alpha=0.3`, window configured as `BASELINE_WINDOW_RUNS` (**8** this week — we started late; 20 is the design default).
- Two-proportion z-test vs baseline. Flag only if **z > 3.0** and **effect > 0.30**.
- Two+ fields flagged on the same host → **structure**.
- `malformed_rate > 0.5` → **structure** (e.g. every price is the string "Contact sales").
- Sparse field (`tier_price_monthly`) with ~20% empty → **healthy**. Fill collapsed to 0 → **structure** (not “Contact sales on Enterprise”).
- Values moved, fill intact → **content** insight.
- Insights on a structural host are stored `suppressed=true`.

Worked example: Linear Basic $10 → $12, other tiers unchanged, fill still ~0.75 → `content`. All four prices empty after a markup move, baseline 0.75 → `structure`, open incident.

## Self-healing

Detect → compose ≤1000-char prompt → heal → **validate preview** → approve → **verification run**.

Preview gate (cannot be the only gate; n=1):

| Level | Role |
|-------|------|
| 1 schema | **Must** — `vendor` required (anchors are `vendor`+`tier_name`) |
| 2 conformance | **Must** |
| 3 fill rate | Advisory on 1-row preview |
| 4 anchors | Opportunistic; never URL |
| 5 collateral | Soft reject |

Approve is not rollback. Verification still broken → `escalated`. Demo needs at least one genuine `closed_healed`.

## Example structured output

See [`samples/example_output.json`](samples/example_output.json).

## Running locally

Python 3.13 venv: `D:\dev\venvs\driftwatch` (not inside OneDrive).

```powershell
D:\dev\venvs\driftwatch\Scripts\Activate.ps1
cd D:\dev\driftwatch
pip install -r requirements.txt
copy .env.example .env   # then set the token; never commit .env
$env:PYTHONPATH="D:\dev\driftwatch\backend"
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 — incident timeline. **Trigger run** with `FIXTURE_MODE=true` uses HN `run1.json` (wrong schema on purpose for validator tests). Live ten-URL run: `FIXTURE_MODE=false` plus collector ID.

```powershell
pytest -q
```

Classifier evaluation prints as pytest names. Known miss: vendor moves every tier to custom pricing — ground truth `content`, detector says `structure`. We publish that.

## Data ethics

Public pricing pages only. robots.txt checked 16 Aug 2026. Fly.io excluded from the day-1 ten for capacity. Cadence: `RUN_INTERVAL_MINUTES=60`.

## AI disclosure

Architecture, contracts, and this backend were written with **Cursor** (Grok 4.6). Bright Data CLI/MCP were used in pre-hackathon learning. Humans own collector-create spend, promo code, Discord, recording, and submission.

## Limitations

No auth, one collector, no ML, no Slack. Baseline window reduced from 20 to 8 because build started 20 Aug. Second changelog collector not built (cut order: insight-feed polish, field-health depth, second collector). Validator and eval set were not cut.

## License

MIT
