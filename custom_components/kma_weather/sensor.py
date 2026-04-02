from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


@dataclass(frozen=True)
class AirQualitySensorDescription:
    key: str
    name: str
    unit: str | None = None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT
    value_keys: tuple[str, ...] = ()
    extra_keys: tuple[str, ...] = ()


AIR_QUALITY_SENSORS: tuple[AirQualitySensorDescription, ...] = (
    AirQualitySensorDescription(
        key="pm10",
        name="AirKorea PM10",
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        value_keys=("pm10Value",),
        extra_keys=("pm10Grade", "pm10Flag"),
    ),
    AirQualitySensorDescription(
        key="pm25",
        name="AirKorea PM2.5",
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        value_keys=("pm25Value",),
        extra_keys=("pm25Grade", "pm25Flag"),
    ),
    AirQualitySensorDescription(
        key="o3",
        name="AirKorea O3",
        unit="ppm",
        value_keys=("o3Value",),
        extra_keys=("o3Grade", "o3Flag"),
    ),
    AirQualitySensorDescription(
        key="no2",
        name="AirKorea NO2",
        unit="ppm",
        value_keys=("no2Value",),
        extra_keys=("no2Grade", "no2Flag"),
    ),
    AirQualitySensorDescription(
        key="co",
        name="AirKorea CO",
        unit="ppm",
        value_keys=("coValue",),
        extra_keys=("coGrade", "coFlag"),
    ),
    AirQualitySensorDescription(
        key="so2",
        name="AirKorea SO2",
        unit="ppm",
        value_keys=("so2Value",),
        extra_keys=("so2Grade", "so2Flag"),
    ),
    AirQualitySensorDescription(
        key="khai",
        name="AirKorea Integrated Air Quality Index",
        value_keys=("khaiValue",),
        extra_keys=("khaiGrade",),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime["coordinator"]
    entities = [
        KmaGridSensor(entry, coordinator, runtime),
        KmaAreaCodeSensor(entry, coordinator, runtime),
        KmaRegionNameSensor(entry, coordinator, runtime),
    ]

    living = runtime.get("living", {})
    if "uv" in living:
        entities.append(KmaLivingValueSensor(entry, living["uv"]["coordinator"], runtime, "uv", "KMA UV Index"))
    if "air_diffusion" in living:
        entities.append(
            KmaLivingValueSensor(
                entry,
                living["air_diffusion"]["coordinator"],
                runtime,
                "air_diffusion",
                "KMA Air Diffusion Index",
            )
        )

    air_quality = runtime.get("air_quality")
    if air_quality:
        air_coordinator = air_quality["coordinator"]
        entities.append(KmaAirStationSensor(entry, air_coordinator, runtime))
        entities.extend(
            KmaAirQualityValueSensor(entry, air_coordinator, runtime, description)
            for description in AIR_QUALITY_SENSORS
        )

    async_add_entities(entities)


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
            "model": "KMA Weather + AirKorea",
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


class KmaLivingValueSensor(_BaseKmaSensor):
    def __init__(self, entry, coordinator, runtime, kind: str, name: str):
        super().__init__(entry, coordinator, runtime, kind, name)
        self.kind = kind
        self.coordinator = coordinator

    @property
    def native_value(self):
        return self.coordinator.data.get("h0") or self.coordinator.data.get("h3")

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        descriptions = {
            "uv": {
                "required_api": "기상청_생활기상지수 조회서비스(3.0)",
                "endpoint": "getUVIdxV4",
            },
            "air_diffusion": {
                "required_api": "기상청_생활기상지수 조회서비스(3.0)",
                "endpoint": "getAirDiffusionIdxV4",
            },
        }
        attrs = {
            "configured": True,
            "kind": self.kind,
            **descriptions.get(self.kind, {}),
        }
        for key, value in self.coordinator.data.items():
            attrs[key] = value
        return attrs


class KmaAirStationSensor(_BaseKmaSensor):
    def __init__(self, entry, coordinator, runtime):
        super().__init__(entry, coordinator, runtime, "air_station", "AirKorea Station")
        self.coordinator = coordinator

    @property
    def native_value(self):
        station = self.runtime.get("air_station") or {}
        return station.get("station_name")

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        station = self.runtime.get("air_station") or {}
        attrs = {
            "required_api": "에어코리아 대기오염정보 조회서비스",
            "endpoint": "getMsrstnAcctoRltmMesureDnsty",
        }
        for key in ("addr", "mang_name", "item", "year", "region_hint", "geo_distance_km", "lat", "lon"):
            if key in station:
                attrs[key] = station.get(key)
        if self.coordinator.data:
            attrs["data_time"] = self.coordinator.data.get("dataTime")
        return attrs


class KmaAirQualityValueSensor(_BaseKmaSensor):
    def __init__(
        self,
        entry: ConfigEntry,
        coordinator,
        runtime: dict[str, Any],
        description: AirQualitySensorDescription,
    ) -> None:
        super().__init__(entry, coordinator, runtime, description.key, description.name)
        self.entity_description = description
        self.coordinator = coordinator
        self._attr_native_unit_of_measurement = description.unit
        self._attr_state_class = description.state_class
        self._attr_suggested_display_precision = 1 if description.unit else 0

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        raw = self._raw_value()
        return self._parse_value(raw)

    @property
    def extra_state_attributes(self):
        attrs = {
            "required_api": "에어코리아 대기오염정보 조회서비스",
            "endpoint": "getMsrstnAcctoRltmMesureDnsty",
            "station_name": (self.runtime.get("air_station") or {}).get("station_name"),
            "data_time": self.coordinator.data.get("dataTime"),
        }
        for key in self.entity_description.extra_keys:
            value = self.coordinator.data.get(key)
            if value not in (None, ""):
                attrs[key] = value
        return attrs

    def _raw_value(self):
        for key in self.entity_description.value_keys:
            value = self.coordinator.data.get(key)
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def _parse_value(value: Any):
        if value in (None, "", "-", "_", "N/A"):
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned in {"-", "_", "통신장애", "점검중"}:
                return None
            try:
                numeric = float(cleaned)
            except ValueError:
                return cleaned
            if numeric.is_integer():
                return int(numeric)
            return numeric
        return value
