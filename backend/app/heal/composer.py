from __future__ import annotations

from typing import Any

from app.contracts.loader import ContractRegistry, FieldContract
from app.detect.classifier import FieldSignal


MAX_PROMPT = 1000


def compose_prompt(
    host: str,
    signals: list[FieldSignal],
    contracts: dict[str, FieldContract],
    *,
    last_good: dict[str, Any] | None = None,
    previous_failure: str | None = None,
) -> str:
    sample = ""
    if last_good:
        sample = f" Last known good value: {last_good.get('value')} (from {last_good.get('url', host)})."
    fail = ""
    if previous_failure:
        fail = f"The previous fix failed validation: {previous_failure} "
    desc = "the expected value for this field"
    flagged = [s for s in signals if s.flagged] or list(signals)
    if not flagged:
        prompt = f"{fail}Heal preview validation on host {host}. Re-capture from the current markup.{sample}"
        return prompt[:MAX_PROMPT]
    names = ", ".join(s.field for s in flagged)
    worst = flagged[0]
    contract = contracts.get(worst.field)
    desc = (contract.description if contract else desc).strip()

    evidence = (
        f"{fail}The {names} field(s) return absent/malformed on host {host}. "
        f"{worst.field} fill_rate={worst.fill_rate:.2f} baseline={worst.baseline or 0:.2f} "
        f"z={worst.z:.1f} malformed_rate={worst.malformed_rate:.2f}."
    )
    should = f" It should contain: {desc}.{sample} Re-capture from the current markup."
    prompt = evidence + should
    if len(prompt) > MAX_PROMPT:
        keep = MAX_PROMPT - len(evidence) - len(sample) - 40
        desc = desc[: max(keep, 40)] + "…"
        should = f" It should contain: {desc}.{sample} Re-capture from the current markup."
        prompt = evidence + should
    return prompt[:MAX_PROMPT]
