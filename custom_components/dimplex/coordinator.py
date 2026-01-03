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
        _LOGGER.info(
            "Initialized Dimplex coordinator for %s at %s:%s with %d second update interval",
            name,
            host,
            port,
            30,
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
        _LOGGER.debug("Starting data update from Dimplex device")
        try:
            # Ensure connection
            if not self.client.is_connected:
                _LOGGER.info("Reconnecting to Dimplex device at %s:%s", self.host, self.port)
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

            # Check if we got at least some data (at least status_code should be present)
            if not system_status or "status_code" not in system_status:
                _LOGGER.warning("Incomplete system status data received: %s", system_status)
                raise UpdateFailed("No valid status data received from device")

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
            # Continue even if some reads fail - partial data is better than no data
            try:
                async with asyncio.timeout(30):
                    operating_data = await self.client.read_operating_data(
                        self.software_version
                    )
                    # Merge operating data into main data dictionary
                    if operating_data:
                        data.update(operating_data)
                    else:
                        _LOGGER.warning("No operating data received, but continuing with system status data")
            except TimeoutError:
                _LOGGER.warning("Timeout reading operating data, but continuing with system status data")
                # Continue with system status data only
            except Exception as err:
                _LOGGER.warning("Error reading operating data: %s, but continuing with system status data", err)
                # Continue with system status data only

            _LOGGER.debug(
                "Successfully updated data from Dimplex device. "
                "Keys: %s, Data points: %d",
                list(data.keys()),
                len(data)
            )
            return data

        except TimeoutError as err:
            _LOGGER.warning("Timeout communicating with Dimplex device: %s", err)
            # Mark connection as lost on timeout
            if self.client.is_connected:
                await self.client.disconnect()
            raise UpdateFailed("Timeout communicating with device") from err
        except OSError as err:
            _LOGGER.warning("Connection error with Dimplex device: %s", err)
            # Mark connection as lost on network error
            if self.client.is_connected:
                await self.client.disconnect()
            raise UpdateFailed(f"Connection error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error updating data from Dimplex device")
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and disconnect."""
        await self.client.disconnect()
