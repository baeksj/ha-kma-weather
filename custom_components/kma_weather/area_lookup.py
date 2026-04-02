from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from .grid import latlon_to_grid

DATA_PATH = Path(__file__).with_name("area_codes.json")


@lru_cache(maxsize=1)
def load_area_codes() -> list[dict[str, Any]]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def nearest_area_code(latitude: float, longitude: float) -> dict[str, Any] | None:
    matches = nearest_area_codes(latitude, longitude, limit=1)
    return matches[0] if matches else None


def nearest_area_codes(latitude: float, longitude: float, limit: int = 3) -> list[dict[str, Any]]:
    target_x, target_y = latlon_to_grid(latitude, longitude)
    candidates: list[tuple[float, float, dict[str, Any]]] = []

    for item in load_area_codes():
        nx = item.get("nx")
        ny = item.get("ny")
        lat = item.get("lat")
        lon = item.get("lon")
        if nx is None or ny is None or lat is None or lon is None:
            continue

        grid_dist = _distance_sq(float(target_x), float(target_y), float(nx), float(ny))
        geo_dist = _haversine_km(latitude, longitude, float(lat), float(lon))
        enriched = {
            **item,
            "grid_distance": grid_dist,
            "geo_distance_km": geo_dist,
        }
        candidates.append((grid_dist, geo_dist, enriched))

    candidates.sort(key=lambda row: (row[0], row[1]))
    return [item for _, _, item in candidates[:limit]]


def _distance_sq(x1: float, y1: float, x2: float, y2: float) -> float:
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c
