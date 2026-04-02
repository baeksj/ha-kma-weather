from __future__ import annotations

import math

# KMA DFS grid conversion constants
RE = 6371.00877  # Earth radius (km)
GRID = 5.0  # Grid spacing (km)
SLAT1 = 30.0
SLAT2 = 60.0
OLON = 126.0
OLAT = 38.0
XO = 43.0
YO = 136.0


def latlon_to_grid(latitude: float, longitude: float) -> tuple[int, int]:
    """Convert WGS84 latitude/longitude to KMA DFS nx/ny grid coordinates."""
    degrad = math.pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * degrad
    slat2 = SLAT2 * degrad
    olon = OLON * degrad
    olat = OLAT * degrad

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf**sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro**sn)

    ra = math.tan(math.pi * 0.25 + latitude * degrad * 0.5)
    ra = re * sf / (ra**sn)
    theta = longitude * degrad - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    x = math.floor(ra * math.sin(theta) + XO + 0.5)
    y = math.floor(ro - ra * math.cos(theta) + YO + 0.5)
    return int(x), int(y)
