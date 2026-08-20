# Official hackathon prompts (reference)

Source: [anil-bd/scraper-studio-scrape-verse-hackathon-august-2026](https://github.com/anil-bd/scraper-studio-scrape-verse-hackathon-august-2026)

We followed that repo’s order after Linear `scraper create` failed twice at `code_generator`:

1. **Library first** — SaaS pricing pages and shopalto.xyz are long-tail; not using Amazon/LinkedIn pre-builts.
2. **Minimal create** — two fields (`name`, `price`) on the public demo store `https://shopalto.xyz/product/aurora-wireless-headphones`.
3. **Run → heal → approve → re-run** — extend schema in place on the **same Collector ID** (description, image url, rating). That is Step 2 of the official README.
4. **Batch** — same ID across the ten product URLs in `contracts/shopalto_urls.json` (official Step 4).
5. **Undeniable heal** — DEMO-IDEAS.md: host a page we control, break a class, film the heal. Design: `prep/presentation/fallback_design.md` in the notes repo. Do this before Saturday.

Driftwatch still owns judgment: detect content vs structure, validate the 1-row preview, do not `--auto-approve` blindly.
