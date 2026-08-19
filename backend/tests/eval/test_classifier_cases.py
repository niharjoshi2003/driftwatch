from __future__ import annotations

from app.contracts.loader import load_contracts
from app.detect.classifier import classify_host, next_baselines
from app.ingest.normalizer import normalize_rows

REG = load_contracts("contracts/pricing_pages.yaml")
HOST = "linear.app"
URL = "https://linear.app/pricing"


def raw(tier: str, price, custom: bool = False, extra=None):
    row = {
        "vendor": "Linear",
        "tier_name": tier,
        "tier_price_monthly": price,
        "currency": "USD",
        "billing_period": "monthly",
        "features": ["A"],
        "is_custom_pricing": custom,
        "scraped_at": "2026-08-20T00:00:00Z",
        "input": {"url": URL},
    }
    if extra:
        row.update(extra)
    return row


def snap(rows):
    return normalize_rows(rows, REG)


def host_rows(rows):
    return [r for r in rows if r["host"] == HOST]


TIERS = [
    raw("Free", 0),
    raw("Basic", 10),
    raw("Business", 16),
    raw("Enterprise", None, True),
]


def classify_pair(prev_raw, cur_raw):
    prev = snap(prev_raw)
    cur = snap(cur_raw)
    baselines = {}
    baselines = next_baselines(baselines, HOST, host_rows(prev), REG, 1.0)
    # Warm a second time so baseline is the healthy fill
    baselines = next_baselines(baselines, HOST, host_rows(prev), REG, 1.0)
    return classify_host(
        HOST,
        host_rows(cur),
        host_rows(prev),
        REG,
        baselines,
        z_threshold=3.0,
        min_effect=0.30,
        ewma_alpha=0.3,
        has_baseline=True,
    )


def test_price_change_is_content():
    cur = [raw("Free", 0), raw("Basic", 12), raw("Business", 16), raw("Enterprise", None, True)]
    c = classify_pair(TIERS, cur)
    assert c.verdict == "content"


def test_all_prices_absent_is_structure():
    cur = [raw(t, None, True) for t in ("Free", "Basic", "Business", "Enterprise")]
    c = classify_pair(TIERS, cur)
    assert c.verdict == "structure"


def test_all_contact_sales_is_structure():
    cur = [raw(t, "Contact sales") for t in ("Free", "Basic", "Business", "Enterprise")]
    c = classify_pair(TIERS, cur)
    assert c.verdict == "structure"


def test_tier_removed_is_content():
    cur = TIERS[:-1]
    c = classify_pair(TIERS, cur)
    assert c.verdict == "content"


def test_tier_added_is_content():
    cur = TIERS + [raw("Plus", 29)]
    c = classify_pair(TIERS, cur)
    assert c.verdict == "content"


def test_two_fields_absent_is_structure():
    cur = []
    for t, p, custom in (("Free", 0, False), ("Basic", 10, False), ("Business", 16, False), ("Enterprise", None, True)):
        r = raw(t, p, custom)
        r.pop("tier_name")
        r.pop("currency")
        cur.append(r)
    c = classify_pair(TIERS, cur)
    assert c.verdict == "structure"


def test_twenty_percent_sparse_is_healthy():
    # 1 of 5 empty ≈ 20%
    cur = [
        raw("Free", 0),
        raw("Basic", 10),
        raw("Business", 16),
        raw("Pro", 20),
        raw("Enterprise", None, True),
    ]
    prev = cur
    c = classify_pair(prev, cur)
    assert c.verdict == "healthy"


def test_all_custom_probably_misclassified():
    """Ground truth is content; detector currently calls this structure. Documented failure."""
    cur = [raw(t, "Custom pricing", True) for t in ("Free", "Basic", "Business", "Enterprise")]
    c = classify_pair(TIERS, cur)
    assert c.verdict == "structure"  # known false positive vs desired `content`
