"""Insert one SYNTHETIC incident so the incident UI can be exercised locally.

Read this before using the output for anything:

    The numbers in this file are invented. linear.app, the fill rates, the
    z-score and the heal prompt are illustrative, NOT captured from Bright Data.
    The real, captured evidence lives in samples/ and is served unmodified at
    /api/v1/recorded-incident. Nothing here is used by that endpoint, by the
    tests, or by the default database.

Why it exists: fixture mode replays one identical collection every run, so no
fill rate ever moves and no incident is ever opened. That is correct detection
behaviour, but it leaves the incident timeline and the five-level validation
table unreachable in a local demo. This seeds one so those screens can be seen.

    $env:DATABASE_URL = "sqlite:///./data/demo.db"
    python scripts/seed_demo_incident.py
    uvicorn app.main:app --app-dir backend --port 8000

The validation report is not hand-written: it is whatever the real validator
returns for this preview, so the table shows genuine gate behaviour.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings
from app.contracts.loader import load_contracts
from app.heal.validator import validate_preview
from app.store.models import HealAttempt, Incident, Timeline, make_engine, session_factory

# A previously healthy row, and a heal preview that quietly drops the one field
# the incident was opened for. Level 5 should refuse it.
PREVIOUS_HEALTHY = {
    "vendor": "linear.app",
    "tier_name": "Business",
    "tier_price_monthly": "$14",
    "currency": "USD",
    "billing_period": "monthly",
}
PREVIEW = [{"vendor": "linear.app", "tier_name": "Business", "currency": "USD", "billing_period": "monthly"}]

DETECTION = {
    "signal": "fill_rate_drop",
    "field": "tier_price_monthly",
    "baseline_fill_rate": 0.94,
    "current_fill_rate": 0.0,
    "baseline_rows": 34,
    "z_score": -7.82,
    "conformance": {"before": 0.97, "after": 0.0},
    "verdict": "structure",
    "reason": "critical field absent across every row while sibling fields held",
    "synthetic": True,
}

PROMPT = (
    "The collector for linear.app stopped returning tier_price_monthly.\n"
    'Expected: a currency value such as "$14" for each pricing tier.\n'
    "Currently: the field is absent on all 34 rows while vendor and tier_name\n"
    "are unchanged, so the price element specifically moved or was renamed.\n"
    "Keep every existing field. Do not change vendor or tier_name extraction."
)

TIMELINE = [
    ("detected", "tier_price_monthly fill rate 94% -> 0% on 34 rows, sibling fields unchanged"),
    ("prompt_composed", "field contract rendered into a heal prompt"),
    ("heal_requested", "sent to Bright Data AI Flow, anchored on vendor + tier_name"),
    ("awaiting_approval", "preview returned, validating before anyone can approve"),
]


def main() -> None:
    settings = get_settings()
    registry = load_contracts(settings.contracts_path)
    session = session_factory(make_engine(settings.database_url))()

    report = validate_preview(
        PREVIEW,
        registry,
        previous_healthy_row=PREVIOUS_HEALTHY,
        required_fields=["tier_price_monthly"],
    )

    incident = Incident(
        collector_id=settings.bright_data_collector_id or "c_demo_synthetic",
        host="linear.app",
        fields=json.dumps(["tier_price_monthly"]),
        state="awaiting_approval" if not report.passed_gate else "approved",
        detection_evidence=json.dumps(DETECTION, indent=2),
        attempt_count=1,
    )
    session.add(incident)
    session.flush()

    for state, note in TIMELINE:
        session.add(Timeline(incident_id=incident.id, state=state, note=note))

    session.add(
        HealAttempt(
            incident_id=incident.id,
            attempt_number=1,
            prompt=PROMPT,
            prompt_length=len(PROMPT),
            preview_result=json.dumps(PREVIEW),
            validation_report=json.dumps(report.as_dict()),
            decision="approved" if report.passed_gate else "rejected",
        )
    )
    session.commit()

    failed = [f"L{l.level} {l.name}" for l in report.levels if not l.passed]
    print(f"seeded SYNTHETIC incident #{incident.id} into {settings.database_url}")
    print(f"  gate: {'pass' if report.passed_gate else 'fail'}")
    print(f"  failing levels: {', '.join(failed) or 'none'}")
    print("  the captured, real evidence is at /api/v1/recorded-incident")


if __name__ == "__main__":
    main()
