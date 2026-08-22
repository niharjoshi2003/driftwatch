from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.contracts.loader import load_contracts
from app.detect.classifier import Classification, classify_host, next_baselines
from app.heal.composer import compose_prompt
from app.heal.validator import validate_preview
from app.ingest.normalizer import normalize_rows
from app.store.models import (
    Baseline,
    Collector,
    HealAttempt,
    Incident,
    Insight,
    Observation,
    Run,
    Timeline,
    dump,
    utcnow,
)
from app.brightdata.client import BrightDataClient, FixtureClient


def load_urls(path: Path) -> list[dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _signal_dict(c: Classification) -> dict[str, Any]:
    return {
        "verdict": c.verdict,
        "reason": c.reason,
        "confidence": c.confidence,
        "signals": [
            {
                "field": s.field,
                "fill_rate": s.fill_rate,
                "malformed_rate": s.malformed_rate,
                "z": s.z,
                "effect": s.effect,
                "flagged": s.flagged,
            }
            for s in c.signals
        ],
    }


def ingest_and_detect(session: Session, settings: Settings, *, urls: list[dict[str, str]] | None = None) -> dict[str, Any]:
    registry = load_contracts(settings.contracts_path)
    collector_id = settings.bright_data_collector_id or "c_fixture"
    if session.get(Collector, collector_id) is None:
        session.add(Collector(id=collector_id, name="pricing_pages"))
        session.commit()

    run = Run(collector_id=collector_id, status="running")
    session.add(run)
    session.commit()

    try:
        if settings.fixture_mode:
            client = FixtureClient(settings.fixtures_dir)
            collection_id = client.trigger(collector_id, urls or [])
            raw_rows = client.poll_dataset(collection_id)
        else:
            if not settings.bright_data_api_token or not settings.bright_data_collector_id:
                raise RuntimeError("Set BRIGHT_DATA_API_TOKEN and BRIGHT_DATA_COLLECTOR_ID (or FIXTURE_MODE=true)")
            client = BrightDataClient(settings)
            payload = urls or load_urls(settings.day1_urls_path)
            collection_id = client.trigger(collector_id, payload)
            raw_rows = client.poll_dataset(collection_id)
            client.close()
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = utcnow()
        session.commit()
        raise

    run.collection_id = collection_id
    normalized = normalize_rows(raw_rows, registry, collection_id=collection_id)
    run.row_count = len(normalized)
    run.status = "ok"
    run.finished_at = utcnow()
    session.commit()

    by_host: dict[str, list] = defaultdict(list)
    for row in normalized:
        by_host[row["host"]].append(row)
        for fname, parsed in row["fields"].items():
            session.add(
                Observation(
                    run_id=run.id,
                    host=row["host"],
                    entity_key=row["entity_key"],
                    field=fname,
                    status=parsed["status"],
                    value_json=dump(parsed["value"]),
                )
            )
    session.commit()

    baselines = {b.key: (b.fill_rate, int(b.n_rows or 0)) for b in session.query(Baseline).all()}
    prior_runs = session.query(Run).filter(Run.status == "ok", Run.id != run.id).count()
    has_baseline = prior_runs >= 1

    previous_by_host: dict[str, list] = defaultdict(list)
    prev_run = (
        session.query(Run)
        .filter(Run.status == "ok", Run.id != run.id)
        .order_by(Run.id.desc())
        .first()
    )
    if prev_run:
        prev_obs = session.query(Observation).filter(Observation.run_id == prev_run.id).all()
        grouped: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(dict))
        for o in prev_obs:
            grouped[o.entity_key][o.field] = {"status": o.status, "value": json.loads(o.value_json) if o.value_json else None}
            grouped[o.entity_key]["_host"] = o.host
        for ek, fields in grouped.items():
            host = fields.pop("_host")
            previous_by_host[host].append({"entity_key": ek, "host": host, "fields": fields})

    results = []
    for host, rows in by_host.items():
        c = classify_host(
            host,
            rows,
            previous_by_host.get(host),
            registry,
            baselines,
            z_threshold=settings.detect_z_threshold,
            min_effect=settings.detect_min_effect,
            ewma_alpha=settings.baseline_ewma_alpha,
            has_baseline=has_baseline,
        )
        results.append(_signal_dict(c))
        baselines = next_baselines(baselines, host, rows, registry, settings.baseline_ewma_alpha)
        structural_hosts = {host} if c.verdict == "structure" else set()
        for ins in c.insights:
            suppressed = 1 if ins["host"] in structural_hosts or c.verdict == "structure" else 0
            session.add(
                Insight(
                    run_id=run.id,
                    host=ins["host"],
                    field=ins["field"],
                    before=dump(ins.get("before")),
                    after=dump(ins.get("after")),
                    suppressed=suppressed,
                    reason="host in structural state" if suppressed else None,
                )
            )
        if c.verdict == "structure":
            _open_incident(session, settings, collector_id, host, c, registry)
        elif c.verdict == "ambiguous":
            _open_incident(session, settings, collector_id, host, c, registry, auto_heal=False)

    for key, (fill, n_rows) in baselines.items():
        row = session.get(Baseline, key)
        if row is None:
            session.add(Baseline(key=key, fill_rate=fill, n_rows=n_rows, updated_at=utcnow()))
        else:
            row.fill_rate = fill
            row.n_rows = n_rows
            row.updated_at = utcnow()
    session.commit()
    return {"run_id": run.id, "collection_id": collection_id, "row_count": run.row_count, "hosts": results}


def _open_incident(session: Session, settings: Settings, collector_id: str, host: str, c: Classification, registry, auto_heal: bool = True) -> Incident:
    fields = [s.field for s in c.signals if s.flagged]
    inc = Incident(
        collector_id=collector_id,
        host=host,
        fields=dump(fields),
        state="detected",
        detection_evidence=dump(_signal_dict(c)),
        attempt_count=0,
    )
    session.add(inc)
    session.commit()
    session.add(Timeline(incident_id=inc.id, state="detected", note=c.reason))
    session.commit()
    if not auto_heal:
        inc.state = "escalated"
        inc.outcome = "ambiguous_sparse"
        session.add(Timeline(incident_id=inc.id, state="escalated", note="sparse_prone absent-only — human review"))
        session.commit()
        return inc

    prompt = compose_prompt(host, c.signals, registry.by_name())
    inc.state = "prompt_composed"
    session.add(Timeline(incident_id=inc.id, state="prompt_composed", note=f"prompt_length={len(prompt)}"))
    session.commit()

    attempt_n = inc.attempt_count + 1
    inc.attempt_count = attempt_n
    inc.state = "heal_requested"
    session.add(Timeline(incident_id=inc.id, state="heal_requested"))
    session.commit()

    if settings.fixture_mode:
        from app.brightdata.client import FixtureClient

        envelope = FixtureClient(settings.fixtures_dir).heal_preview()
        preview = envelope.get("preview_result") or []
        # HN preview is the wrong schema — the validator should reject it, which
        # is the demo of "never approve on faith". Tests inject a good preview.
        report = validate_preview(preview if isinstance(preview, list) else [], registry)
        decision = "approved" if report.passed_gate else "rejected"
        ha = HealAttempt(
            incident_id=inc.id,
            attempt_number=attempt_n,
            prompt=prompt,
            prompt_length=len(prompt),
            preview_result=dump(preview),
            validation_report=dump(report.as_dict()),
            decision=decision,
            decided_at=utcnow(),
        )
        session.add(ha)
        inc.state = "awaiting_approval"
        session.add(Timeline(incident_id=inc.id, state="awaiting_approval", note="fixture heal envelope"))
        session.add(Timeline(incident_id=inc.id, state="validating"))
        if report.passed_gate:
            inc.state = "approved"
            session.add(Timeline(incident_id=inc.id, state="approved", note="preview gate passed"))
            inc.state = "verifying"
            session.add(Timeline(incident_id=inc.id, state="verifying", note="verification run is the hard gate"))
            inc.state = "closed_healed"
            inc.outcome = "healed"
            inc.closed_at = utcnow()
            session.add(Timeline(incident_id=inc.id, state="closed_healed"))
        else:
            inc.state = "rejected"
            session.add(Timeline(incident_id=inc.id, state="rejected", note="preview gate failed"))
            if attempt_n >= settings.heal_max_attempts:
                inc.state = "escalated"
                inc.outcome = "escalated"
                inc.closed_at = utcnow()
                session.add(Timeline(incident_id=inc.id, state="escalated", note="attempts exhausted"))
            else:
                inc.state = "prompt_composed"
                session.add(Timeline(incident_id=inc.id, state="prompt_composed", note="retry with failure feedback"))
        session.commit()
        return inc

    inc.state = "escalated"
    inc.outcome = "live_heal_not_wired_this_run"
    session.add(Timeline(incident_id=inc.id, state="escalated", note="live AI Flow: use CLI heal then POST /incidents/{id}/validate-preview"))
    session.commit()
    return inc


def _incident_fields(inc: Incident) -> list[str]:
    """The fields an incident was opened for, stored as JSON or as a bare list."""
    raw = inc.fields or ""
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return [p.strip() for p in raw.split(",") if p.strip()]
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return []


def apply_preview(session: Session, settings: Settings, incident_id: int, preview_rows: list[dict[str, Any]], *, verification_healthy: bool) -> Incident:
    registry = load_contracts(settings.contracts_path)
    inc = session.get(Incident, incident_id)
    if inc is None:
        raise KeyError(incident_id)
    # The preview is judged against the fields that opened this incident, so a
    # heal that returns without them is rejected instead of silently approved.
    report = validate_preview(preview_rows, registry, required_fields=_incident_fields(inc))
    inc.attempt_count += 1
    prompt = compose_prompt(inc.host, [], registry.by_name())
    session.add(
        HealAttempt(
            incident_id=inc.id,
            attempt_number=inc.attempt_count,
            prompt=prompt,
            prompt_length=len(prompt),
            preview_result=dump(preview_rows),
            validation_report=dump(report.as_dict()),
            decision="approved" if report.passed_gate else "rejected",
            decided_at=utcnow(),
        )
    )
    session.add(Timeline(incident_id=inc.id, state="validating"))
    if not report.passed_gate:
        inc.state = "rejected"
        session.add(Timeline(incident_id=inc.id, state="rejected"))
        if inc.attempt_count >= settings.heal_max_attempts:
            inc.state = "escalated"
            inc.outcome = "escalated"
            inc.closed_at = utcnow()
            session.add(Timeline(incident_id=inc.id, state="escalated"))
        session.commit()
        return inc
    inc.state = "approved"
    session.add(Timeline(incident_id=inc.id, state="approved"))
    inc.state = "verifying"
    session.add(Timeline(incident_id=inc.id, state="verifying", note="approve is not rollback"))
    if verification_healthy:
        inc.state = "closed_healed"
        inc.outcome = "healed"
        inc.closed_at = utcnow()
        session.add(Timeline(incident_id=inc.id, state="closed_healed"))
    else:
        inc.state = "escalated"
        inc.outcome = "verification_failed"
        inc.closed_at = utcnow()
        session.add(Timeline(incident_id=inc.id, state="escalated", note="verification still broken"))
    session.commit()
    return inc
