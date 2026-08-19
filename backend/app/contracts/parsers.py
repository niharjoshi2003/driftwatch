from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_CURRENCY = re.compile(
    r"(?i)^\s*(?:usd|eur|gbp|inr|cad|aud|\$|€|£)?\s*(\d+(?:[.,]\d+)?)\s*"
    r"(?:usd|eur|gbp|/mo|/month|per month)?\s*$"
)
_FREE = re.compile(r"(?i)^\s*(free|0(\.0+)?)\s*$")
_CUSTOM = re.compile(r"(?i)contact\s+sales|custom|talk to sales|quote")


class ParseResult:
    __slots__ = ("status", "value", "reason")

    def __init__(self, status: str, value: Any = None, reason: str | None = None):
        self.status = status  # present | absent | malformed
        self.value = value
        self.reason = reason


def _absent() -> ParseResult:
    return ParseResult("absent")


def parse_currency(raw: Any) -> ParseResult:
    if raw is None or raw == "":
        return _absent()
    if isinstance(raw, (int, float)):
        return ParseResult("present", float(raw))
    text = str(raw).strip()
    if not text:
        return _absent()
    if _CUSTOM.search(text):
        return ParseResult("malformed", text, "custom_or_contact_sales_in_numeric_field")
    if _FREE.match(text):
        return ParseResult("present", 0.0)
    m = _CURRENCY.search(text.replace(",", ""))
    if not m:
        return ParseResult("malformed", text, "not_a_currency")
    try:
        return ParseResult("present", float(m.group(1)))
    except ValueError:
        return ParseResult("malformed", text, "not_a_currency")


def parse_non_empty_string(raw: Any, max_length: int | None = None) -> ParseResult:
    if raw is None or raw == "":
        return _absent()
    text = str(raw).strip()
    if not text:
        return _absent()
    if max_length and len(text) > max_length:
        return ParseResult("malformed", text, "too_long")
    return ParseResult("present", text)


def parse_enum(raw: Any, values: list[str]) -> ParseResult:
    if raw is None or raw == "":
        return _absent()
    text = str(raw).strip()
    for v in values:
        if text.lower() == v.lower():
            return ParseResult("present", v)
    return ParseResult("malformed", text, "not_in_enum")


def parse_boolean(raw: Any) -> ParseResult:
    if raw is None or raw == "":
        return _absent()
    if isinstance(raw, bool):
        return ParseResult("present", raw)
    text = str(raw).strip().lower()
    if text in {"true", "1", "yes"}:
        return ParseResult("present", True)
    if text in {"false", "0", "no"}:
        return ParseResult("present", False)
    return ParseResult("malformed", raw, "not_boolean")


def parse_iso_date(raw: Any) -> ParseResult:
    if raw is None or raw == "":
        return _absent()
    text = str(raw).strip()
    if not text:
        return _absent()
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return ParseResult("present", text)
    except ValueError:
        return ParseResult("malformed", text, "not_iso_date")


def parse_string_array(raw: Any) -> ParseResult:
    if raw is None or raw == "":
        return _absent()
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        return ParseResult("present", parts) if parts else _absent()
    if isinstance(raw, list):
        parts = [str(p).strip() for p in raw if str(p).strip()]
        return ParseResult("present", parts)
    return ParseResult("malformed", raw, "not_array")


def parse_field(raw: Any, parser: str, *, enum_values: list[str] | None = None, max_length: int | None = None) -> ParseResult:
    if parser == "currency":
        return parse_currency(raw)
    if parser == "non_empty_string":
        return parse_non_empty_string(raw, max_length)
    if parser == "enum":
        return parse_enum(raw, enum_values or [])
    if parser == "boolean":
        return parse_boolean(raw)
    if parser == "iso_date":
        return parse_iso_date(raw)
    if parser == "string_array":
        return parse_string_array(raw)
    return parse_non_empty_string(raw, max_length)
