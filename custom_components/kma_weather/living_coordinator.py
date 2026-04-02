from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DEFAULT_MAX_CONSECUTIVE_FAILURES, DEFAULT_SCAN_INTERVAL
from .coordinator import _FailureTolerantCoordinator
from .living_api import KmaLivingApiError, KmaLivingWeatherApi


_LOGGER = logging.getLogger(__name__)


class KmaLivingCoordinator(_FailureTolerantCoordinator):
    def __init__(
        self,
        hass,
        api: KmaLivingWeatherApi,
        kind: str,
        *,
        config_entry=None,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"KMA Living {kind}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=config_entry,
            max_consecutive_failures=max_consecutive_failures,
        )
        self.api = api
        self.kind = kind

    async def _fetch(self) -> dict[str, Any]:
        try:
            if self.kind == "uv":
                return await self.api.async_fetch_uv()
            if self.kind == "air_diffusion":
                return await self.api.async_fetch_air_diffusion()
            raise UpdateFailed(f"Unsupported living kind: {self.kind}")
        except KmaLivingApiError as err:
            raise UpdateFailed(str(err)) from err
