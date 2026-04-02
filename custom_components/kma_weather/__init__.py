from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .api import KmaWeatherApi
from .const import (
    CONF_API_KEY,
    CONF_AREA_NO,
    CONF_LOCATION_NAME,
    CONF_MAX_CONSECUTIVE_FAILURES,
    CONF_NX,
    CONF_NY,
    DEFAULT_MAX_CONSECUTIVE_FAILURES,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import KmaWeatherDataCoordinator
from .grid import latlon_to_grid
from .living_api import KmaLivingWeatherApi
from .living_coordinator import KmaLivingCoordinator


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    data = entry.data
    nx = data.get(CONF_NX)
    ny = data.get(CONF_NY)
    if nx is None or ny is None:
        latitude = data[CONF_LATITUDE]
        longitude = data[CONF_LONGITUDE]
        nx, ny = latlon_to_grid(float(latitude), float(longitude))

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
    }

    enabled_groups = entry.options.get("enabled_api_groups", [])
    area_no = data.get(CONF_AREA_NO)
    base_api_key = data.get(CONF_API_KEY)
    if area_no and base_api_key and "living_weather" in enabled_groups:
        for kind in ("uv", "air_diffusion"):
            living_api = KmaLivingWeatherApi(hass, base_api_key, str(area_no))
            living_coordinator = KmaLivingCoordinator(hass, living_api, kind)
            await living_coordinator.async_config_entry_first_refresh()
            runtime["living"][kind] = {
                "api": living_api,
                "coordinator": living_coordinator,
            }

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
