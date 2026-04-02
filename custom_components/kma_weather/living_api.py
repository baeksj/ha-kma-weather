from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode

from aiohttp import ClientError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import DEFAULT_API_TIMEOUT, KMA_LIVING_API_BASE


class KmaLivingApiError(Exception):
    pass


class KmaLivingWeatherApi:
    def __init__(self, hass, api_key: str, area_no: str) -> None:
        self.hass = hass
        self.api_key = api_key
        self.area_no = area_no
        self._session = async_get_clientsession(hass)

    async def async_fetch_uv(self) -> dict:
        return await self._async_request("getUVIdxV4")

    async def async_fetch_air_diffusion(self) -> dict:
        return await self._async_request("getAirDiffusionIdxV4")

    async def _async_request(self, endpoint: str) -> dict:
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": "10",
            "dataType": "JSON",
            "areaNo": self.area_no,
            "time": dt_util.now().strftime("%Y%m%d%H"),
        }
        url = f"{KMA_LIVING_API_BASE}/{endpoint}?{urlencode(params)}"
        try:
            async with self._session.get(url, timeout=DEFAULT_API_TIMEOUT) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise KmaLivingApiError(f"Request failed for {endpoint}: {err}") from err

        header = payload.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            raise KmaLivingApiError(f"KMA Living API error for {endpoint}: {header.get('resultCode')} {header.get('resultMsg')}")

        items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            raise KmaLivingApiError(f"No items returned for {endpoint}")
        return items[0]
