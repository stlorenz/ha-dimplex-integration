"""DataUpdateCoordinator for Dimplex integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DimplexDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Dimplex data."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize."""
        self.host = host
        self.port = port
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Dimplex device.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # TODO: Implement actual data fetching from your device
            # Example:
            # async with async_timeout.timeout(10):
            #     data = await self._client.fetch_data()
            # return data
            return {}
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err


