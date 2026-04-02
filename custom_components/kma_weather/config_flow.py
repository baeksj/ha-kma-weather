from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .area_lookup import nearest_area_codes
from .const import (
    CONF_API_KEY,
    CONF_AREA_NO,
    CONF_ENV_KIND,
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


API_GROUP_DESCRIPTIONS = {
    "living_weather": (
        "생활기상지수 조회서비스(3.0) → UV, 대기확산지수 센서 추가"
    ),
    "air_quality": (
        "에어코리아 대기오염정보 조회서비스 → PM10, PM2.5, O3, NO2, CO, SO2, 통합대기환경지수, 측정소 센서 추가"
    ),
}

API_GROUP_DETAILS = {
    "living_weather": (
        "추가 API: 기상청_생활기상지수 조회서비스(3.0)\n"
        "추가되는 센서: KMA UV Index, KMA Air Diffusion Index\n"
        "API 키는 기본 설치 시 입력한 공통 키를 재사용합니다."
    ),
    "air_quality": (
        "추가 API: 에어코리아 대기오염정보 조회서비스\n"
        "추가되는 센서: AirKorea Station, AirKorea PM10, AirKorea PM2.5, AirKorea O3, AirKorea NO2, "
        "AirKorea CO, AirKorea SO2, AirKorea Integrated Air Quality Index\n"
        "측정소는 zone 위도/경도 기준 최근접 대기측정소를 자동 선택합니다.\n"
        "API 키는 기본 설치 시 입력한 공통 키를 재사용합니다."
    ),
}


class KmaWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._pending_data: dict[str, Any] = {}
        self._area_candidates: list[dict[str, Any]] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_LOCATION_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_ZONE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="zone")
                ),
            }
        )

        if user_input is not None:
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

                    candidates = nearest_area_codes(float(latitude), float(longitude), limit=3)
                    if not candidates:
                        errors["base"] = "area_code_not_found"
                    else:
                        self._pending_data = data
                        self._area_candidates = candidates
                        return await self.async_step_area_choice()

                    if errors:
                        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_area_choice(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        options = {}
        for item in self._area_candidates:
            key = item["area_no"]
            label = (
                f"{item['level1']} {item['level2']} {item['level3']} "
                f"(code={item['area_no']}, nx={item['nx']}, ny={item['ny']}, "
                f"{item['geo_distance_km']:.3f}km)"
            )
            options[key] = label

        if user_input is not None:
            selected = user_input.get(CONF_AREA_NO)
            chosen = next((item for item in self._area_candidates if item["area_no"] == selected), None)
            if chosen is None:
                errors["base"] = "invalid_area_choice"
            else:
                data = dict(self._pending_data)
                data[CONF_AREA_NO] = chosen["area_no"]
                data["region_level_1"] = chosen["level1"]
                data["region_level_2"] = chosen["level2"]
                data["region_level_3"] = chosen["level3"]
                await self.async_set_unique_id(f"{data[CONF_NX]}_{data[CONF_NY]}_{data[CONF_AREA_NO]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data.get(CONF_LOCATION_NAME) or DEFAULT_NAME,
                    data=data,
                    options={
                        CONF_MAX_CONSECUTIVE_FAILURES: DEFAULT_MAX_CONSECUTIVE_FAILURES,
                    },
                )

        schema = vol.Schema({
            vol.Required(CONF_AREA_NO): vol.In(options)
        })
        return self.async_show_form(step_id="area_choice", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "KmaWeatherOptionsFlow":
        return KmaWeatherOptionsFlow(config_entry)


class KmaWeatherOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry
        self._pending_kind: str | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            if user_input.get(CONF_ENV_KIND):
                self._pending_kind = user_input[CONF_ENV_KIND]
                return await self.async_step_add_environment()

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

        existing = self.entry.options.get("enabled_api_groups", [])
        available = {k: v for k, v in API_GROUP_DESCRIPTIONS.items() if k not in existing}

        schema_dict = {
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
        if available:
            schema_dict[vol.Optional(CONF_ENV_KIND)] = vol.In(available)

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict), errors={})

    async def async_step_add_environment(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        kind = self._pending_kind
        if kind is None:
            return await self.async_step_init()

        existing = list(self.entry.options.get("enabled_api_groups", []))
        if kind in existing:
            return await self.async_step_init()

        if user_input is not None:
            existing.append(kind)
            return self.async_create_entry(
                title="",
                data={
                    **self.entry.options,
                    "enabled_api_groups": existing,
                },
            )

        schema = vol.Schema({})
        return self.async_show_form(
            step_id="add_environment",
            data_schema=schema,
            errors={},
            description_placeholders={"details": API_GROUP_DETAILS.get(kind, kind)},
        )
