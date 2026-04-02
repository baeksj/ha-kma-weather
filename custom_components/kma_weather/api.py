from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
import logging
from urllib.parse import urlencode

from homeassistant.util import dt as dt_util

from aiohttp import ClientError

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_API_TIMEOUT, KMA_API_BASE

_LOGGER = logging.getLogger(__name__)


class KmaApiError(Exception):
    """Raised when the KMA API request fails."""


class KmaWeatherApi:
    def __init__(self, hass, api_key: str, nx: int, ny: int) -> None:
        self.hass = hass
        self.api_key = api_key
        self.nx = nx
        self.ny = ny
        self._session = async_get_clientsession(hass)

    async def async_fetch_all(self) -> dict[str, list[dict]]:
        now = dt_util.now()
        ncst_date, ncst_time = self._ultra_ncst_base(now)
        fcst_date, fcst_time = self._ultra_fcst_base(now)
        village_date, village_time = self._village_fcst_base(now)

        # Keep simple, sequential cloud calls for MVP readability.
        current = await self.async_request("getUltraSrtNcst", ncst_date, ncst_time)
        hourly = await self.async_request("getUltraSrtFcst", fcst_date, fcst_time)
        daily = await self.async_request("getVilageFcst", village_date, village_time)

        return {
            "current": current,
            "hourly": hourly,
            "daily": daily,
            "meta": {
                "nx": self.nx,
                "ny": self.ny,
                "requested_at": datetime.now().isoformat(),
                "base_times": {
                    "current": f"{ncst_date} {ncst_time}",
                    "hourly": f"{fcst_date} {fcst_time}",
                    "daily": f"{village_date} {village_time}",
                },
            },
        }

    async def async_request(
        self,
        endpoint: str,
        base_date: str,
        base_time: str,
        *,
        num_of_rows: int = 1000,
    ) -> list[dict]:
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": str(num_of_rows),
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": str(self.nx),
            "ny": str(self.ny),
        }
        url = f"{KMA_API_BASE}/{endpoint}?{urlencode(params)}"
        try:
            async with self._session.get(url, timeout=DEFAULT_API_TIMEOUT) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise KmaApiError(f"Request failed for {endpoint}: {err}") from err

        header = payload.get("response", {}).get("header", {})
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg")
        if result_code != "00":
            raise KmaApiError(
                f"KMA API error for {endpoint}: {result_code} {result_msg}"
            )

        items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if not isinstance(items, list):
            raise KmaApiError(f"Unexpected payload shape for {endpoint}")

        _LOGGER.debug(
            "KMA %s returned %s items for nx=%s ny=%s base=%s %s",
            endpoint,
            len(items),
            self.nx,
            self.ny,
            base_date,
            base_time,
        )
        return items

    @staticmethod
    def _latest_published_slot(now: datetime, schedule: list[str], release_lag_minutes: int) -> tuple[str, str]:
        current = now.replace(second=0, microsecond=0)
        candidates: list[datetime] = []
        for base_time in schedule:
            hour = int(base_time[:2])
            minute = int(base_time[2:])
            slot = current.replace(hour=hour, minute=minute)
            if slot <= current - timedelta(minutes=release_lag_minutes):
                candidates.append(slot)
        if candidates:
            selected = candidates[-1]
            return selected.strftime("%Y%m%d"), selected.strftime("%H%M")

        previous_day = current - timedelta(days=1)
        last_time = schedule[-1]
        selected = previous_day.replace(hour=int(last_time[:2]), minute=int(last_time[2:]), second=0, microsecond=0)
        return selected.strftime("%Y%m%d"), selected.strftime("%H%M")

    @classmethod
    def _ultra_ncst_base(cls, now: datetime) -> tuple[str, str]:
        # Observations are typically published shortly after the hour.
        return cls._latest_published_slot(now, [f"{hour:02d}00" for hour in range(24)], 10)

    @classmethod
    def _ultra_fcst_base(cls, now: datetime) -> tuple[str, str]:
        # Ultra short forecast is typically published around hh:30 and reliably available a bit later.
        schedule = [f"{hour:02d}30" for hour in range(24)]
        return cls._latest_published_slot(now, schedule, 10)

    @classmethod
    def _village_fcst_base(cls, now: datetime) -> tuple[str, str]:
        # Village forecast runs on fixed release slots; allow some lag before using the latest slot.
        schedule = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
        return cls._latest_published_slot(now, schedule, 15)

    @staticmethod
    def bucket_by_forecast_time(items: list[dict]) -> dict[str, dict[str, str]]:
        buckets: dict[str, dict[str, str]] = {}
        for item in items:
            fcst_date = item.get("fcstDate") or item.get("baseDate")
            fcst_time = item.get("fcstTime") or item.get("baseTime")
            category = item.get("category")
            value = item.get("fcstValue") or item.get("obsrValue")
            if not fcst_date or not fcst_time or not category:
                continue
            key = f"{fcst_date}{fcst_time}"
            bucket = buckets.setdefault(key, {"fcstDate": fcst_date, "fcstTime": fcst_time})
            bucket[category] = value
        return buckets

    @staticmethod
    def daily_bucket(items: list[dict]) -> dict[str, dict[str, str]]:
        buckets: dict[str, dict[str, str]] = {}
        for item in items:
            fcst_date = item.get("fcstDate")
            fcst_time = item.get("fcstTime")
            category = item.get("category")
            value = item.get("fcstValue")
            if not fcst_date or not fcst_time or not category:
                continue
            bucket = buckets.setdefault(fcst_date, {"fcstDate": fcst_date})
            bucket[f"{category}_{fcst_time}"] = value
            if category in {"TMX", "TMN"}:
                bucket[category] = value
        return buckets
