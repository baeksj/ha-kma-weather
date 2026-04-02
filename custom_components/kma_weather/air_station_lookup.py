from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

DATA_PATH = Path(__file__).with_name("air_stations.json")


@lru_cache(maxsize=1)
def load_air_stations() -> list[dict[str, Any]]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def nearest_air_station(latitude: float, longitude: float) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_dist: float | None = None
    for item in load_air_stations():
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is None or lon is None:
            continue
        dist = _haversine_km(latitude, longitude, float(lat), float(lon))
        if best is None or dist < best_dist:
            best = {**item, "geo_distance_km": dist}
            best_dist = dist
    return best


async def async_nearest_air_station(
    hass: HomeAssistant,
    latitude: float,
    longitude: float,
) -> dict[str, Any] | None:
    return await hass.async_add_executor_job(nearest_air_station, latitude, longitude)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c
