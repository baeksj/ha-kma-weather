from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode

from aiohttp import ClientError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import DEFAULT_API_TIMEOUT, KMA_MIDTERM_API_BASE


class KmaMidtermApiError(Exception):
    """Raised when the KMA midterm API request fails."""


class KmaMidtermApi:
    def __init__(self, hass, api_key: str, stn_id: str, reg_id: str) -> None:
        self.hass = hass
        self.api_key = api_key
        self.stn_id = stn_id
        self.reg_id = reg_id
        self._session = async_get_clientsession(hass)

    async def async_fetch_all(self) -> dict:
        tm_fc = self._latest_tm_fc()
        summary = await self._async_request("getMidFcst", {"stnId": self.stn_id, "tmFc": tm_fc})
        temperature = await self._async_request("getMidTa", {"regId": self.reg_id, "tmFc": tm_fc})
        return {
            "tmFc": tm_fc,
            "summary": summary,
            "temperature": temperature,
        }

    async def _async_request(self, endpoint: str, extra_params: dict[str, str]) -> dict:
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": "10",
            "dataType": "JSON",
            **extra_params,
        }
        url = f"{KMA_MIDTERM_API_BASE}/{endpoint}?{urlencode(params)}"
        try:
            async with self._session.get(url, timeout=DEFAULT_API_TIMEOUT) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise KmaMidtermApiError(f"Request failed for {endpoint}: {err}") from err

        header = payload.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            raise KmaMidtermApiError(
                f"KMA Midterm API error for {endpoint}: {header.get('resultCode')} {header.get('resultMsg')}"
            )

        items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            raise KmaMidtermApiError(f"No items returned for {endpoint}")
        return items[0]

    @staticmethod
    def _latest_tm_fc() -> str:
        now = dt_util.now().replace(second=0, microsecond=0)
        release_lag = timedelta(minutes=30)
        six = now.replace(hour=6, minute=0)
        eighteen = now.replace(hour=18, minute=0)
        if now >= eighteen + release_lag:
            selected = eighteen
        elif now >= six + release_lag:
            selected = six
        else:
            selected = (now - timedelta(days=1)).replace(hour=18, minute=0)
        return selected.strftime("%Y%m%d%H%M")
