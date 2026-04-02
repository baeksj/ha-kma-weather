from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime["coordinator"]
    async_add_entities(
        [
            KmaGridSensor(entry, coordinator, runtime),
            KmaAreaCodeSensor(entry, coordinator, runtime),
            KmaRegionNameSensor(entry, coordinator, runtime),
        ]
    )


class _BaseKmaSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, coordinator, runtime: dict, suffix: str, name: str) -> None:
        super().__init__(coordinator)
        self.runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": runtime["title"],
            "manufacturer": "Korea Meteorological Administration",
            "model": "KMA Short Forecast API",
        }


class KmaGridSensor(_BaseKmaSensor):
    def __init__(self, entry, coordinator, runtime):
        super().__init__(entry, coordinator, runtime, "grid", "KMA Grid")

    @property
    def native_value(self):
        grid = self.runtime.get("grid", {})
        return f"{grid.get('nx')},{grid.get('ny')}"

    @property
    def extra_state_attributes(self):
        grid = self.runtime.get("grid", {})
        return {"nx": grid.get("nx"), "ny": grid.get("ny")}


class KmaAreaCodeSensor(_BaseKmaSensor):
    def __init__(self, entry, coordinator, runtime):
        super().__init__(entry, coordinator, runtime, "area_code", "KMA Area Code")

    @property
    def native_value(self):
        return self.runtime.get("area_no")


class KmaRegionNameSensor(_BaseKmaSensor):
    def __init__(self, entry, coordinator, runtime):
        super().__init__(entry, coordinator, runtime, "region_name", "KMA Region")

    @property
    def native_value(self):
        parts = [
            self.runtime.get("region_level_1"),
            self.runtime.get("region_level_2"),
            self.runtime.get("region_level_3"),
        ]
        return " ".join([p for p in parts if p]) or None

    @property
    def extra_state_attributes(self):
        return {
            "level1": self.runtime.get("region_level_1"),
            "level2": self.runtime.get("region_level_2"),
            "level3": self.runtime.get("region_level_3"),
        }
