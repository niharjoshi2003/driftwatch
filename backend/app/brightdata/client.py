from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings

API = "https://api.brightdata.com"


class BrightDataClient:
    """All network I/O to Bright Data lives here. Business logic never calls HTTP."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._http = httpx.Client(timeout=60.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.bright_data_api_token}",
            "Content-Type": "application/json",
        }

    def trigger(self, collector_id: str, urls: list[dict[str, str]]) -> str:
        q = urlencode({"collector": collector_id, "queue_next": 1})
        r = self._http.post(f"{API}/dca/trigger?{q}", headers=self._headers(), json=urls)
        r.raise_for_status()
        data = r.json()
        return data.get("collection_id") or data.get("snapshot_id")

    def poll_dataset(self, collection_id: str, *, timeout_s: int = 900) -> list[dict[str, Any]]:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            r = self._http.get(f"{API}/dca/dataset?id={collection_id}", headers=self._headers())
            if r.status_code == 202:
                time.sleep(5)
                continue
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return data
            status = str(data.get("status") or data.get("collection_status") or "").lower()
            if status in {"building", "running", "pending", "collecting"}:
                time.sleep(5)
                continue
            if "data" in data and isinstance(data["data"], list):
                return data["data"]
            if isinstance(data, dict) and data.get("error"):
                raise RuntimeError(data["error"])
            time.sleep(5)
        raise TimeoutError(f"dataset {collection_id} not ready in {timeout_s}s")

    def heal(self, collector_id: str, prompt: str, url: str) -> dict[str, Any]:
        raise NotImplementedError("heal goes through the Bright Data CLI, not this HTTP client")

    def close(self) -> None:
        self._http.close()


class FixtureClient:
    """Replay captured JSON. No network."""

    def __init__(self, fixtures_dir: Path):
        self.dir = Path(fixtures_dir)

    def _load(self, name: str) -> Any:
        return json.loads((self.dir / name).read_text(encoding="utf-8"))

    def trigger(self, collector_id: str, urls: list[dict[str, str]]) -> str:
        raw = self._load("raw_trigger.json")
        if isinstance(raw, dict) and raw.get("collection_id"):
            return raw["collection_id"]
        return "j_fixture"

    def poll_dataset(self, collection_id: str, *, timeout_s: int = 900) -> list[dict[str, Any]]:
        rows = self._load("run1.json")
        if isinstance(rows, list):
            return rows
        return []

    def heal_preview(self, name: str = "heal.json") -> dict[str, Any]:
        return self._load(name)

    def close(self) -> None:
        return None
