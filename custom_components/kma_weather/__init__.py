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

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "title": data.get(CONF_LOCATION_NAME) or entry.title,
        "grid": {"nx": int(nx), "ny": int(ny)},
        "area_no": data.get(CONF_AREA_NO),
    }
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
