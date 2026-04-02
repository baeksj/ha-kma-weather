from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .air_station_lookup import nearest_air_station
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
from .midterm_region import midterm_reg_id_for_region, midterm_stn_id_for_region
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

    api = KmaWeatherApi(hass, data[CONF_API_KEY], int(nx), int(ny))
    coordinator = KmaWeatherDataCoordinator(
        hass,
        api,
        max_consecutive_failures=int(
            entry.options.get(
                CONF_MAX_CONSECUTIVE_FAILURES,
                DEFAULT_MAX_CONSECUTIVE_FAILURES,
            )
        ),
    )
    await coordinator.async_config_entry_first_refresh()

    air_station = nearest_air_station(latitude, longitude)

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
                living_coordinator = KmaLivingCoordinator(hass, living_api, kind)
                await living_coordinator.async_config_entry_first_refresh()
                runtime["living"][kind] = {
                    "api": living_api,
                    "coordinator": living_coordinator,
                }
            except Exception as err:
                _LOGGER.warning("Failed to set up living weather sensor group '%s': %s", kind, err)
                runtime["group_status"][f"living:{kind}"] = {"ok": False, "error": str(err)}

    if API_GROUP_LIVING_WEATHER in enabled_groups and runtime["living"]:
        runtime["group_status"][API_GROUP_LIVING_WEATHER] = {"ok": True}

    if area_no and base_api_key and API_GROUP_POLLEN in enabled_groups:
        for kind in ("pine", "oak", "weed"):
            try:
                pollen_api = KmaPollenApi(hass, base_api_key, str(area_no))
                pollen_coordinator = KmaPollenCoordinator(hass, pollen_api, kind)
                await pollen_coordinator.async_config_entry_first_refresh()
                runtime["pollen"][kind] = {
                    "api": pollen_api,
                    "coordinator": pollen_coordinator,
                }
            except Exception as err:
                _LOGGER.warning("Failed to set up pollen sensor group '%s': %s", kind, err)
                runtime["group_status"][f"pollen:{kind}"] = {"ok": False, "error": str(err)}

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
                air_coordinator = AirKoreaCoordinator(hass, air_api)
                await air_coordinator.async_config_entry_first_refresh()
                runtime["air_quality"] = {
                    "api": air_api,
                    "coordinator": air_coordinator,
                }
                runtime["group_status"][API_GROUP_AIR_QUALITY] = {"ok": True}
            except Exception as err:
                _LOGGER.warning("Failed to set up AirKorea air quality group: %s", err)
                runtime["group_status"][API_GROUP_AIR_QUALITY] = {"ok": False, "error": str(err)}

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
                midterm_api = KmaMidtermApi(hass, base_api_key, stn_id, reg_id)
                midterm_coordinator = KmaMidtermCoordinator(hass, midterm_api)
                await midterm_coordinator.async_config_entry_first_refresh()
                runtime["midterm"] = {
                    "api": midterm_api,
                    "coordinator": midterm_coordinator,
                    "stn_id": stn_id,
                    "reg_id": reg_id,
                }
                runtime["group_status"][API_GROUP_MIDTERM_FORECAST] = {"ok": True}
            except Exception as err:
                _LOGGER.warning("Failed to set up KMA midterm forecast group: %s", err)
                runtime["group_status"][API_GROUP_MIDTERM_FORECAST] = {"ok": False, "error": str(err)}

    hass.data[DOMAIN][entry.entry_id] = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
