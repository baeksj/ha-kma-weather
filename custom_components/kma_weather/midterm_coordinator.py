from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DEFAULT_MAX_CONSECUTIVE_FAILURES, DEFAULT_SCAN_INTERVAL
from .coordinator import _FailureTolerantCoordinator
from .midterm_api import KmaMidtermApi, KmaMidtermApiError

_LOGGER = logging.getLogger(__name__)


class KmaMidtermCoordinator(_FailureTolerantCoordinator):
    def __init__(
        self,
        hass,
        api: KmaMidtermApi,
        *,
        config_entry=None,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="KMA Midterm Forecast",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=config_entry,
            max_consecutive_failures=max_consecutive_failures,
        )
        self.api = api

    async def _fetch(self) -> dict[str, Any]:
        try:
            return await self.api.async_fetch_all()
        except KmaMidtermApiError as err:
            raise UpdateFailed(str(err)) from err
