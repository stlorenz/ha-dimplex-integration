"""DataUpdateCoordinator for Dimplex integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .modbus_client import DimplexModbusClient
from .modbus_registers import (
    SoftwareVersion,
    get_error_register,
    get_lock_message,
    get_lock_register,
    get_sensor_error_register,
    get_status_message,
    get_status_register,
)

_LOGGER = logging.getLogger(__name__)


class DimplexDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Dimplex data."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        software_version: SoftwareVersion = SoftwareVersion.L_M,
        name: str = "Dimplex",
    ) -> None:
        """Initialize.

        Args:
            hass: Home Assistant instance
            host: IP address or hostname of Dimplex device
            port: Modbus TCP port
            software_version: WPM software version (defaults to L_M)
            name: Device name

        """
        self.host = host
        self.port = port
        self.software_version = software_version
        self.device_name = name
        self.client = DimplexModbusClient(host, port)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Dimplex device.

        Returns:
            Dictionary containing all device data

        Raises:
            UpdateFailed: If communication with device fails

        """
        try:
            # Ensure connection
            if not self.client.is_connected:
                connected = await self.client.connect()
                if not connected:
                    raise UpdateFailed("Failed to connect to Dimplex device")

            # Get register addresses for current software version
            status_reg = get_status_register(self.software_version)
            lock_reg = get_lock_register(self.software_version)
            error_reg = get_error_register(self.software_version)

            # Read system status with timeout
            async with asyncio.timeout(10):
                system_status = await self.client.read_system_status(
                    status_reg, lock_reg, error_reg
                )

            if not system_status:
                raise UpdateFailed("No data received from device")

            # Process status codes into readable strings
            data = {
                "status_code": system_status.get("status_code", 0),
                "lock_code": system_status.get("lock_code", 0),
                "error_code": system_status.get("error_code", 0),
                "status": get_status_message(
                    system_status.get("status_code", 0), self.software_version
                ),
                "lock": get_lock_message(
                    system_status.get("lock_code", 0), self.software_version
                ),
                "connected": True,
                "name": self.device_name,
            }

            # Read sensor error if available (L/M software only)
            sensor_error_reg = get_sensor_error_register(self.software_version)
            if sensor_error_reg is not None:
                sensor_error = await self.client.read_holding_registers(
                    sensor_error_reg, count=1
                )
                if sensor_error:
                    data["sensor_error_code"] = sensor_error[0]

            _LOGGER.debug("Updated data from Dimplex device: %s", data)
            return data

        except asyncio.TimeoutError as err:
            raise UpdateFailed("Timeout communicating with device") from err
        except Exception as err:
            _LOGGER.error("Error updating data from Dimplex device: %s", err)
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and disconnect."""
        await self.client.disconnect()

