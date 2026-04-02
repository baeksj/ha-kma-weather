from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.weather import Forecast
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import KmaApiError, KmaWeatherApi
from .const import (
    ATTR_CONSECUTIVE_FAILURES,
    ATTR_DAILY_FORECAST,
    ATTR_DATA_STALE,
    ATTR_FAILURE_TOLERANCE,
    ATTR_GRID,
    ATTR_HOURLY_FORECAST,
    DEFAULT_MAX_CONSECUTIVE_FAILURES,
    DEFAULT_SCAN_INTERVAL,
    PTY_DRIZZLE,
    PTY_NONE,
    PTY_RAIN,
    PTY_RAIN_SNOW,
    PTY_RAIN_SNOW_FLURRY,
    PTY_SHOWER,
    PTY_SNOW,
    PTY_SNOW_FLURRY,
    SKY_CLEAR,
    SKY_CLOUDY,
    SKY_PARTLY_CLOUDY,
)

_LOGGER = logging.getLogger(__name__)


class _FailureTolerantCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """연속 실패 허용 로직을 공통으로 제공하는 베이스 coordinator.

    실패 횟수가 max_consecutive_failures 이하이고 이전 데이터가 있으면
    UpdateFailed를 raise하지 않고 이전 데이터를 유지한다.
    """

    def __init__(
        self,
        *args: Any,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._max_consecutive_failures = max(1, int(max_consecutive_failures))
        self._consecutive_failures = 0

    async def _fetch(self) -> dict[str, Any]:
        raise NotImplementedError

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self._fetch()
            self._consecutive_failures = 0
            return data
        except UpdateFailed as err:
            self._consecutive_failures += 1
            if self._consecutive_failures <= self._max_consecutive_failures and self.data is not None:
                _LOGGER.warning(
                    "%s: update failed (%d/%d), keeping previous data: %s",
                    self.name,
                    self._consecutive_failures,
                    self._max_consecutive_failures,
                    err,
                )
                return self.data
            raise


PTY_TO_CONDITION = {
    PTY_NONE: None,
    PTY_RAIN: "rainy",
    PTY_RAIN_SNOW: "snowy-rainy",
    PTY_SNOW: "snowy",
    PTY_SHOWER: "pouring",
    PTY_DRIZZLE: "rainy",
    PTY_RAIN_SNOW_FLURRY: "snowy-rainy",
    PTY_SNOW_FLURRY: "snowy",
}

SKY_TO_CONDITION = {
    SKY_CLEAR: "sunny",
    SKY_PARTLY_CLOUDY: "partlycloudy",
    SKY_CLOUDY: "cloudy",
}


class KmaWeatherDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: KmaWeatherApi,
        *,
        config_entry=None,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="KMA Weather",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=config_entry,
        )
        self.api = api
        self._max_consecutive_failures = max(1, int(max_consecutive_failures))
        self._consecutive_failures = 0

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            raw = await self.api.async_fetch_all()
            hourly = self._normalize_hourly(raw["hourly"])
            daily = self._normalize_daily(raw["daily"])
            current = self._normalize_current(raw["current"], raw["hourly"], raw["daily"])
            self._consecutive_failures = 0
            return {
                **raw["meta"],
                "current": current,
                ATTR_HOURLY_FORECAST: hourly,
                ATTR_DAILY_FORECAST: daily,
                ATTR_GRID: {"nx": self.api.nx, "ny": self.api.ny},
                ATTR_CONSECUTIVE_FAILURES: 0,
                ATTR_FAILURE_TOLERANCE: self._max_consecutive_failures,
                ATTR_DATA_STALE: False,
            }
        except KmaApiError as err:
            self._consecutive_failures += 1
            if self._consecutive_failures <= self._max_consecutive_failures and self.data:
                _LOGGER.warning(
                    "KMA API error (%s/%s). Keeping previous state: %s",
                    self._consecutive_failures,
                    self._max_consecutive_failures,
                    err,
                )
                return {
                    **self.data,
                    ATTR_CONSECUTIVE_FAILURES: self._consecutive_failures,
                    ATTR_FAILURE_TOLERANCE: self._max_consecutive_failures,
                    ATTR_DATA_STALE: True,
                }
            raise UpdateFailed(str(err)) from err

    def _normalize_current(self, items: list[dict], hourly_items: list[dict], daily_items: list[dict]) -> dict:
        mapped = {item["category"]: item.get("obsrValue") for item in items if item.get("category")}
        pty = str(mapped.get("PTY", PTY_NONE))

        hourly_buckets = self.api.bucket_by_forecast_time(hourly_items)
        first_hourly = hourly_buckets[sorted(hourly_buckets.keys())[0]] if hourly_buckets else {}
        hourly_sky = str(first_hourly.get("SKY")) if first_hourly.get("SKY") is not None else None
        hourly_pty = str(first_hourly.get("PTY", pty or PTY_NONE))

        daily_buckets = self.api.daily_bucket(daily_items)
        today_key = sorted(daily_buckets.keys())[0] if daily_buckets else None
        today_bucket = daily_buckets.get(today_key, {}) if today_key else {}

        wind_bearing = self._to_int(mapped.get("VEC"))
        return {
            "temperature": self._to_float(mapped.get("T1H")),
            "humidity": self._to_float(mapped.get("REH")),
            "wind_speed": self._to_float(mapped.get("WSD")),
            "wind_bearing": wind_bearing,
            "wind_direction": self._bearing_to_direction(wind_bearing),
            "precipitation_1h": self._to_precip_float(mapped.get("RN1")),
            "condition": self._condition_from_values(hourly_sky, hourly_pty),
            "today_low": self._to_float(today_bucket.get("TMN")),
            "today_high": self._to_float(today_bucket.get("TMX")),
            "forecast_sky": hourly_sky,
            "forecast_pty": hourly_pty,
            "raw": mapped,
        }

    def _normalize_hourly(self, items: list[dict]) -> list[Forecast]:
        buckets = self.api.bucket_by_forecast_time(items)
        forecasts: list[Forecast] = []
        for key in sorted(buckets.keys())[:24]:
            bucket = buckets[key]
            dt_value = self._parse_forecast_dt(bucket["fcstDate"], bucket["fcstTime"])
            forecasts.append(
                Forecast(
                    datetime=dt_value.isoformat(),
                    native_temperature=self._to_float(bucket.get("T1H") or bucket.get("TMP")),
                    native_precipitation=self._to_precip_float(bucket.get("RN1")),
                    precipitation_probability=self._to_int(bucket.get("POP")),
                    humidity=self._to_int(bucket.get("REH")),
                    condition=self._condition_from_values(
                        str(bucket.get("SKY", SKY_CLEAR)),
                        str(bucket.get("PTY", PTY_NONE)),
                    ),
                )
            )
        return forecasts

    def _normalize_daily(self, items: list[dict]) -> list[Forecast]:
        buckets = self.api.daily_bucket(items)
        forecasts: list[Forecast] = []
        for fcst_date in sorted(buckets.keys())[:5]:
            bucket = buckets[fcst_date]
            condition = self._daily_condition(bucket)
            forecasts.append(
                Forecast(
                    datetime=datetime.strptime(fcst_date, "%Y%m%d").date().isoformat(),
                    native_templow=self._to_float(bucket.get("TMN")),
                    native_temperature=self._to_float(bucket.get("TMX")),
                    precipitation_probability=self._daily_pop(bucket),
                    condition=condition,
                )
            )
        return forecasts

    def _daily_condition(self, bucket: dict[str, str]) -> str | None:
        for time_key in ("0600", "0900", "1200", "1500"):
            pty = bucket.get(f"PTY_{time_key}")
            sky = bucket.get(f"SKY_{time_key}")
            if pty and pty != PTY_NONE:
                return self._condition_from_values(str(sky or SKY_CLOUDY), str(pty))
            if sky:
                return self._condition_from_values(str(sky), PTY_NONE)
        return None

    def _daily_pop(self, bucket: dict[str, str]) -> int | None:
        values = []
        for key, value in bucket.items():
            if key.startswith("POP_"):
                parsed = self._to_int(value)
                if parsed is not None:
                    values.append(parsed)
        return max(values) if values else None

    @staticmethod
    def _condition_from_values(sky: str | None, pty: str) -> str | None:
        if pty and pty != PTY_NONE:
            return PTY_TO_CONDITION.get(pty, "rainy")
        if sky is None:
            return None
        return SKY_TO_CONDITION.get(sky, None)

    @staticmethod
    def _parse_forecast_dt(fcst_date: str, fcst_time: str) -> datetime:
        naive = datetime.strptime(f"{fcst_date}{fcst_time}", "%Y%m%d%H%M")
        return naive.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

    @staticmethod
    def _to_float(value) -> float | None:
        if value in (None, "", "-999"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value) -> int | None:
        parsed = KmaWeatherDataCoordinator._to_float(value)
        return int(parsed) if parsed is not None else None

    @staticmethod
    def _to_precip_float(value) -> float | None:
        if value in (None, "", "강수없음"):
            return 0.0
        if isinstance(value, str):
            cleaned = value.replace("mm", "").replace("cm", "").replace("~", "-").strip()
            if cleaned in {"1.0미만", "1mm 미만"}:
                return 0.0
            if "-" in cleaned:
                cleaned = cleaned.split("-", 1)[0].strip()
            value = cleaned
        return KmaWeatherDataCoordinator._to_float(value)

    @staticmethod
    def _bearing_to_direction(bearing: int | None) -> str | None:
        if bearing is None:
            return None
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int(((bearing + 22.5) % 360) / 45)
        return directions[idx]
