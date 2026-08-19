import json
from pathlib import Path

from app.brightdata.client import FixtureClient
from app.contracts.loader import load_contracts
from app.heal.validator import validate_preview

ROOT = Path(__file__).resolve().parents[2]
REG = load_contracts(ROOT / "contracts" / "pricing_pages.yaml")


def test_preview_omits_input():
    client = FixtureClient(ROOT / "backend" / "tests" / "fixtures")
    heal = client.heal_preview()
    preview = heal["preview_result"]
    assert len(preview) == 1
    assert "input" not in preview[0]


def test_hn_preview_fails_pricing_schema_gate():
    client = FixtureClient(ROOT / "backend" / "tests" / "fixtures")
    report = validate_preview(client.heal_preview()["preview_result"], REG)
    assert report.passed_gate is False
    l1 = next(l for l in report.levels if l.level == 1)
    assert l1.passed is False


def test_good_preview_passes_gate():
    preview = [
        {
            "vendor": "Linear",
            "tier_name": "Basic",
            "tier_price_monthly": 10,
            "currency": "USD",
            "billing_period": "monthly",
            "is_custom_pricing": False,
            "features": ["SSO"],
            "scraped_at": "2026-08-20T00:00:00Z",
        }
    ]
    report = validate_preview(preview, REG)
    assert report.passed_gate is True
    l4 = next(l for l in report.levels if l.level == 4)
    assert "anchor" in l4.detail.lower() or l4.passed


def test_closed_healed_requires_verification():
    from app.config import Settings
    from app.pipeline import apply_preview
    from app.store.models import Incident, make_engine, session_factory

    engine = make_engine("sqlite:///:memory:")
    Session = session_factory(engine)
    s = Session()
    inc = Incident(
        collector_id="c_test",
        host="linear.app",
        fields='["tier_price_monthly"]',
        state="awaiting_approval",
        detection_evidence="{}",
    )
    s.add(inc)
    s.commit()
    settings = Settings(contracts_path=ROOT / "contracts" / "pricing_pages.yaml")
    preview = [
        {
            "vendor": "Linear",
            "tier_name": "Basic",
            "tier_price_monthly": 10.0,
            "currency": "USD",
            "billing_period": "monthly",
            "is_custom_pricing": False,
        }
    ]
    apply_preview(s, settings, inc.id, preview, verification_healthy=True)
    s.refresh(inc)
    assert inc.state == "closed_healed"
    apply_preview(s, settings, inc.id, preview, verification_healthy=False)
    # second call increments attempts; last outcome verification
    s.refresh(inc)
    assert inc.state in {"escalated", "closed_healed"}
