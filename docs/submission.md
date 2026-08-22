# Submission — ready-to-paste answers

Form: <https://bit.ly/4xmOMsr> · Deadline Sunday 23 August 2026 · **Submit in the morning, not at the deadline.**

Fill the video URL in below once it is uploaded, then copy each block straight
into the form.

---

## Project name

```
Driftwatch
```

## One-line pitch

```
Every scrape answers one question: did the content change, or did the page break the scraper? One engine, two outputs — a change feed and a self-healing loop.
```

## Repository

```
https://github.com/niharjoshi2003/driftwatch
```

## Demo video

```
<paste the unlisted YouTube link here>
```

## Description

```
Scrapers fail silently. The site ships a redesign, a class name moves, the field
comes back empty, and the job still exits zero. Nobody finds out until someone
downstream asks why the numbers look strange.

Driftwatch watches a Bright Data Scraper Studio collector and, on every run,
answers one question: did the content change, or did the page change? A price
moving $29 to $39 is content — news, and it goes in a change feed. A price moving
$29 to empty because a class name moved is structure — breakage, and it opens an
incident and repairs the scraper. Those are the same computation, so a single
engine emits both.

Detection is deliberately classical statistics rather than a model, because it
has to be explainable: fill rate per field per host, an EWMA baseline, a
two-proportion z-test, and a flag only when the result is both statistically
significant (z > 3) and materially large (a 30-point drop). Cross-field
correlation separates a redesign from a one-off edit — content changes are sparse
and independent, a redesign breaks several fields at once.

The part that matters is what happens next. Bright Data gives you a repair
mechanism; it does not give you judgment. When Scraper Studio finishes a
refactor it emails you "review and test before deploying to production" — and in
practice nobody reviews, they click approve. Driftwatch is the reviewer. It
composes a heal prompt inside the 1,000-character cap from the field's declared
contract plus quantified evidence, validates the returned preview against those
contracts and hand-verified anchors, and only then approves. Approval is not a
rollback, so the hard gate is a verification run against the live target
afterwards; if the field is still broken the incident escalates with the full
evidence chain rather than closing as healed.

The classifier is measured against a labelled set of eight run-pairs, and the
README publishes the case it gets wrong and why.
```

## How Bright Data Scraper Studio is used

```
Load-bearing — remove Scraper Studio and there is no product. We followed the
official prompt order: library check, minimal create, run, heal in place,
approve, batch.

CREATE. scraper create against Linear's pricing page failed twice at
code_generator (c_mt0h7usvdesnctj3q, c_mt0hn92ue1oi96zqi). Following the official
README we created a minimal two-field collector against the public demo store:
c_mt0hvfomh2bmennhd (shopalto_products), status done. The collector ID is pinned
in .cursor/rules/collector.mdc so the coding agent reuses it rather than creating
new collectors. Envelope: samples/create_shopalto.json.

RUN. brightdata scraper run returned Wireless Headphones Aurora at $172.40 USD.
Envelope: samples/run_shopalto.json.

HEAL IN PLACE. The same collector was healed to add description, image_url and
rating, with rating specified as empty when a product has no reviews — legitimate
sparsity is exactly the case a naive null check gets wrong. Bright Data returned
awaiting_approval with a one-row preview_result and emailed a review link. We did
not use --auto-approve: Driftwatch validated the preview first, then approved,
then re-ran to confirm the fields populate.

COLLECTION API. Scheduled runs use POST /dca/trigger and GET /dca/dataset, in
backend/app/brightdata/client.py. All Bright Data network I/O lives in that one
module; business logic never calls HTTP directly.

CODING AGENT. The collector was created and operated from the Bright Data CLI
inside Cursor, with the Bright Data MCP server and agent skills installed.

Honest limitation, also in the README: the AI Flow endpoints (refactor_template,
progress polling, resume_automation_job) are not wired in-process. Heals are
driven through the CLI; Driftwatch validates and gates them.
```

## AI assistance disclosure

```
This project was built with AI assistance throughout.

- Cursor (Grok 4.6) wrote the majority of the backend during the contest week.
- Cursor (Claude Opus) did the pre-contest architecture and field-contract
  design, code reviews on 20 and 22 August that caught a hardcoded baseline
  sample size in the z-test and a fabricated example-output file, and the README.
- The Bright Data CLI and MCP server were used for collector creation, runs and
  the heal.
- Architecture, field contracts, target verification and anchor values were
  prepared before the contest in a separate private notes repository, which the
  rules permit. All application code in the submitted repository was written
  after kickoff on 17 August.
- Humans owned the collector-create spend, the approve decision on the live
  heal, the recording and the submission.
```

## Example structured output

```
samples/example_output.json — generated by samples/build_example_output.py from
captured Bright Data responses, never hand-written, so the published example
cannot drift from what the collector actually returned.
```

---

## Pre-submit checklist

- [ ] Everything local pushed — `git status` clean
- [ ] `pytest -q` green on Python 3.13
- [ ] `python samples/build_example_output.py` re-run after the post-heal file is committed, so `stage` reads `post_heal`
- [ ] `git grep c_mt0h7usvdesnctj3q` returns only the README and this file, where it is named as a *failed* collector
- [ ] Repo is public
- [ ] Video uploaded, unlisted is fine, link works in a private window
- [ ] README video link filled in
- [ ] Form submitted
