from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_API_KEY,
    CONF_LOCATION_NAME,
    CONF_MAX_CONSECUTIVE_FAILURES,
    CONF_NX,
    CONF_NY,
    CONF_ZONE,
    DEFAULT_MAX_CONSECUTIVE_FAILURES,
    DEFAULT_NAME,
    DOMAIN,
)
from .grid import latlon_to_grid


class KmaWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            title = user_input.get(CONF_LOCATION_NAME) or DEFAULT_NAME
            zone_entity_id = user_input.get(CONF_ZONE)
            state = self.hass.states.get(zone_entity_id) if zone_entity_id else None

            if state is None:
                errors["base"] = "zone_not_found"
            else:
                latitude = state.attributes.get(CONF_LATITUDE)
                longitude = state.attributes.get(CONF_LONGITUDE)
                if latitude is None or longitude is None:
                    errors["base"] = "zone_missing_coordinates"
                else:
                    data = dict(user_input)
                    data[CONF_LATITUDE] = float(latitude)
                    data[CONF_LONGITUDE] = float(longitude)
                    nx, ny = latlon_to_grid(float(latitude), float(longitude))
                    data[CONF_NX] = nx
                    data[CONF_NY] = ny

                    await self.async_set_unique_id(f"{data[CONF_NX]}_{data[CONF_NY]}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=title,
                        data=data,
                        options={
                            CONF_MAX_CONSECUTIVE_FAILURES: DEFAULT_MAX_CONSECUTIVE_FAILURES,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_LOCATION_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_ZONE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="zone")
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "KmaWeatherOptionsFlow":
        return KmaWeatherOptionsFlow(config_entry)


class KmaWeatherOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            max_failures = int(
                user_input.get(
                    CONF_MAX_CONSECUTIVE_FAILURES,
                    self.entry.options.get(
                        CONF_MAX_CONSECUTIVE_FAILURES,
                        DEFAULT_MAX_CONSECUTIVE_FAILURES,
                    ),
                )
            )
            return self.async_create_entry(
                title="",
                data={
                    **self.entry.options,
                    CONF_MAX_CONSECUTIVE_FAILURES: max(1, min(max_failures, 20)),
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MAX_CONSECUTIVE_FAILURES,
                    default=int(
                        self.entry.options.get(
                            CONF_MAX_CONSECUTIVE_FAILURES,
                            DEFAULT_MAX_CONSECUTIVE_FAILURES,
                        )
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors={})

    # TODO: add zone-based location picker and coordinate edits here.
