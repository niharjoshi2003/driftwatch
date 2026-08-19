from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FieldContract:
    name: str
    description: str
    type: str
    parser: str
    expected_null_rate: float = 0.0
    sparse_prone: bool = False
    critical: bool = False
    max_length: int | None = None
    plausible_range: list[float] | None = None
    enum_values: list[str] = field(default_factory=list)
    anchors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ContractRegistry:
    collector: str
    version: str
    fields: list[FieldContract]

    def by_name(self) -> dict[str, FieldContract]:
        return {f.name: f for f in self.fields}

    def schema_names(self) -> list[str]:
        return [f.name for f in self.fields]


def load_contracts(path: str | Path) -> ContractRegistry:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    fields = []
    for raw in data.get("fields", []):
        desc = raw.get("description") or ""
        if isinstance(desc, str):
            desc = " ".join(desc.split())
        fields.append(
            FieldContract(
                name=raw["name"],
                description=desc,
                type=raw.get("type", "string"),
                parser=raw.get("parser", "non_empty_string"),
                expected_null_rate=float(raw.get("expected_null_rate") or 0),
                sparse_prone=bool(raw.get("sparse_prone")),
                critical=bool(raw.get("critical")),
                max_length=raw.get("max_length"),
                plausible_range=raw.get("plausible_range"),
                enum_values=list(raw.get("enum_values") or []),
                anchors=list(raw.get("anchors") or []),
            )
        )
    return ContractRegistry(
        collector=data.get("collector", "pricing_pages"),
        version=str(data.get("version", "0")),
        fields=fields,
    )
