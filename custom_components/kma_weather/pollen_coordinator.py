from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DEFAULT_MAX_CONSECUTIVE_FAILURES, DEFAULT_SCAN_INTERVAL
from .coordinator import _FailureTolerantCoordinator
from .pollen_api import KmaPollenApi, KmaPollenApiError

_LOGGER = logging.getLogger(__name__)


class KmaPollenCoordinator(_FailureTolerantCoordinator):
    def __init__(
        self,
        hass,
        api: KmaPollenApi,
        kind: str,
        *,
        config_entry=None,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"KMA Pollen {kind}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=config_entry,
            max_consecutive_failures=max_consecutive_failures,
        )
        self.api = api
        self.kind = kind

    async def _fetch(self) -> dict[str, Any]:
        try:
            if self.kind == "pine":
                return await self.api.async_fetch_pine()
            if self.kind == "oak":
                return await self.api.async_fetch_oak()
            if self.kind == "weed":
                return await self.api.async_fetch_weed()
            raise UpdateFailed(f"Unsupported pollen kind: {self.kind}")
        except KmaPollenApiError as err:
            raise UpdateFailed(str(err)) from err
