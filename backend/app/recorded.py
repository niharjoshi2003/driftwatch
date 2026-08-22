"""The recorded shopalto incident, read from the captured envelopes in samples/.

This is not synthetic and it is not seeded into the database. It is the sequence
of real Bright Data responses from 21-22 August 2026, assembled into the shape
the incident view already renders, so the audit trail can be inspected on a fresh
deployment where no run history exists yet.

Fixture mode replays one healthy Hacker News run, which by design never opens an
incident: identical data run after run means fill rates never move. Without this
endpoint a fresh deployment has nothing to show.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

COLLECTOR_ID = "c_mt0hvfomh2bmennhd"
TARGET = "https://shopalto.xyz/product/aurora-wireless-headphones"


def _load(samples: Path, name: str) -> Any:
    path = samples / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("preview_result", "data", "rows"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _fields(rows: list[dict]) -> list[str]:
    return sorted({key for row in rows for key in row if key != "input"})


def _compare(baseline: list[str], preview: list[str], live: list[str]) -> dict[str, list[str]]:
    """Split a failed heal into the two failures it actually contains.

    A field the baseline collector already returned and the live run no longer
    does has regressed: the heal broke something that worked. A field only the
    preview ever showed was never delivered at all. Both are missing against the
    preview, but only the first is a regression, and conflating them overstates
    one claim while hiding the other.
    """
    return {
        "regressed": [f for f in baseline if f not in live],
        "never_delivered": [f for f in preview if f not in baseline and f not in live],
        "delivered": [f for f in preview if f not in baseline and f in live],
    }


def _verdict(diff: dict[str, list[str]], live: list[str], repeat: bool) -> str:
    if not diff["regressed"] and not diff["never_delivered"]:
        return "live run matches the preview"
    parts = [f"live run returns {len(live)} fields"]
    if diff["regressed"]:
        again = " again" if repeat else ""
        parts.append(
            f"{', '.join(diff['regressed'])} regressed{again} — returned before the heal, gone after"
        )
    if diff["never_delivered"]:
        parts.append(f"{', '.join(diff['never_delivered'])} never arrived despite the preview")
    if diff["delivered"]:
        parts.append(f"{', '.join(diff['delivered'])} did land")
    return ". ".join(parts)


def build(samples_dir: Path) -> dict[str, Any]:
    run0 = _rows(_load(samples_dir, "run_shopalto.json"))
    heal1 = _load(samples_dir, "heal_shopalto.json") or {}
    approve1 = _load(samples_dir, "approve_shopalto.json") or {}
    run1 = _rows(_load(samples_dir, "run_shopalto_after_heal.json"))
    heal2 = _load(samples_dir, "heal2_shopalto.json") or {}
    approve2 = _load(samples_dir, "approve2_shopalto.json") or {}
    run2 = _rows(_load(samples_dir, "run_shopalto_verified.json"))

    baseline = _fields(run0)
    preview1, live1 = _fields(_rows(heal1)), _fields(run1)
    preview2, live2 = _fields(_rows(heal2)), _fields(run2)

    diff1 = _compare(baseline, preview1, live1)
    diff2 = _compare(baseline, preview2, live2)

    timeline = [
        {
            "state": "baseline",
            "note": f"collector returns {', '.join(baseline)}",
            "evidence": {"fields": baseline},
        },
        {
            "state": "heal_requested",
            "note": f"attempt 1 prompt, {len(heal1.get('prompt', ''))} chars of a 1000 budget",
            "evidence": {"prompt": heal1.get("prompt")},
        },
        {
            "state": "awaiting_approval",
            "note": f"preview shows {len(preview1)} fields: {', '.join(preview1)}",
            "evidence": {"preview_result": _rows(heal1)},
        },
        {
            "state": "approved",
            "note": "completed_steps: " + ", ".join(approve1.get("completed_steps", [])),
            "evidence": {"status": approve1.get("status")},
        },
        {
            "state": "verifying",
            "note": _verdict(diff1, live1, repeat=False),
            "evidence": {"rows": run1, "field_comparison": diff1},
        },
        {
            "state": "heal_requested",
            "note": f"attempt 2 recomposed with the regression named, {len(heal2.get('prompt', ''))} chars",
            "evidence": {"prompt": heal2.get("prompt")},
        },
        {
            "state": "awaiting_approval",
            "note": f"preview restores {len(preview2)} fields: {', '.join(preview2)}",
            "evidence": {"preview_result": _rows(heal2)},
        },
        {
            "state": "approved",
            "note": "completed_steps: " + ", ".join(approve2.get("completed_steps", [])),
            "evidence": {"status": approve2.get("status")},
        },
        {
            "state": "verifying",
            "note": _verdict(diff2, live2, repeat=True),
            "evidence": {"rows": run2, "field_comparison": diff2},
        },
        {
            "state": "escalated",
            "note": "two attempts, two clean previews, two production regressions",
            "evidence": None,
        },
    ]

    return {
        "recorded": True,
        "source": "captured Bright Data responses in samples/, 21-22 August 2026",
        "collector_id": COLLECTOR_ID,
        "target": TARGET,
        "host": "shopalto.xyz",
        "state": "escalated",
        "outcome": "verification_failed",
        "attempt_count": 2,
        "headline": (
            f"Both previews showed all {len(preview1)} requested fields. Both live runs "
            f"afterwards dropped {', '.join(diff1['regressed'])}, which the collector "
            f"returned before the heal, and never delivered "
            f"{', '.join(diff1['never_delivered'])} at all. The previews were clean "
            "every time. Only the verification run caught either failure."
        ),
        "approval_step_difference": {
            "attempt_1": approve1.get("completed_steps", []),
            "attempt_2": approve2.get("completed_steps", []),
            "note": (
                "Attempt 1 reached save_new_template and changed live behaviour. "
                "Attempt 2 stopped at user_approval and did not. Both returned "
                "status: done. Reported as an observation, not a proven cause."
            ),
        },
        "timeline": timeline,
    }
