from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .grid import latlon_to_grid

DATA_PATH = Path(__file__).with_name("area_codes.json")


@lru_cache(maxsize=1)
def load_area_codes() -> list[dict[str, Any]]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def nearest_area_code(latitude: float, longitude: float) -> dict[str, Any] | None:
    target_x, target_y = latlon_to_grid(latitude, longitude)

    best: dict[str, Any] | None = None
    best_grid_dist: float | None = None
    best_geo_dist: float | None = None

    for item in load_area_codes():
        nx = item.get("nx")
        ny = item.get("ny")
        lat = item.get("lat")
        lon = item.get("lon")
        if nx is None or ny is None or lat is None or lon is None:
            continue

        grid_dist = _distance_sq(float(target_x), float(target_y), float(nx), float(ny))
        geo_dist = _distance_sq(latitude, longitude, float(lat), float(lon))

        if best is None:
            best = item
            best_grid_dist = grid_dist
            best_geo_dist = geo_dist
            continue

        if grid_dist < best_grid_dist:
            best = item
            best_grid_dist = grid_dist
            best_geo_dist = geo_dist
            continue

        if grid_dist == best_grid_dist and geo_dist < best_geo_dist:
            best = item
            best_grid_dist = grid_dist
            best_geo_dist = geo_dist

    return best


def _distance_sq(x1: float, y1: float, x2: float, y2: float) -> float:
    return (x1 - x2) ** 2 + (y1 - y2) ** 2
