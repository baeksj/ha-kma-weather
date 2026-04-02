from __future__ import annotations

from urllib.parse import urlencode

from aiohttp import ClientError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import AIRKOREA_API_BASE, AIRKOREA_API_VERSION


class AirKoreaApiError(Exception):
    """Raised when the AirKorea API request fails."""


class AirKoreaApi:
    def __init__(self, hass, api_key: str, station_name: str) -> None:
        self.hass = hass
        self.api_key = api_key
        self.station_name = station_name
        self._session = async_get_clientsession(hass)

    async def async_fetch_realtime_air_quality(self) -> dict:
        params = {
            "serviceKey": self.api_key,
            "returnType": "json",
            "numOfRows": "1",
            "pageNo": "1",
            "stationName": self.station_name,
            "dataTerm": "DAILY",
            "ver": AIRKOREA_API_VERSION,
        }
        url = f"{AIRKOREA_API_BASE}/getMsrstnAcctoRltmMesureDnsty?{urlencode(params)}"
        try:
            async with self._session.get(url, timeout=30) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise AirKoreaApiError(f"Request failed for AirKorea realtime air quality: {err}") from err

        response = payload.get("response", {})
        header = response.get("header", {})
        if header.get("resultCode") != "00":
            raise AirKoreaApiError(
                "AirKorea API error: "
                f"{header.get('resultCode')} {header.get('resultMsg')}"
            )

        items = response.get("body", {}).get("items", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            raise AirKoreaApiError("No AirKorea realtime air quality items returned")
        if not isinstance(items, list):
            raise AirKoreaApiError("Unexpected AirKorea payload shape")
        return items[0]
