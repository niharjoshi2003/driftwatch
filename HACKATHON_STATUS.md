# Contest build status — 20 Aug 2026 (Thu, day 4 of 7)

Deadline: Sunday 23 Aug. Form: https://bit.ly/4xmOMsr

## Already done before this repo (prep, 9–16 Aug)

- Bright Data CLI 0.3.3, login, zones, MCP, HN spike fixtures
- Architecture, playbook, 10-URL list, robots checks, field contracts
- Preview gating (1-row, vendor+tier anchors), eval spec of 8 cases
- Private notes repo: https://github.com/niharjoshi2003/driftwatch-prep
- OBS portable on D: (mic test still on you)
- C: disk space recovered (~24 GB) by moving Downloads to E: and apps to D:

## Done tonight (product at D:\dev\driftwatch)

- Empty git repo + venv at D:\dev\venvs\driftwatch
- FastAPI ingest / normalizer / EWMA+z classifier / prompt composer / 5-level validator / SQLite
- Incident timeline UI at /
- Pytest: parsers, 8 classifier cases, validator, composer
- README with Scraper Studio + AI disclosure + example JSON
- FIXTURE_MODE default so you can demo the loop without spending credits

## You must still do

1. `brightdata scraper create` with `contracts/create_prompt.txt` (5–25 min, credits)
2. Pin `c_…` in `.cursor/rules/collector.mdc` and `.env`
3. First live run of the 10 URLs; per-host fill rate; Browser worker if 0%
4. One real heal → verification → `closed_healed` before Saturday
5. Promo `wemakedevs`, Discord, OBS 30s playback, submit form + video
