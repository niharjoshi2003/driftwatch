# Build status — 22 August 2026

Deadline Sunday 23 August. Form: <https://bit.ly/4xmOMsr>

## Done

**Prep, 9–16 August** (separate private notes repo, no application code)
Bright Data CLI, login, zones, MCP server, agent skills. Architecture and field
contracts. Ten verified public pricing URLs with robots.txt checked. Hacker News
spike producing six real API envelopes, used as offline fixtures. Preview-gating
decision and the eight-case classifier evaluation spec.

**Contest week**
- Collector `c_mt0hvfomh2bmennhd` (`shopalto_products`) created, run, healed in
  place to add `description`, `image_url`, `rating`, preview validated, approved,
  re-run. Envelopes in `samples/`.
- FastAPI backend: ingest with three-way field classification, YAML contracts and
  parsers, EWMA baseline and two-proportion z-test, classifier, 1,000-character
  prompt composer, five-level preview validator, incident state machine, SQLite.
- Incident timeline UI at `/`.
- Tests: parsers, composer, validator, eight labelled classifier cases.
- `FIXTURE_MODE` replay so the loop runs without spending credits.
- README with detection methodology, Scraper Studio usage, honest gating table,
  published known misclassification, and AI disclosure.
- Example output generated from captured responses rather than hand-written.

## Remaining before submission

- [ ] Push `samples/heal_shopalto.json`, `samples/approve_shopalto.json`,
      `samples/run_shopalto_after_heal.json` — the heal evidence is still local
- [ ] Re-run `python samples/build_example_output.py` so `stage` becomes `post_heal`
- [ ] Record the demo video — `docs/demo-script.md` has the shot list
- [ ] Add the video link to the README
- [ ] Submit, Sunday morning

## Known limitations, stated in the README

AI Flow endpoints not wired in-process; heals run through the CLI. The live
target is a product page because Linear's `create` failed twice at
`code_generator`. The demonstrated heal adds fields rather than repairing a
break. Baseline window shortened because the build started on 20 August.
Classifier case 8 is a known miss and the number is published.
