# Driftwatch

**Every scrape answers one question: did the content change, or did the page break the scraper?**

A price moving $29 → $39 is news. It belongs in a change feed.
A price moving $29 → empty because a class name moved is breakage. It belongs in an incident queue, and the scraper needs repairing.

Both answers come out of the same computation, so Driftwatch runs one engine and emits both: an insight feed for humans, and a self-healing loop for the scraper.

**Event:** Into the Scrape-Verse (WeMakeDevs × Bright Data), 17–23 August 2026
**Live collector:** [`c_mt0hvfomh2bmennhd`](https://brightdata.com/cp/scrapers/c_mt0hvfomh2bmennhd) (`shopalto_products`)
**Official coding-agent prompts followed:** [anil-bd/scraper-studio-scrape-verse-hackathon-august-2026](https://github.com/anil-bd/scraper-studio-scrape-verse-hackathon-august-2026)

---

## Why this exists

Bright Data gives you a repair *mechanism*. It does not give you judgment.

When Scraper Studio finishes refactoring a collector, it sends an email that says:

> The code refactoring for your scraper has been completed successfully.
> **Review and test before deploying to production.**

That sentence is the entire problem. Something has to do the reviewing. In practice nobody does — they click approve, or they pass `--auto-approve` and never look. Driftwatch is the reviewer: it notices the breakage, quantifies it, describes it to the healer in under 1,000 characters, checks the proposed fix against declared field contracts and hand-verified anchors, and only then approves.

**This is not hypothetical.** During this hackathon a heal on our own collector returned a flawless-looking preview, was approved, and then silently destroyed a field that had been working — see [How Scraper Studio is used](#3-heal-in-place--and-the-thing-that-justifies-this-entire-project) for the receipts. The preview lied. Approving on faith made a working scraper worse.

Four steps sit between "a scraper broke" and "a scraper is fixed" — **notice, describe, validate, decide**. Scraper Studio covers the repair. Driftwatch covers the other four.

---

## How Bright Data Scraper Studio is used

Load-bearing. Remove Scraper Studio and there is no product. We followed the official prompt order: library check → minimal create → run → heal in place → approve → batch.

### 1. Create

`scraper create` against Linear's pricing page **failed twice at `code_generator`** (`c_mt0h7usvdesnctj3q`, `c_mt0hn92ue1oi96zqi`). Rather than burn the remaining build days retrying a target we did not control, we followed the official README and created a minimal two-field collector against the public demo store:

```
brightdata scraper create https://shopalto.xyz/product/aurora-wireless-headphones \
  "Extract product name and price" --pretty -o samples/create_shopalto.json
```

→ `c_mt0hvfomh2bmennhd`, status `done`. Envelope: [`samples/create_shopalto.json`](samples/create_shopalto.json).
The collector ID is pinned in [`.cursor/rules/collector.mdc`](.cursor/rules/collector.mdc) so the coding agent reuses it instead of creating new collectors.

### 2. Run

```
brightdata scraper run c_mt0hvfomh2bmennhd https://shopalto.xyz/product/aurora-wireless-headphones --pretty
```

→ `Wireless Headphones Aurora`, **$172.40 USD**. Envelope: [`samples/run_shopalto.json`](samples/run_shopalto.json).

### 3. Heal in place — and the thing that justifies this entire project

The same collector was healed to add three fields — `description`, `image_url`, `rating` — with `rating` deliberately specified as *empty when a product has no reviews yet*, because legitimate sparsity is the case a naive null-check gets wrong.

Bright Data returned `awaiting_approval` with a preview and emailed a review link. **The preview looked perfect.** All five fields populated ([`samples/heal_shopalto.json`](samples/heal_shopalto.json)):

```json
{"product_name": "Headphones Wireless Aurora",
 "price": {"value": 145.99, "currency": "USD"},
 "description": "Over-ear wireless headphones with 40 mm drivers...",
 "image_url": "https://shopalto.xyz/_next/image?url=...",
 "rating": 4.7}
```

We approved it. Then we ran the collector against the live target, and got this ([`samples/run_shopalto_after_heal.json`](samples/run_shopalto_after_heal.json)):

```json
{"product_name": "Headphones Wireless Aurora",
 "description": "Over-ear wireless headphones with 40 mm drivers...",
 "image_url": "https://shopalto.xyz/_next/image?url=...",
 "input": {"url": "https://shopalto.xyz/product/aurora-wireless-headphones"}}
```

**`price` and `rating` are gone.** The heal added the two fields we asked for and silently destroyed a field that had been working since the collector was created. The preview did not show it. The approval succeeded. The API reported `status: done`.

This is not a staged demo. It happened to us, on the organisers' own demo store, and it is the single strongest argument for everything in this repository:

- A preview is **a proposal, not a fix**. One sampled row cannot tell you what a template does across a live run.
- `--auto-approve` would have shipped this silently. So would a human glancing at a preview that looked fine.
- **Collateral damage is the failure nobody checks for.** Validation level 5 exists precisely for a fix that repairs one field and breaks another, and this is what that looks like in production.
- The verification run is the hard gate. Approval only means Bright Data accepted the diff.

So the incident did not close as healed. It went back through the composer with the specific failure attached, which is the retry path the design calls for — the most useful input a healer can get is what it did wrong last time ([`samples/heal2_shopalto.json`](samples/heal2_shopalto.json)):

> The last approved heal added description and image_url but dropped price and rating on the live run. Restore price as a numeric amount with currency, and rating as the numeric star score (empty if no reviews). Keep product_name, description, and image_url working.

Second preview restores all five fields ([`samples/heal2_shopalto.json`](samples/heal2_shopalto.json)): `price: 151.24`, `rating: 4.1`. We approved it and ran a verification run.

**It regressed again.** [`samples/run_shopalto_verified.json`](samples/run_shopalto_verified.json) returns the same three fields — `product_name`, `description`, `image_url`. Two consecutive heals, two flawless previews, two production regressions.

So the incident **did not close as healed.** It escalated with the full evidence chain, which is the designed outcome when verification fails: `approved → verifying → escalated`, never `closed_healed`. A system that reported success here would have been lying twice.

### A concrete finding about approval

Comparing the two approval envelopes turned up something worth reporting to Bright Data. `completed_steps` differs:

| Approval | Final steps |
|---|---|
| [heal 1](samples/approve_shopalto.json) | `... user_approval`, **`save_new_template`** |
| [heal 2](samples/approve2_shopalto.json) | `... user_approval` |

Heal 1 changed live behaviour; heal 2 did not, and its approval never reached `save_new_template`. That is consistent with approval and deployment being separate steps, and with `status: done` being returned either way. We are stating this as an observation with the envelopes attached, not a proven root cause — but it is precisely the kind of thing that only surfaces when something independently verifies production after an approval.

**Which is the point.** Across both attempts, the only mechanism that noticed anything was wrong was the verification run against the live target. The preview said fine. The API said `done`. Production said otherwise.

### 4. Batch

`contracts/shopalto_urls.json` holds the ten-product list for the batch step.
`contracts/day1_urls.json` holds ten verified public SaaS pricing URLs, kept for the pricing-page collector the engine was designed against.

### 5. Collection API

Scheduled runs go through `POST /dca/trigger` + `GET /dca/dataset` in [`backend/app/brightdata/client.py`](backend/app/brightdata/client.py). All network I/O to Bright Data lives in that one module; business logic never calls HTTP.

---

## Detection methodology

Scraper Studio schemas are per-row best-effort: a row with no value for a field comes back with the field omitted rather than fabricated. So a missing value is genuinely ambiguous — the scraper may have broken, or this particular row may legitimately have nothing to show. Row-level null checks cannot tell those apart. Population statistics can.

For field `f` on host `h`, **fill rate** is the proportion of rows where the value is present *and* conformant to the field's contract.

- **Baseline:** EWMA over previous runs, `alpha = 0.3`.
- **Significance:** two-proportion z-test of the current run against the baseline, using the baseline's real observed row count.
- **Flag only when both hold:** `z > 3.0` **and** `fill drop > 0.30`. The effect-size floor matters — with enough accumulated rows a two-point drift becomes statistically significant and would produce constant false alarms.

Then the decision rule:

| Signal | Verdict |
|---|---|
| Two or more fields flagged on the same host, same run | **structure**, high confidence |
| One field flagged with `malformed_rate > 0.5` (e.g. every price is the string "Contact sales") | **structure**, high confidence |
| One field flagged, absent only, `sparse_prone: false` | **structure**, medium confidence |
| One field flagged, absent only, `sparse_prone: true` | **ambiguous** — surface for a human, do not auto-heal |
| Sparse-prone field whose fill collapses to **zero** | **structure** — total collapse is not "Contact sales on one tier" |
| Values moved, fill rate and conformance intact | **content** — emit an insight |

Cross-field correlation is the strongest signal available and the cheapest: content changes are sparse and independent, while a redesign breaks several fields on the same host in the same run.

**Insight suppression.** While a host is in the structural state, insights for it are stored with `suppressed = true` and a reason. Otherwise the feed would announce "vendor removed all pricing" during a scraper outage — which is both wrong and precisely the failure this project exists to prevent.

Implementation: [`backend/app/detect/`](backend/app/detect/). Longer write-up in [`docs/detection.md`](docs/detection.md).

---

## Self-healing, and what actually gates an approval

`detect → compose ≤1000-char prompt → heal → validate preview → approve → verification run`

The composed prompt carries four things: what broke, quantified evidence, what the field is supposed to contain (taken verbatim from the contract description), and a last-known-good value. On a retry it also carries the previous validation failure, which is the most useful input the composer has — it tells the healer what not to do again. `prompt_length` is logged on every attempt so silent truncation at the 1,000-character boundary can never hide.

### The five-level preview gate, and its honest limits

`preview_result` comes back with **one sample row**, and that row **omits `input`**. Both facts change what validation can actually promise, so we state the gating rather than implying five equal checks:

| Level | Check | Gating | Why |
|---|---|---|---|
| 1 | Schema — `vendor` present, keys usable | **must** | Anchors depend on it |
| 2 | Conformance — parser + plausible range | **must** | Catches "Contact sales" landing in a numeric field |
| 3 | Fill rate vs baseline | **advisory** | Meaningless on `n = 1`; reported, never gates |
| 4 | Anchors, keyed on `vendor` + `tier_name` | **opportunistic** | Preview omits `input`, so anchors can never key on URL. Fires only when the sampled row happens to match an anchor |
| 5 | No collateral damage to healthy fields | **soft** | Detects gross damage only on one row |

Because levels 3 and 4 cannot be relied on, **the verification run against the live target is the hard gate.** Approval means Bright Data accepted the diff; it does not prove the data is right. Approve is not a rollback — if verification still shows the field broken, the incident goes to `escalated` with the full evidence chain rather than closing as healed.

Level 5 is the one most likely to be skipped by other implementations and the one most likely to matter: a fix that repairs `price` and destroys `tier_name` must not be approved, and nothing else in the pipeline would catch it.

Implementation: [`backend/app/heal/`](backend/app/heal/). Longer write-up in [`docs/self-healing.md`](docs/self-healing.md).

### Where the heal is driven from

The heal itself runs through the Bright Data **CLI**, which is the path the official hackathon prompts use. `backend/app/brightdata/client.py` owns the Collection API (trigger + dataset polling); the AI Flow endpoints (`refactor_template`, progress polling, `resume_automation_job`) are **not** wired in-process. Driftwatch validates the returned preview and drives the state machine through `POST /api/v1/incidents/{id}/validate-preview`. This is a real limitation and it is listed below rather than hidden.

---

## Evaluation

Most hackathon projects have no tests. The classifier here is measured against a labelled set of eight run-pairs in [`backend/tests/eval/`](backend/tests/eval/):

| # | Case | Ground truth |
|---|---|---|
| 1 | One row's price changes, rest stable | content |
| 2 | All prices go absent at once | structure |
| 3 | All prices become the string "Contact sales" | structure |
| 4 | One tier removed | content |
| 5 | A new tier added | content |
| 6 | Two fields go absent together | structure |
| 7 | ~20% of rows have no price, as normal | healthy |
| 8 | A vendor genuinely moves every tier to custom pricing | content |

**Case 8 is misclassified as `structure`, and we publish that.** When every tier legitimately becomes "contact us", the fill rate collapses to zero and the detector cannot distinguish that from the markup breaking — the observable signal is identical. Fixing it would require the very cross-run semantic understanding the design deliberately avoids in favour of explainable statistics. A false positive here costs credits and rewrites a working scraper, which is why the validator exists as a second gate.

---

## Running locally

**Python 3.13.** (3.14 has no `pydantic-core` wheel yet and will fail to install.)

```powershell
python -m venv .venv            # keep this outside OneDrive
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # set the token; .env is gitignored
$env:PYTHONPATH="$PWD\backend"
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Open <http://127.0.0.1:8000> for the incident timeline.

```powershell
pytest -q
```

`FIXTURE_MODE=true` (the default) replays JSON captured **before** the contest from `backend/tests/fixtures/` so the loop can be exercised without spending credits. Those fixtures are captured API responses used as reference material, not contest code. Set `FIXTURE_MODE=false` with a collector ID for live runs.

Note that fixture mode replays the *same* healthy run every time, so fill rates never move and no incident is ever opened — which is the correct verdict, not a bug. The incident view therefore opens on the **recorded shopalto regression**, assembled by `backend/app/recorded.py` from the captured envelopes in `samples/`. It is labelled `RECORDED` in the UI, it is not seeded into the database, and the field-loss lines in its timeline are computed from the files rather than written by hand.

### Deployment

`render.yaml` defines a free-tier Render web service running with `FIXTURE_MODE=true`, so the public instance needs no API token and spends no credits. The free tier sleeps when idle and SQLite is ephemeral there, so live run history resets on redeploy; the recorded incident is read from files and always available.

### API

```
GET  /api/v1/health
GET  /api/v1/contracts                        contracts as loaded
GET  /api/v1/runs                             run history
POST /api/v1/runs/trigger                     manual run (used in the demo)
GET  /api/v1/insights?host=&suppressed=       change feed, suppression visible
GET  /api/v1/health/fields?host=              fill-rate series per field
GET  /api/v1/incidents                        incident list
GET  /api/v1/incidents/{id}                   full audit trail
GET  /api/v1/recorded-incident                the real shopalto regression, from samples/
POST /api/v1/incidents/{id}/validate-preview  validate a preview, advance the machine
POST /api/v1/incidents/{id}/approve           human override on an escalation
POST /api/v1/incidents/{id}/abandon           close without healing
```

---

## Example structured output

[`samples/example_output.json`](samples/example_output.json) — **generated, never hand-written.** Run `python samples/build_example_output.py` and it is rebuilt from the captured collector responses in `samples/`, so the published example cannot drift from what the collector actually returned.

---

## Repository layout

```
backend/app/
  brightdata/client.py    Collection API + fixture replay. All HTTP lives here.
  ingest/normalizer.py    three-way field classification: present | absent | malformed
  contracts/              YAML loader + parsers (currency, iso_date, url, enum, ...)
  detect/statistics.py    EWMA baseline, two-proportion z-test
  detect/classifier.py    the decision rule
  heal/composer.py        1,000-character prompt construction
  heal/validator.py       the five levels
  pipeline.py             ingest → detect → incident state machine
  main.py                 FastAPI
frontend/index.html       incident timeline
contracts/                field contracts + verified URL lists
samples/                  real Bright Data envelopes
docs/                     detection, self-healing, Scraper Studio, official prompts
```

Two rules held throughout: business logic never calls the network directly, and `detect/` plus `heal/validator.py` are pure functions over data with no I/O — which is why they are testable without a network.

---

## Limitations

Stated as decisions, because that is what they are.

- **AI Flow endpoints are not wired in-process.** Heals are driven through the CLI. Driftwatch validates and gates them; it does not yet request them over HTTP.
- **The live target is a product page, not a SaaS pricing page.** Linear's `create` failed twice at `code_generator` and we chose to spend the remaining time on the detection and validation engine rather than on retrying a target we do not control. The field contracts in `contracts/pricing_pages.yaml` describe the pricing-tier schema the engine was designed against; `contracts/day1_urls.json` holds the ten verified pricing URLs it is meant for.
- **No live target broke on its own during the contest week.** The breakage we caught was caused by our own approved heals regressing `price` and `rating` — real and unstaged, but not the same as a vendor shipping a redesign.
- **The demonstrated incident ends in `escalated`, not `closed_healed`.** Two heal attempts both regressed in production. That is the honest outcome of the loop working: verification caught what the previews missed, and the system refused to declare success. A green `closed_healed` on this collector would have required either luck or lying.
- **Baseline window reduced** from the designed 20 runs to a shorter window, because the build started on 20 August.
- Preview gating is levels 1, 2 and 5; see the table above for why.
- Single user, no auth, one collector, no ML, no notifications, no mobile layout.
- **Not cut:** the validator and the evaluation set. They are the reason this is not a dashboard that calls `--auto-approve` once.

---

## Data ethics

Public data only. `robots.txt` was checked for every candidate domain on 16 August 2026 and recorded before any target was selected. `shopalto.xyz` is Bright Data's public demo store, provided by the organisers for this hackathon. Fly.io was excluded from the target list. Default cadence `RUN_INTERVAL_MINUTES=60`; every detector threshold is configuration, not a literal buried in code.

---

## AI assistance disclosure

This project was built with AI assistance throughout, as the hackathon requires disclosing.

- **Cursor (Grok 4.6)** wrote the majority of the backend during the contest week.
- **Cursor (Claude Opus)** did the pre-contest architecture and field-contract work, a code review on 20 and 22 August that found the hardcoded baseline sample size and a fabricated example-output file, and this README.
- **Bright Data CLI and MCP server** were used for collector creation, runs, and the heal.
- Architecture, contracts, target verification and anchor values were designed before the contest and kept in a separate private notes repository; the application code in this repository was written after kickoff.
- Humans own: collector-create spend, the promo code, the approve decision on the live heal, recording, and submission.

---

## License

MIT
