from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL
from .living_api import KmaLivingApiError, KmaLivingWeatherApi


_LOGGER = logging.getLogger(__name__)


class KmaLivingCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, api: KmaLivingWeatherApi, kind: str) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"KMA Living {kind}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.kind = kind

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if self.kind == "uv":
                return await self.api.async_fetch_uv()
            if self.kind == "air_diffusion":
                return await self.api.async_fetch_air_diffusion()
            raise UpdateFailed(f"Unsupported living kind: {self.kind}")
        except KmaLivingApiError as err:
            raise UpdateFailed(str(err)) from err
