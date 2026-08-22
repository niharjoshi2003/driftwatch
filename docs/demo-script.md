# Demo video — shot list and narration

Target **5 minutes**. Everything below is recordable from assets that already
exist: a terminal, the Bright Data control panel, the approval email, the four
envelopes in `samples/`, the Driftwatch UI, and the editor.

**The spine of this video is a real failure that happened to us.** A heal
returned a perfect-looking preview, we approved it, and it destroyed a working
field. Lead with that. It is more convincing than any staged break.

**Before you hit record**

- Notifications off. One display. Browser zoom 125% so text survives 1080p.
- Terminal font size up. Dark theme.
- Tabs open in this order: the approval email, the control panel for
  `c_mt0hvfomh2bmennhd`, `samples/heal_shopalto.json`,
  `samples/run_shopalto_after_heal.json`, `samples/heal2_shopalto.json`,
  the Driftwatch UI.
- App already running. Do not start uvicorn on camera.
- Record audio and video in one pass. Do not dub afterwards.

---

## 0:00–0:35 — The problem

**Screen:** `samples/run_shopalto.json`, then the fill-rate view in the UI.

> A scraper runs every hour. It works for weeks. Then the site ships a redesign,
> a class name moves, and a field quietly comes back empty. The job still exits
> zero. The dashboard still renders. The data is just wrong now, and nobody finds
> out until someone downstream asks why the numbers look strange.
>
> Scraping doesn't fail loudly. It decays.

---

## 0:35–1:15 — The insight

**Screen:** a single slide, or the README's opening two lines.

> Every time you scrape a page twice, something differs. And every difference
> forces one question: did the content change, or did the page change?
>
> A price moving from twenty-nine dollars to thirty-nine is content. That's news
> — it belongs in a change feed.
>
> A price moving from twenty-nine to empty because a class name moved is
> structure. That's breakage — it belongs in an incident queue.
>
> Those are the same computation. So Driftwatch runs one engine and emits both.
> Everything else follows from that.

---

## 1:15–1:50 — A real collector

**Screen:** terminal, `samples/create_shopalto.json`, `samples/run_shopalto.json`,
then the control panel.

> This is a real Scraper Studio collector, created from the CLI inside Cursor.
> Two fields to start: product name and price. One run, one row — a hundred and
> seventy-two dollars forty.
>
> Then I healed the same collector in place to add three more fields:
> description, image URL, and a customer rating.

---

## 1:50–2:20 — The email

**Screen:** the Bright Data email, zoomed on the sentence.

> Bright Data finished the refactor and sent me this:
>
> *"Review and test before deploying to production."*
>
> Read that again. Something has to do the reviewing. In practice nobody does —
> you click approve, or you pass `--auto-approve` and you never look.
>
> Bright Data gives you a repair mechanism. It does not give you judgment.

---

## 2:20–3:20 — What actually happened. Slow down here.

**Screen:** `samples/heal_shopalto.json`, scrolled to `preview_result`. Then
`samples/run_shopalto_after_heal.json` side by side if you can.

> Here's the preview it returned. All five fields. Product name. Price, a hundred
> and forty-five ninety-nine. Description. Image URL. Rating, four point seven.
>
> It looks perfect. So I approved it.

Pause. Switch to the after-heal run.

> And this is what the live run gave me afterwards.
>
> Product name. Description. Image URL.
>
> **Price is gone. Rating is gone.**
>
> The heal added the two fields I asked for and silently destroyed a field that
> had been working since the collector was created. The preview didn't show it.
> The approval succeeded. The API reported status: done.
>
> This wasn't staged. It happened to me, yesterday, on the demo store the
> organisers provided. And it is the whole reason this project exists.

---

## 3:20–4:20 — What Driftwatch does about it

**Screen:** `backend/app/heal/validator.py`, then the five-level table, then the
incident detail timeline in the UI.

> A preview is a proposal, not a fix. One sampled row cannot tell you what a
> template does across a live run. So Driftwatch is explicit about which checks
> can actually gate an approval and which are only reported.
>
> Levels one and two must pass: the schema is usable, and every value parses
> against its declared contract and falls inside a plausible range. Level three
> is advisory — you cannot compute a fill rate from one row and I'm not going to
> pretend otherwise. Level four fires only when the sampled row happens to match
> a hand-verified anchor, because the preview doesn't even tell you which URL it
> came from.
>
> And level five is collateral damage. A fix that repairs one field and destroys
> another must not be approved — which is precisely what just happened to me, and
> precisely what nothing else in the pipeline would catch.
>
> But since the preview can lie, the real gate is the verification run afterwards.
> Approval only means Bright Data accepted the diff. It does not mean the data is
> right. Verification still broken means the incident escalates, not closes.

---

## 4:20–4:45 — The retry, driven by evidence

**Screen:** `samples/heal2_shopalto.json`, the prompt field.

> So the incident didn't close. It went back through the composer with the
> specific failure attached — because the most useful thing you can tell a healer
> is what it did wrong last time:
>
> *"The last approved heal added description and image_url but dropped price and
> rating on the live run. Restore price as a numeric amount with currency, and
> rating as the numeric star score."*
>
> Second preview brings all five fields back. Same loop, second attempt, driven
> by evidence instead of hope. Every prompt, every preview, every validation
> report and every decision is on the incident timeline.

---

## 4:45–5:00 — Honesty, then close

**Screen:** README limitations, then the eval table.

> Two things I'll say plainly. The AI Flow endpoints aren't wired in-process yet
> — heals run through the CLI and Driftwatch validates and gates them. And the
> classifier has a known miss: when a vendor genuinely moves every tier to custom
> pricing, the fill rate collapses to zero and my detector calls it breakage. The
> signal is identical to a real break. I publish that rather than hide it.
>
> Driftwatch. One engine, two outputs — what changed, and what broke.

---

## If you have time for one more thing

Approve heal 2 and run the collector once more. If all five fields come back, you
close the loop on camera with a genuine `closed_healed` and the video ends on a
recovery instead of a retry. That is worth twenty minutes.
