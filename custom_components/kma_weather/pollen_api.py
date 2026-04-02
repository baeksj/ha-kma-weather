from __future__ import annotations

from urllib.parse import urlencode

from aiohttp import ClientError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import KMA_POLLEN_API_BASE


class KmaPollenApiError(Exception):
    """Raised when the KMA pollen API request fails."""


class KmaPollenApi:
    def __init__(self, hass, api_key: str, area_no: str) -> None:
        self.hass = hass
        self.api_key = api_key
        self.area_no = area_no
        self._session = async_get_clientsession(hass)

    async def async_fetch_pine(self) -> dict:
        return await self._async_request("getPinePollenRiskIdxV3")

    async def async_fetch_oak(self) -> dict:
        return await self._async_request("getOakPollenRiskIdxV3")

    async def async_fetch_weed(self) -> dict:
        return await self._async_request("getWeedPollenRiskIdxV3")

    async def _async_request(self, endpoint: str) -> dict:
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": "10",
            "dataType": "JSON",
            "areaNo": self.area_no,
            "time": dt_util.now().strftime("%Y%m%d%H"),
        }
        url = f"{KMA_POLLEN_API_BASE}/{endpoint}?{urlencode(params)}"
        try:
            async with self._session.get(url, timeout=30) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise KmaPollenApiError(f"Request failed for {endpoint}: {err}") from err

        header = payload.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            raise KmaPollenApiError(
                f"KMA Pollen API error for {endpoint}: {header.get('resultCode')} {header.get('resultMsg')}"
            )

        items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            raise KmaPollenApiError(f"No items returned for {endpoint}")
        return items[0]
