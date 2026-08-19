from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from app.contracts.loader import ContractRegistry
from app.contracts.parsers import parse_field


def host_from_row(row: dict[str, Any]) -> str:
    inp = row.get("input")
    if isinstance(inp, dict) and inp.get("url"):
        return urlparse(str(inp["url"])).netloc.lower().lstrip("www.")
    url = row.get("url")
    if isinstance(url, str) and url.startswith("http"):
        return urlparse(url).netloc.lower().lstrip("www.")
    vendor = str(row.get("vendor") or "unknown").strip().lower()
    return vendor or "unknown"


def entity_key(host: str, tier_name: str | None) -> str:
    norm = "".join(ch.lower() for ch in (tier_name or "") if ch.isalnum())
    return f"{host}:{norm or 'unknown'}"


def classify_value(row: dict[str, Any], field_name: str, registry: ContractRegistry) -> dict[str, Any]:
    contract = registry.by_name().get(field_name)
    if field_name not in row or row.get(field_name) is None or row.get(field_name) == "":
        return {"status": "absent", "value": None, "reason": None}
    if not contract:
        return {"status": "present", "value": row.get(field_name), "reason": None}
    result = parse_field(
        row.get(field_name),
        contract.parser,
        enum_values=contract.enum_values,
        max_length=contract.max_length,
    )
    return {"status": result.status, "value": result.value, "reason": result.reason}


def normalize_rows(
    raw_rows: list[dict[str, Any]],
    registry: ContractRegistry,
    *,
    collection_id: str | None = None,
    scraped_at: str | None = None,
) -> list[dict[str, Any]]:
    now = scraped_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    out: list[dict[str, Any]] = []
    for row in raw_rows:
        host = host_from_row(row)
        parsed: dict[str, Any] = {}
        for name in registry.schema_names():
            parsed[name] = classify_value(row, name, registry)
        if parsed.get("scraped_at", {}).get("status") == "absent":
            parsed["scraped_at"] = {"status": "present", "value": now, "reason": None}
        tier = parsed.get("tier_name", {}).get("value")
        out.append(
            {
                "host": host,
                "entity_key": entity_key(host, str(tier) if tier is not None else None),
                "vendor": parsed.get("vendor", {}).get("value"),
                "raw": row,
                "fields": parsed,
                "collection_id": collection_id,
            }
        )
    return out
