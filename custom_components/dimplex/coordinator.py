"""DataUpdateCoordinator for Dimplex integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, MODEL_NAMES, HeatPumpModel
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
        model: str = HeatPumpModel.GENERIC,
        capabilities: dict[str, Any] | None = None,
    ) -> None:
        """Initialize.

        Args:
            hass: Home Assistant instance
            host: IP address or hostname of Dimplex device
            port: Modbus TCP port
            software_version: WPM software version (defaults to L_M)
            name: Device name
            model: Heat pump model identifier
            capabilities: Dictionary of device capabilities and enabled features

        """
        self.host = host
        self.port = port
        self.software_version = software_version
        self.device_name = name
        self.model = model
        self.model_name = MODEL_NAMES.get(model, model)
        self.capabilities = capabilities or {}
        self.client = DimplexModbusClient(host, port)
        self._write_enabled = False  # Default: read-only mode

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    @property
    def cooling_enabled(self) -> bool:
        """Return whether cooling is enabled for this installation."""
        return self.capabilities.get("cooling_enabled", False)

    @property
    def dhw_enabled(self) -> bool:
        """Return whether DHW is enabled for this installation."""
        return self.capabilities.get("dhw_enabled", True)

    @property
    def pool_enabled(self) -> bool:
        """Return whether pool heating is enabled for this installation."""
        return self.capabilities.get("pool_enabled", False)

    @property
    def second_hc_enabled(self) -> bool:
        """Return whether second heating circuit is enabled."""
        return self.capabilities.get("second_hc_enabled", False)

    @property
    def has_defrost(self) -> bool:
        """Return whether this heat pump has defrost capability (air source)."""
        return self.capabilities.get("defrost", True)

    @property
    def heat_source(self) -> str:
        """Return the heat source type (air, brine, water)."""
        return self.capabilities.get("heat_source", "unknown")

    @property
    def write_enabled(self) -> bool:
        """Return whether write operations are enabled."""
        return self._write_enabled

    @callback
    def set_write_enabled(self, enabled: bool) -> None:
        """Set write enabled state.

        Args:
            enabled: True to enable write operations, False for read-only mode.

        """
        self._write_enabled = enabled
        _LOGGER.info(
            "Dimplex write mode %s",
            "enabled" if enabled else "disabled (read-only)",
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
            data: dict[str, Any] = {
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

            # Read operating data (temperatures, pressures, power, energy, runtime)
            # This provides HA-compliant sensor data for InfluxDB/Grafana integration
            async with asyncio.timeout(30):
                operating_data = await self.client.read_operating_data(
                    self.software_version
                )
            
            # Merge operating data into main data dictionary
            data.update(operating_data)

            _LOGGER.debug("Updated data from Dimplex device: %s", data)
            return data

        except TimeoutError as err:
            raise UpdateFailed("Timeout communicating with device") from err
        except OSError as err:
            _LOGGER.error("Connection error with Dimplex device: %s", err)
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error updating data from Dimplex device")
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and disconnect."""
        await self.client.disconnect()
