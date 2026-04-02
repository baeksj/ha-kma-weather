from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CONSECUTIVE_FAILURES,
    ATTR_DAILY_FORECAST,
    ATTR_DATA_STALE,
    ATTR_FAILURE_TOLERANCE,
    ATTR_GRID,
    ATTR_HOURLY_FORECAST,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KmaWeatherEntity(entry, runtime["coordinator"], runtime["title"], runtime)])


class KmaWeatherEntity(CoordinatorEntity, WeatherEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND

    def __init__(self, entry: ConfigEntry, coordinator, title: str, runtime: dict) -> None:
        super().__init__(coordinator)
        self.runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}_weather"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": title,
            "manufacturer": "Korea Meteorological Administration",
            "model": "KMA Short Forecast API",
        }

    @property
    def condition(self) -> str | None:
        return self.coordinator.data["current"].get("condition")

    @property
    def native_temperature(self) -> float | None:
        return self.coordinator.data["current"].get("temperature")

    @property
    def humidity(self) -> int | None:
        value = self.coordinator.data["current"].get("humidity")
        return int(value) if value is not None else None

    @property
    def native_wind_speed(self) -> float | None:
        return self.coordinator.data["current"].get("wind_speed")

    @property
    def extra_state_attributes(self) -> dict:
        current = self.coordinator.data["current"]
        daily_forecast = self._merged_daily_forecast()
        return {
            "hourly_forecast": self.coordinator.data.get(ATTR_HOURLY_FORECAST, []),
            "daily_forecast": daily_forecast,
            ATTR_GRID: self.coordinator.data.get(ATTR_GRID),
            ATTR_CONSECUTIVE_FAILURES: self.coordinator.data.get(ATTR_CONSECUTIVE_FAILURES, 0),
            ATTR_FAILURE_TOLERANCE: self.coordinator.data.get(ATTR_FAILURE_TOLERANCE),
            ATTR_DATA_STALE: self.coordinator.data.get(ATTR_DATA_STALE, False),
            "wind_bearing": current.get("wind_bearing"),
            "wind_direction": current.get("wind_direction"),
            "precipitation_1h": current.get("precipitation_1h"),
            "today_low": current.get("today_low"),
            "today_high": current.get("today_high"),
            "forecast_sky": current.get("forecast_sky"),
            "forecast_pty": current.get("forecast_pty"),
            "raw_current": current.get("raw", {}),
            "base_times": self.coordinator.data.get("base_times"),
            "midterm_connected": self.runtime.get("midterm") is not None,
        }

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        return self.coordinator.data.get(ATTR_HOURLY_FORECAST)

    async def async_forecast_daily(self) -> list[Forecast] | None:
        return self._merged_daily_forecast()

    def _merged_daily_forecast(self) -> list[Forecast]:
        base_daily = list(self.coordinator.data.get(ATTR_DAILY_FORECAST, []))
        existing_dates = {
            item["datetime"]
            for item in base_daily
            if isinstance(item, dict) and item.get("datetime")
        }

        midterm_runtime = self.runtime.get("midterm")
        if not midterm_runtime:
            return base_daily

        midterm_coordinator = midterm_runtime.get("coordinator")
        if not midterm_coordinator or not midterm_coordinator.data:
            return base_daily

        tm_fc = midterm_coordinator.data.get("tmFc")
        temperature = midterm_coordinator.data.get("temperature") or {}
        if not tm_fc:
            return base_daily

        try:
            base_date = datetime.strptime(tm_fc, "%Y%m%d%H%M").date()
        except ValueError:
            return base_daily

        merged = list(base_daily)
        for day in range(4, 11):
            forecast_date = (base_date + timedelta(days=day)).isoformat()
            if forecast_date in existing_dates:
                continue
            merged.append(
                Forecast(
                    datetime=forecast_date,
                    native_templow=_to_float_or_none(temperature.get(f"taMin{day}")),
                    native_temperature=_to_float_or_none(temperature.get(f"taMax{day}")),
                    condition=None,
                )
            )

        merged.sort(key=lambda item: item["datetime"])
        return merged


def _to_float_or_none(value) -> float | None:
    if value in (None, "", "-", "_", "N/A"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
