from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.contracts.loader import ContractRegistry, FieldContract
from app.detect.statistics import ewma, two_proportion_z


@dataclass
class FieldSignal:
    host: str
    field: str
    fill_rate: float
    malformed_rate: float
    n_rows: int
    baseline: float | None
    z: float
    effect: float
    flagged: bool
    malformed_structural: bool
    sparse_prone: bool


@dataclass
class Classification:
    verdict: str  # healthy | content | structure | ambiguous
    host: str
    reason: str
    confidence: str
    signals: list[FieldSignal] = field(default_factory=list)
    insights: list[dict[str, Any]] = field(default_factory=list)


def _fill_and_malformed(rows: list[dict[str, Any]], field_name: str) -> tuple[float, float, int]:
    n = len(rows)
    if n == 0:
        return 0.0, 0.0, 0
    present = 0
    malformed = 0
    for row in rows:
        st = row["fields"][field_name]["status"]
        if st == "present":
            present += 1
        elif st == "malformed":
            malformed += 1
    return present / n, malformed / n, n


def classify_host(
    host: str,
    current_rows: list[dict[str, Any]],
    previous_rows: list[dict[str, Any]] | None,
    registry: ContractRegistry,
    baseline_fill: dict[str, tuple[float, int]],
    *,
    z_threshold: float,
    min_effect: float,
    ewma_alpha: float,
    has_baseline: bool,
) -> Classification:
    signals: list[FieldSignal] = []
    flagged: list[FieldSignal] = []
    contracts = registry.by_name()

    for name, contract in contracts.items():
        fill, mal, n = _fill_and_malformed(current_rows, name)
        base = baseline_fill.get(f"{host}:{name}")
        z = 0.0
        effect = 0.0
        flag = False
        mal_struct = mal > 0.5
        if has_baseline and base is not None and n > 0:
            p_base, n_base = base
            z = two_proportion_z(p_base, n_base, fill, n)
            effect = p_base - fill
            collapse = fill == 0 and effect > min_effect
            flag = (z > z_threshold and effect > min_effect) or mal_struct or collapse
        elif mal_struct:
            flag = True
        sig = FieldSignal(
            host=host,
            field=name,
            fill_rate=fill,
            malformed_rate=mal,
            n_rows=n,
            baseline=None if base is None else base[0],
            z=z,
            effect=effect,
            flagged=flag,
            malformed_structural=mal_struct,
            sparse_prone=contract.sparse_prone,
        )
        signals.append(sig)
        if flag:
            flagged.append(sig)

        # update caller baseline outside

    if not flagged:
        insights = _content_insights(host, current_rows, previous_rows, contracts)
        if insights:
            return Classification("content", host, "values moved with fill rate intact", "high", signals, insights)
        return Classification("healthy", host, "no fill-rate or conformance signal", "high", signals, [])

    if len(flagged) >= 2:
        return Classification(
            "structure",
            host,
            f"{len(flagged)} fields flagged on the same host",
            "high",
            signals,
            [],
        )

    only = flagged[0]
    if only.malformed_structural:
        return Classification("structure", host, f"{only.field} malformed_rate>{0.5}", "high", signals, [])
    contract = contracts[only.field]
    # Total fill collapse is not legitimate sparsity (Contact-sales on one tier).
    if contract.sparse_prone and only.fill_rate == 0 and only.effect > min_effect:
        return Classification("structure", host, f"{only.field} fill collapsed to 0 (not sparse-tier noise)", "high", signals, [])
    if not contract.sparse_prone:
        return Classification("structure", host, f"{only.field} absent on non-sparse field", "medium", signals, [])
    return Classification(
        "ambiguous",
        host,
        f"{only.field} absent-only on sparse_prone field — do not auto-heal",
        "low",
        signals,
        [],
    )


def _content_insights(
    host: str,
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]] | None,
    contracts: dict[str, FieldContract],
) -> list[dict[str, Any]]:
    if not previous:
        return []
    prev_map = {r["entity_key"]: r for r in previous}
    cur_map = {r["entity_key"]: r for r in current}
    insights: list[dict[str, Any]] = []
    for key, row in cur_map.items():
        old = prev_map.get(key)
        if not old:
            insights.append(
                {
                    "host": host,
                    "entity_key": key,
                    "field": "tier_name",
                    "before": None,
                    "after": row["fields"].get("tier_name", {}).get("value"),
                    "kind": "added",
                }
            )
            continue
        for fname, contract in contracts.items():
            if fname in {"scraped_at", "features"}:
                continue
            a = old["fields"][fname]["value"] if fname in old["fields"] else None
            b = row["fields"][fname]["value"] if fname in row["fields"] else None
            if a != b and old["fields"][fname]["status"] == "present" and row["fields"][fname]["status"] == "present":
                insights.append(
                    {
                        "host": host,
                        "entity_key": key,
                        "field": fname,
                        "before": a,
                        "after": b,
                        "kind": "changed",
                    }
                )
    for key, old in prev_map.items():
        if key not in cur_map:
            insights.append(
                {
                    "host": host,
                    "entity_key": key,
                    "field": "tier_name",
                    "before": old["fields"].get("tier_name", {}).get("value"),
                    "after": None,
                    "kind": "removed",
                }
            )
    return insights


def next_baselines(
    baseline_fill: dict[str, tuple[float, int]],
    host: str,
    rows: list[dict[str, Any]],
    registry: ContractRegistry,
    alpha: float,
) -> dict[str, tuple[float, int]]:
    out = dict(baseline_fill)
    for name in registry.schema_names():
        fill, _, n_rows = _fill_and_malformed(rows, name)
        key = f"{host}:{name}"
        prev = out.get(key)
        prev_fill = prev[0] if prev else None
        out[key] = (ewma(prev_fill, fill, alpha), n_rows)
    return out
