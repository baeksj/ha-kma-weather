from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .air_station_lookup import async_nearest_air_station
from .airkorea_api import AirKoreaApi
from .airkorea_coordinator import AirKoreaCoordinator
from .api import KmaWeatherApi
from .const import (
    CONF_API_KEY,
    CONF_AREA_NO,
    CONF_ENABLED_API_GROUPS,
    CONF_LOCATION_NAME,
    CONF_MAX_CONSECUTIVE_FAILURES,
    CONF_NX,
    CONF_NY,
    API_GROUP_AIR_QUALITY,
    API_GROUP_LIVING_WEATHER,
    API_GROUP_MIDTERM_FORECAST,
    API_GROUP_POLLEN,
    DEFAULT_MAX_CONSECUTIVE_FAILURES,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import KmaWeatherDataCoordinator
from .grid import latlon_to_grid
from .living_api import KmaLivingWeatherApi
from .living_coordinator import KmaLivingCoordinator
from .midterm_api import KmaMidtermApi
from .midterm_coordinator import KmaMidtermCoordinator
from .midterm_region import midterm_land_reg_id_for_region, midterm_reg_id_for_region, midterm_stn_id_for_region
from .pollen_api import KmaPollenApi
from .pollen_coordinator import KmaPollenCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    data = entry.data
    nx = data.get(CONF_NX)
    ny = data.get(CONF_NY)
    latitude = float(data[CONF_LATITUDE])
    longitude = float(data[CONF_LONGITUDE])
    if nx is None or ny is None:
        nx, ny = latlon_to_grid(latitude, longitude)

    max_failures = int(
        entry.options.get(CONF_MAX_CONSECUTIVE_FAILURES, DEFAULT_MAX_CONSECUTIVE_FAILURES)
    )
    api = KmaWeatherApi(hass, data[CONF_API_KEY], int(nx), int(ny))
    coordinator = KmaWeatherDataCoordinator(
        hass,
        api,
        config_entry=entry,
        max_consecutive_failures=max_failures,
    )
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        _LOGGER.warning("KMA Weather initial data fetch failed, will retry on next update cycle")

    air_station = await async_nearest_air_station(hass, latitude, longitude)

    runtime = {
        "api": api,
        "coordinator": coordinator,
        "title": data.get(CONF_LOCATION_NAME) or entry.title,
        "grid": {"nx": int(nx), "ny": int(ny)},
        "area_no": data.get(CONF_AREA_NO),
        "region_level_1": data.get("region_level_1"),
        "region_level_2": data.get("region_level_2"),
        "region_level_3": data.get("region_level_3"),
        "living": {},
        "pollen": {},
        "air_station": air_station,
        "air_quality": None,
        "midterm": None,
        "group_status": {},
    }

    enabled_groups = entry.options.get(CONF_ENABLED_API_GROUPS, [])
    area_no = data.get(CONF_AREA_NO)
    base_api_key = data.get(CONF_API_KEY)
    if area_no and base_api_key and API_GROUP_LIVING_WEATHER in enabled_groups:
        for kind in ("uv", "air_diffusion"):
            try:
                living_api = KmaLivingWeatherApi(hass, base_api_key, str(area_no))
                living_coordinator = KmaLivingCoordinator(
                    hass,
                    living_api,
                    kind,
                    config_entry=entry,
                    max_consecutive_failures=max_failures,
                )
            except Exception as err:
                _LOGGER.warning("Failed to create living weather group '%s': %s", kind, err)
                continue
            await living_coordinator.async_refresh()
            runtime["living"][kind] = {"api": living_api, "coordinator": living_coordinator}
            if not living_coordinator.last_update_success:
                _LOGGER.warning(
                    "Living weather group '%s' initial fetch failed, will retry on next update", kind
                )

    if API_GROUP_LIVING_WEATHER in enabled_groups and runtime["living"]:
        runtime["group_status"][API_GROUP_LIVING_WEATHER] = {"ok": True}

    if area_no and base_api_key and API_GROUP_POLLEN in enabled_groups:
        # `getWeedPollenRiskIdxV3` is currently not available from the public API.
        # Keep the supported subset enabled so the rest of the pollen group remains usable.
        for kind in ("pine", "oak"):
            try:
                pollen_api = KmaPollenApi(hass, base_api_key, str(area_no))
                pollen_coordinator = KmaPollenCoordinator(
                    hass,
                    pollen_api,
                    kind,
                    config_entry=entry,
                    max_consecutive_failures=max_failures,
                )
            except Exception as err:
                _LOGGER.warning("Failed to create pollen group '%s': %s", kind, err)
                continue
            await pollen_coordinator.async_refresh()
            runtime["pollen"][kind] = {"api": pollen_api, "coordinator": pollen_coordinator}
            if not pollen_coordinator.last_update_success:
                _LOGGER.warning(
                    "Pollen group '%s' initial fetch failed, will retry on next update", kind
                )

    if API_GROUP_POLLEN in enabled_groups and runtime["pollen"]:
        runtime["group_status"][API_GROUP_POLLEN] = {"ok": True}

    if API_GROUP_AIR_QUALITY in enabled_groups:
        if not air_station:
            _LOGGER.warning("AirKorea air quality group enabled but no nearby station mapping was found")
            runtime["group_status"][API_GROUP_AIR_QUALITY] = {
                "ok": False,
                "error": "No nearby AirKorea station mapping found",
            }
        elif not base_api_key:
            runtime["group_status"][API_GROUP_AIR_QUALITY] = {
                "ok": False,
                "error": "Missing base API key",
            }
        else:
            try:
                air_api = AirKoreaApi(hass, base_api_key, str(air_station["station_name"]))
                air_coordinator = AirKoreaCoordinator(
                    hass,
                    air_api,
                    config_entry=entry,
                    max_consecutive_failures=max_failures,
                )
            except Exception as err:
                _LOGGER.warning("Failed to create AirKorea air quality group: %s", err)
                runtime["group_status"][API_GROUP_AIR_QUALITY] = {"ok": False, "error": str(err)}
            else:
                await air_coordinator.async_refresh()
                runtime["air_quality"] = {"api": air_api, "coordinator": air_coordinator}
                if not air_coordinator.last_update_success:
                    _LOGGER.warning(
                        "AirKorea air quality initial fetch failed, will retry on next update"
                    )
                runtime["group_status"][API_GROUP_AIR_QUALITY] = {"ok": True}

    if API_GROUP_MIDTERM_FORECAST in enabled_groups:
        if not base_api_key:
            runtime["group_status"][API_GROUP_MIDTERM_FORECAST] = {
                "ok": False,
                "error": "Missing base API key",
            }
        else:
            try:
                stn_id = midterm_stn_id_for_region(runtime.get("region_level_1"))
                reg_id = midterm_reg_id_for_region(runtime.get("region_level_1"))
                land_reg_id = midterm_land_reg_id_for_region(runtime.get("region_level_1"))
                midterm_api = KmaMidtermApi(hass, base_api_key, stn_id, reg_id, land_reg_id)
                midterm_coordinator = KmaMidtermCoordinator(
                    hass,
                    midterm_api,
                    config_entry=entry,
                    max_consecutive_failures=max_failures,
                )
            except Exception as err:
                _LOGGER.warning("Failed to create KMA midterm forecast group: %s", err)
                runtime["group_status"][API_GROUP_MIDTERM_FORECAST] = {"ok": False, "error": str(err)}
            else:
                await midterm_coordinator.async_refresh()
                runtime["midterm"] = {
                    "api": midterm_api,
                    "coordinator": midterm_coordinator,
                    "stn_id": stn_id,
                    "reg_id": reg_id,
                    "land_reg_id": land_reg_id,
                }
                if not midterm_coordinator.last_update_success:
                    _LOGGER.warning(
                        "KMA midterm forecast initial fetch failed, will retry on next update"
                    )
                runtime["group_status"][API_GROUP_MIDTERM_FORECAST] = {"ok": True}

    hass.data[DOMAIN][entry.entry_id] = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    except ValueError:
        _LOGGER.debug(
            "Platforms were not registered for entry %s, skipping platform unload",
            entry.entry_id,
        )
        unload_ok = True
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
