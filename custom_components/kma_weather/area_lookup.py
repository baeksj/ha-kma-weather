from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).with_name("area_codes.json")


@lru_cache(maxsize=1)
def load_area_codes() -> list[dict[str, Any]]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def nearest_area_code(latitude: float, longitude: float) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_dist: float | None = None

    for item in load_area_codes():
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is None or lon is None:
            continue
        dist = _distance_sq(latitude, longitude, float(lat), float(lon))
        if best_dist is None or dist < best_dist:
            best = item
            best_dist = dist
    return best


def _distance_sq(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return (lat1 - lat2) ** 2 + (lon1 - lon2) ** 2
