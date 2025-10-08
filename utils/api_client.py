"""API client abstractions for the historian app."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional

import math
import random

try:  # pragma: no cover - Streamlit is optional during tests
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    st = None  # type: ignore

import requests

DEFAULT_MAX_POINTS = 20_000


class BaseApiClient:
    """Abstract base client interface."""

    def fetch_tags(self) -> List[str]:
        raise NotImplementedError

    def fetch_series(
        self,
        tags: Iterable[str],
        start: datetime,
        end: datetime,
        agg: str,
        max_points: int = DEFAULT_MAX_POINTS,
    ) -> List[dict]:
        raise NotImplementedError


class HttpApiClient(BaseApiClient):
    """Client that talks to the historian HTTP API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def fetch_tags(self) -> List[str]:
        response = requests.get(f"{self.base_url}/tags", timeout=30)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "tags" in data:
            tags = data["tags"]
        else:
            tags = data
        return [str(tag) for tag in tags]

    def fetch_series(
        self,
        tags: Iterable[str],
        start: datetime,
        end: datetime,
        agg: str,
        max_points: int = DEFAULT_MAX_POINTS,
    ) -> List[dict]:
        params = {
            "tags": list(tags),
            "start": start.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
            "end": end.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"),
            "agg": agg,
            "max_points": max_points,
        }
        response = requests.get(f"{self.base_url}/series", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("series", data)


class DemoApiClient(BaseApiClient):
    """Fallback client that generates synthetic data for demos."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or Path(__file__).resolve().parent.parent / "data"
        self._tags_cache: List[str] | None = None

    def fetch_tags(self) -> List[str]:
        if self._tags_cache is None:
            fixture = self.data_path / "demo_tags.json"
            if fixture.exists():
                self._tags_cache = sorted(
                    [line.strip() for line in fixture.read_text().splitlines() if line.strip()]
                )
            else:
                self._tags_cache = self._generate_default_tags()
        return list(self._tags_cache)

    def fetch_series(
        self,
        tags: Iterable[str],
        start: datetime,
        end: datetime,
        agg: str,
        max_points: int = DEFAULT_MAX_POINTS,
    ) -> List[dict]:
        results: List[dict] = []
        tags_list = list(tags)
        if not tags_list:
            return results

        start = start.astimezone(UTC)
        end = end.astimezone(UTC)
        total_seconds = max((end - start).total_seconds(), 1)
        # Determine step to keep points under the limit per tag.
        raw_points = min(int(total_seconds // 60) + 1, max_points)
        step_seconds = max(total_seconds / max(raw_points, 1), 1)

        for tag in tags_list:
            points: List[List[Optional[float]]] = []
            timestamp = start
            seed = sum(ord(ch) for ch in tag)
            random.seed(seed)
            phase = random.random() * math.pi
            amplitude = random.uniform(10, 100)
            noise = random.uniform(0.1, 1.5)
            while timestamp <= end and len(points) < max_points:
                value = amplitude * math.sin(phase + timestamp.timestamp() / 3600) + random.gauss(0, noise)
                quality = 0
                points.append([
                    timestamp.isoformat().replace("+00:00", "Z"),
                    round(value, 3),
                    quality,
                ])
                timestamp += timedelta(seconds=step_seconds)
            results.append({"name": tag, "points": points})
        return results

    def _generate_default_tags(self) -> List[str]:
        enterprises = ["EnterpriseA"]
        sites = ["Site1", "Site2"]
        areas = ["AreaA", "AreaB"]
        lines = ["Line1", "Line2"]
        cells = ["Cell1", "Cell2"]
        equipments = ["Pump01", "Pump02"]
        tags = [
            f"{enterprise}/{site}/{area}/{line}/{cell}/{equipment}/Tag{i}"
            for enterprise in enterprises
            for site in sites
            for area in areas
            for line in lines
            for cell in cells
            for equipment in equipments
            for i in range(1, 4)
        ]
        return tags


def get_api_client() -> BaseApiClient:
    """Return the appropriate API client based on configuration."""

    base_url: Optional[str] = None
    if st is not None:
        try:
            base_url = st.secrets.get("API_BASE")  # type: ignore[assignment]
        except Exception:  # pragma: no cover
            base_url = None
    if base_url:
        return HttpApiClient(str(base_url))
    return DemoApiClient()
