from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Collector(Base):
    __tablename__ = "collectors"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collector_id: Mapped[str] = mapped_column(String)
    collection_id: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="running")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Observation(Base):
    __tablename__ = "field_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"))
    host: Mapped[str] = mapped_column(String)
    entity_key: Mapped[str] = mapped_column(String)
    field: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    value_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Insight(Base):
    __tablename__ = "insights"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer)
    host: Mapped[str] = mapped_column(String)
    field: Mapped[str] = mapped_column(String)
    before: Mapped[str | None] = mapped_column(Text, nullable=True)
    after: Mapped[str | None] = mapped_column(Text, nullable=True)
    suppressed: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collector_id: Mapped[str] = mapped_column(String)
    host: Mapped[str] = mapped_column(String)
    fields: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String)
    detection_evidence: Mapped[str] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)


class HealAttempt(Base):
    __tablename__ = "heal_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, ForeignKey("incidents.id"))
    attempt_number: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    prompt_length: Mapped[int] = mapped_column(Integer)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    preview_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str | None] = mapped_column(String, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Timeline(Base):
    __tablename__ = "incident_timeline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, ForeignKey("incidents.id"))
    state: Mapped[str] = mapped_column(String)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Baseline(Base):
    __tablename__ = "baselines"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    fill_rate: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


def make_engine(url: str):
    if url.startswith("sqlite:///./"):
        root = Path(__file__).resolve().parents[3]
        rel = url.replace("sqlite:///./", "")
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path.as_posix()}"
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return engine


def session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)


def dump(obj: Any) -> str:
    return json.dumps(obj, default=str)
