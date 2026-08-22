from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.contracts.loader import ContractRegistry, FieldContract
from app.contracts.parsers import parse_field
from app.ingest.normalizer import classify_value


@dataclass
class LevelResult:
    level: int
    name: str
    passed: bool
    detail: str
    gating: str  # must | opportunistic | advisory | soft | hard


@dataclass
class ValidationReport:
    passed_gate: bool
    levels: list[LevelResult] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed_gate": self.passed_gate,
            "levels": [l.__dict__ for l in self.levels],
        }


def _row_vendor_tier(row: dict[str, Any]) -> tuple[str | None, str | None]:
    vendor = row.get("vendor")
    if isinstance(vendor, dict):
        vendor = vendor.get("value")
    tier = row.get("tier_name")
    if isinstance(tier, dict):
        tier = tier.get("value")
    return (str(vendor) if vendor else None, str(tier) if tier else None)


def validate_preview(
    preview_rows: list[dict[str, Any]],
    registry: ContractRegistry,
    *,
    fill_tolerance: float = 0.10,
    previous_healthy_row: dict[str, Any] | None = None,
    required_fields: Sequence[str] | None = None,
) -> ValidationReport:
    """Check a heal preview before anyone is allowed to approve it.

    required_fields is what this particular heal was asked to restore, normally
    the fields that opened the incident. A preview that comes back without them
    has not done the job, however well-formed the rest of it looks.
    """
    levels: list[LevelResult] = []
    contracts = registry.by_name()
    n = len(preview_rows)
    row0 = preview_rows[0] if preview_rows else {}

    # L1 schema — vendor, the fields that can never legitimately be absent, and
    # whatever this heal was asked to restore.
    #
    # A sparse_prone field is allowed to be missing, because some tiers really
    # have no monthly price. It stops being allowed the moment this heal was
    # requested to bring it back: then its absence is the heal failing silently.
    missing_vendor = False
    schema_ok = n >= 1
    if n == 0:
        schema_ok = False
        detail = "preview_result empty"
    else:
        must_have = [
            c.name for c in registry.fields
            if c.critical and not c.sparse_prone and c.name != "vendor"
        ]
        for name in required_fields or []:
            if name != "vendor" and name not in must_have:
                must_have.append(name)

        absent: list[str] = []
        for r in preview_rows:
            v = r.get("vendor")
            if v is None or v == "":
                missing_vendor = True
                schema_ok = False
            for name in must_have:
                if r.get(name) in (None, "") and name not in absent:
                    absent.append(name)
        if absent:
            schema_ok = False

        parts: list[str] = []
        if missing_vendor:
            parts.append("vendor missing on a preview row.")
        if absent:
            parts.append(
                "absent from the preview: " + ", ".join(absent)
                + ". a field that cannot legitimately be null, or one this heal was"
                " asked to restore, may not be missing."
            )
        if not parts:
            parts.append("schema keys usable.")
        if "input" not in row0:
            parts.append("preview omits input (expected); anchors must use vendor+tier_name.")
        detail = " ".join(parts)
    levels.append(LevelResult(1, "schema", schema_ok, detail, "must"))

    # L2 conformance
    conf_ok = True
    reasons = []
    for r in preview_rows:
        for name, contract in contracts.items():
            if name not in r or r.get(name) in (None, ""):
                continue
            parsed = parse_field(r.get(name), contract.parser, enum_values=contract.enum_values, max_length=contract.max_length)
            if parsed.status == "malformed":
                conf_ok = False
                reasons.append(f"{name}:{parsed.reason}")
            if contract.plausible_range and parsed.status == "present" and isinstance(parsed.value, (int, float)):
                lo, hi = contract.plausible_range
                if not (lo <= float(parsed.value) <= hi):
                    conf_ok = False
                    reasons.append(f"{name}:out_of_range")
    levels.append(LevelResult(2, "conformance", conf_ok, "; ".join(reasons) or "values parse", "must"))

    # L3 fill rate — advisory on n=1
    l3_pass = True
    l3_detail = f"n={n}; fill-rate not a gate on a 1-row preview"
    if n >= 5:
        # would apply fill_tolerance vs expected_null_rate
        l3_detail = f"n={n}; opportunistic fill check (tolerance={fill_tolerance})"
    levels.append(LevelResult(3, "fill_rate", l3_pass, l3_detail, "advisory"))

    # L4 anchors keyed on vendor + tier_name, never URL
    l4_pass = True
    l4_detail = "no matching anchor on this preview row; skipped (opportunistic)"
    matched = False
    for r in preview_rows:
        vendor, tier = _row_vendor_tier(r)
        if not vendor:
            continue
        for name, contract in contracts.items():
            for anchor in contract.anchors:
                if str(anchor.get("vendor", "")).lower() != vendor.lower():
                    continue
                atier = anchor.get("tier_name")
                if atier and str(atier).lower() != str(tier or "").lower():
                    continue
                expected = anchor.get("expected")
                got = r.get(name)
                parsed = classify_value(r, name, registry)
                val = parsed["value"]
                if isinstance(expected, list):
                    if val not in expected and got not in expected:
                        l4_pass = False
                        l4_detail = f"anchor miss {name} vendor={vendor} expected one of {expected} got {val}"
                    else:
                        matched = True
                        l4_detail = f"anchor hit {name} vendor={vendor} tier={tier}"
                else:
                    if val != expected and got != expected:
                        # numeric compare
                        try:
                            if float(val) != float(expected):
                                l4_pass = False
                                l4_detail = f"anchor miss {name}={val} expected={expected}"
                            else:
                                matched = True
                                l4_detail = f"anchor hit {name}={val}"
                        except (TypeError, ValueError):
                            if str(val) != str(expected) and str(got).lower() != str(expected).lower() and val is not True and expected is not True:
                                if val is True and expected is True:
                                    matched = True
                                else:
                                    l4_pass = False
                                    l4_detail = f"anchor miss {name}={val} expected={expected}"
                            else:
                                matched = True
                                l4_detail = f"anchor hit {name}"
                    else:
                        matched = True
                        l4_detail = f"anchor hit {name} vendor={vendor} tier={tier}"
    if not matched:
        l4_pass = True  # skip rather than fail
    levels.append(LevelResult(4, "anchors", l4_pass, l4_detail, "opportunistic"))

    # L5 collateral — soft
    l5_pass = True
    l5_detail = "no previous healthy row to compare"
    if previous_healthy_row and preview_rows:
        prev_v, prev_t = _row_vendor_tier(previous_healthy_row)
        cur_v, cur_t = _row_vendor_tier(preview_rows[0])
        if prev_v and cur_v and prev_v.lower() == cur_v.lower():
            notes: list[str] = []
            # A field the collector used to return and the preview no longer does
            # is the regression this project exists to catch, visible before approval.
            lost = sorted(
                name for name, value in previous_healthy_row.items()
                if name != "input"
                and value not in (None, "")
                and preview_rows[0].get(name) in (None, "")
            )
            if lost:
                l5_pass = False
                notes.append("lost against the last healthy row: " + ", ".join(lost))
            # garbage tier_name while price looks fixed
            if previous_healthy_row.get("tier_name") and preview_rows[0].get("tier_name"):
                if str(preview_rows[0]["tier_name"]) in {"", "null", "undefined"}:
                    l5_pass = False
                    notes.append("tier_name destroyed on preview row")
            l5_detail = "; ".join(notes) or "no collateral damage on sample row"
    levels.append(LevelResult(5, "collateral", l5_pass, l5_detail, "soft"))

    must = all(l.passed for l in levels if l.gating == "must")
    soft_block = any(l.level == 5 and not l.passed for l in levels)
    passed_gate = must and not soft_block
    return ValidationReport(passed_gate=passed_gate, levels=levels)
