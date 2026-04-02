from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL
from .midterm_api import KmaMidtermApi, KmaMidtermApiError

_LOGGER = logging.getLogger(__name__)


class KmaMidtermCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, api: KmaMidtermApi) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="KMA Midterm Forecast",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_fetch_all()
        except KmaMidtermApiError as err:
            raise UpdateFailed(str(err)) from err
