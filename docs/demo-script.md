# Demo video — shot list and narration

Target **5 minutes**. Everything below is recordable with what already exists: a
terminal, the Bright Data control panel, the approval email, the Driftwatch UI at
`http://127.0.0.1:8000`, and the editor.

**Before you hit record**

- Notifications off. One display. Browser zoom 125% so text survives 1080p.
- Terminal font size up. Dark theme.
- Have these open in tabs, in this order: the approval email, the control panel
  for `c_mt0hvfomh2bmennhd`, `samples/heal_shopalto.json`, the Driftwatch UI.
- Have the app already running. Do not start uvicorn on camera.
- Record audio and video in one pass. Do not try to dub narration afterwards.

---

## 0:00–0:30 — The problem

**Screen:** `samples/run_shopalto.json` open, then the fill-rate view in the UI.

> A scraper runs every hour. It works for weeks. Then the site ships a redesign,
> a class name moves, and the field quietly comes back empty. The job still exits
> zero. The dashboard still renders. The data is just wrong now, and nobody finds
> out until someone downstream asks why the numbers look strange.
>
> That is the failure mode this project is about.

---

## 0:30–1:15 — The insight

**Screen:** the README section "Why this exists", or a single slide with the two
lines side by side.

> Every time you scrape a page twice, something differs. And every difference
> forces one question: did the content change, or did the page change?
>
> A price moving from twenty-nine dollars to thirty-nine is content. That is news
> — it belongs in a change feed.
>
> A price moving from twenty-nine to empty because a class name moved is
> structure. That is breakage — it belongs in an incident queue.
>
> Those are the same computation. So Driftwatch runs one engine and emits both.
> That is the whole design, and everything else follows from it.

---

## 1:15–2:00 — Scraper Studio doing the work

**Screen:** terminal, then the control panel.

Show `samples/create_shopalto.json` and `samples/run_shopalto.json`.

> This is a real Scraper Studio collector, created from the CLI inside Cursor.
> Two fields to start: product name and price. One run, one row — Wireless
> Headphones Aurora, a hundred and seventy-two dollars forty.
>
> Then I healed the same collector in place to add three more fields:
> description, image URL, and rating. Rating is deliberately specified as empty
> when a product has no reviews — because a field that is *legitimately* empty is
> exactly what a naive null check gets wrong.

---

## 2:00–2:45 — The email. This is the pitch.

**Screen:** the Bright Data approval email, zoomed on the sentence.

> And here is what came back. Bright Data finished the refactor and emailed me
> this:
>
> *"Review and test before deploying to production."*
>
> Read that again, because that sentence is the entire problem. Something has to
> do the reviewing. In practice nobody does — you click approve, or you pass
> `--auto-approve` and you never look at it.
>
> Bright Data gives you a repair mechanism. It does not give you judgment.
> Driftwatch is the judgment.

---

## 2:45–4:00 — The validation, which is the actual contribution

**Screen:** `samples/heal_shopalto.json` showing `preview_result`, then
`backend/app/heal/validator.py`, then the incident detail screen in the UI.

> This is the preview Bright Data returned. Notice two things. It is **one row**.
> And it has no `input` field, so I cannot tell which URL it came from.
>
> That matters, because it means a fill-rate check across the preview is
> meaningless, and an anchor check keyed on URL is impossible. So Driftwatch
> keys anchors on vendor and tier name instead, and it is explicit about which
> levels actually gate an approval and which are only reported.

Walk the five-level table on screen.

> Levels one and two must pass: the schema is usable, and every value parses
> against its declared contract and falls inside a plausible range. Level three
> is advisory — you cannot compute a fill rate from one row and I am not going to
> pretend otherwise. Level four fires only when the sampled row happens to match
> a hand-verified anchor. Level five is a soft reject for collateral damage — a
> fix that repairs the price and destroys the product name must not go through,
> and nothing else in the pipeline would catch that.
>
> And because the preview can't carry the whole decision, the real gate is the
> verification run afterwards. Approval only means Bright Data accepted the diff.
> It does not mean the data is right. If verification still shows the field
> broken, the incident escalates instead of closing as healed.

---

## 4:00–4:30 — The audit trail

**Screen:** incident detail timeline, expanding each state.

> Every transition is persisted. The detection evidence with the fill rates and
> the z-score. The composed prompt with its character count, because the API caps
> it at a thousand and silent truncation would be a miserable bug to find during
> a demo. The returned preview. The validation report, level by level. The
> decision, and why.
>
> Nobody clicked anything in the middle of this. That is the point.

---

## 4:30–5:00 — Honesty, then close

**Screen:** README limitations section, then the eval table.

> Two things I will say plainly. The AI Flow endpoints are not wired in-process
> yet — heals are driven through the CLI and Driftwatch validates and gates them.
> And the classifier has a known miss: when a vendor genuinely moves every tier
> to custom pricing, the fill rate collapses to zero and my detector calls it
> breakage. The observable signal is identical to a real break. I publish that
> number rather than hide it, because a detector you cannot characterise is a
> detector you cannot trust.
>
> Driftwatch. One engine, two outputs — what changed, and what broke.

---

## If a heal is running during recording

Start it before the last section, then say:

> That heal takes ten to fifteen minutes, so I am not going to make you watch it.
> The completed one I just walked through is the same path, with real timestamps.

Honest, and it proves the flow is live rather than staged.
