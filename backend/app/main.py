from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.contracts.loader import load_contracts
from app.pipeline import apply_preview, ingest_and_detect, load_urls
from app.store.models import HealAttempt, Incident, Insight, Observation, Run, Timeline, make_engine, session_factory

settings = get_settings()
engine = make_engine(settings.database_url)
SessionLocal = session_factory(engine)
ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"

app = FastAPI(title="Driftwatch", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def db() -> Session:
    return SessionLocal()


@app.get("/api/v1/health")
def health():
    return {
        "ok": True,
        "fixture_mode": settings.fixture_mode,
        "collector_id": settings.bright_data_collector_id or None,
        "utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/contracts")
def contracts():
    reg = load_contracts(settings.contracts_path)
    return {
        "collector": reg.collector,
        "version": reg.version,
        "fields": [
            {
                "name": f.name,
                "parser": f.parser,
                "critical": f.critical,
                "sparse_prone": f.sparse_prone,
                "expected_null_rate": f.expected_null_rate,
            }
            for f in reg.fields
        ],
    }


@app.get("/api/v1/runs")
def runs():
    s = db()
    try:
        rows = s.query(Run).order_by(Run.id.desc()).limit(50).all()
        return [
            {
                "id": r.id,
                "status": r.status,
                "row_count": r.row_count,
                "collection_id": r.collection_id,
                "started_at": r.started_at,
                "error": r.error,
            }
            for r in rows
        ]
    finally:
        s.close()


@app.post("/api/v1/runs/trigger")
def trigger_run():
    s = db()
    try:
        urls = load_urls(settings.day1_urls_path)
        return ingest_and_detect(s, settings, urls=urls)
    finally:
        s.close()


@app.get("/api/v1/insights")
def insights(host: str | None = None, suppressed: int | None = None):
    s = db()
    try:
        q = s.query(Insight).order_by(Insight.id.desc())
        if host:
            q = q.filter(Insight.host == host)
        if suppressed is not None:
            q = q.filter(Insight.suppressed == suppressed)
        return [
            {
                "id": i.id,
                "host": i.host,
                "field": i.field,
                "before": i.before,
                "after": i.after,
                "suppressed": bool(i.suppressed),
                "reason": i.reason,
                "created_at": i.created_at,
            }
            for i in q.limit(200).all()
        ]
    finally:
        s.close()


@app.get("/api/v1/health/fields")
def field_health(host: str | None = None):
    s = db()
    try:
        q = s.query(Observation)
        if host:
            q = q.filter(Observation.host == host)
        rows = q.order_by(Observation.id.desc()).limit(2000).all()
        series: dict[str, list] = {}
        for o in reversed(rows):
            key = f"{o.host}:{o.field}"
            series.setdefault(key, []).append({"run_id": o.run_id, "status": o.status})
        out = []
        for key, pts in series.items():
            n = len(pts)
            present = sum(1 for p in pts if p["status"] == "present")
            out.append({"key": key, "n": n, "fill_rate": present / n if n else 0, "points": pts[-40:]})
        return out
    finally:
        s.close()


@app.get("/api/v1/incidents")
def incidents():
    s = db()
    try:
        rows = s.query(Incident).order_by(Incident.id.desc()).all()
        return [
            {
                "id": i.id,
                "host": i.host,
                "state": i.state,
                "fields": i.fields,
                "attempt_count": i.attempt_count,
                "outcome": i.outcome,
                "opened_at": i.opened_at,
            }
            for i in rows
        ]
    finally:
        s.close()


@app.get("/api/v1/incidents/{incident_id}")
def incident_detail(incident_id: int):
    s = db()
    try:
        i = s.get(Incident, incident_id)
        if i is None:
            raise HTTPException(404)
        timeline = s.query(Timeline).filter(Timeline.incident_id == i.id).order_by(Timeline.id).all()
        attempts = s.query(HealAttempt).filter(HealAttempt.incident_id == i.id).order_by(HealAttempt.id).all()
        return {
            "id": i.id,
            "host": i.host,
            "state": i.state,
            "fields": i.fields,
            "detection_evidence": i.detection_evidence,
            "attempt_count": i.attempt_count,
            "outcome": i.outcome,
            "opened_at": i.opened_at,
            "closed_at": i.closed_at,
            "timeline": [{"state": t.state, "at": t.at, "note": t.note} for t in timeline],
            "attempts": [
                {
                    "attempt_number": a.attempt_number,
                    "prompt": a.prompt,
                    "prompt_length": a.prompt_length,
                    "preview_result": a.preview_result,
                    "validation_report": a.validation_report,
                    "decision": a.decision,
                }
                for a in attempts
            ],
        }
    finally:
        s.close()


class PreviewBody(BaseModel):
    preview_result: list[dict]
    verification_healthy: bool = True


@app.post("/api/v1/incidents/{incident_id}/validate-preview")
def validate(incident_id: int, body: PreviewBody):
    s = db()
    try:
        inc = apply_preview(s, settings, incident_id, body.preview_result, verification_healthy=body.verification_healthy)
        return {"id": inc.id, "state": inc.state, "outcome": inc.outcome}
    except KeyError:
        raise HTTPException(404)
    finally:
        s.close()


@app.post("/api/v1/incidents/{incident_id}/approve")
def human_approve(incident_id: int):
    s = db()
    try:
        i = s.get(Incident, incident_id)
        if i is None:
            raise HTTPException(404)
        i.state = "closed_healed"
        i.outcome = "healed_human"
        from app.store.models import utcnow

        i.closed_at = utcnow()
        s.add(Timeline(incident_id=i.id, state="closed_healed", note="human override"))
        s.commit()
        return {"id": i.id, "state": i.state}
    finally:
        s.close()


@app.post("/api/v1/incidents/{incident_id}/abandon")
def abandon(incident_id: int):
    s = db()
    try:
        i = s.get(Incident, incident_id)
        if i is None:
            raise HTTPException(404)
        i.state = "escalated"
        i.outcome = "abandoned"
        from app.store.models import utcnow

        i.closed_at = utcnow()
        s.add(Timeline(incident_id=i.id, state="escalated", note="abandoned"))
        s.commit()
        return {"id": i.id, "state": i.state}
    finally:
        s.close()


if FRONTEND.exists():

    @app.get("/")
    def index():
        return FileResponse(FRONTEND / "index.html")
