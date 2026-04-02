from __future__ import annotations

from homeassistant.components.weather import (
    ATTR_FORECAST_HOURLY,
    ATTR_FORECAST_DAILY,
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
    async_add_entities([KmaWeatherEntity(entry, runtime["coordinator"], runtime["title"])])


class KmaWeatherEntity(CoordinatorEntity, WeatherEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND

    def __init__(self, entry: ConfigEntry, coordinator, title: str) -> None:
        super().__init__(coordinator)
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
        return {
            ATTR_FORECAST_HOURLY: self.coordinator.data.get(ATTR_HOURLY_FORECAST, []),
            ATTR_FORECAST_DAILY: self.coordinator.data.get(ATTR_DAILY_FORECAST, []),
            ATTR_GRID: self.coordinator.data.get(ATTR_GRID),
            ATTR_CONSECUTIVE_FAILURES: self.coordinator.data.get(ATTR_CONSECUTIVE_FAILURES, 0),
            ATTR_FAILURE_TOLERANCE: self.coordinator.data.get(ATTR_FAILURE_TOLERANCE),
            ATTR_DATA_STALE: self.coordinator.data.get(ATTR_DATA_STALE, False),
            "raw_current": self.coordinator.data["current"].get("raw", {}),
            "base_times": self.coordinator.data.get("base_times"),
        }

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        return self.coordinator.data.get(ATTR_HOURLY_FORECAST)

    async def async_forecast_daily(self) -> list[Forecast] | None:
        return self.coordinator.data.get(ATTR_DAILY_FORECAST)
