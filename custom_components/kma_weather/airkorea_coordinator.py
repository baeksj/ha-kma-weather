from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .airkorea_api import AirKoreaApi, AirKoreaApiError
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AirKoreaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, api: AirKoreaApi) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="AirKorea Air Quality",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_fetch_realtime_air_quality()
        except AirKoreaApiError as err:
            raise UpdateFailed(str(err)) from err
