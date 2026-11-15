"""DataUpdateCoordinator for Dimplex integration."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_BACKOFF_INTERVAL,
    MODEL_NAMES,
    HeatPumpModel,
)
from .modbus_client import DimplexModbusClient
from .modbus_registers import (
    SoftwareVersion,
    get_error_message,
    get_error_register,
    get_lock_message,
    get_lock_register,
    get_sensor_error_register,
    get_status_message,
    get_status_register,
)
from .modbus_registers_extended import controller_software_family

_LOGGER = logging.getLogger(__name__)

# How long a just-written value is shown instead of the device's read-back.
# The NWPM Touch hands settings writes (5000 range) to the WPM with a delay;
# reading the register right after the write still returns the old value,
# sometimes for more than a minute.
WRITE_HOLD_SECONDS = 180


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
        slave_id: int = 1,
        config_entry: ConfigEntry | None = None,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
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
            slave_id: Modbus unit/slave ID (defaults to 1)
            config_entry: Owning config entry (required by HA >= 2025.11 for
                DataUpdateCoordinator; implicit detection is deprecated)
            scan_interval: Polling interval in seconds (10..300)

        """
        self.host = host
        self.port = port
        self.software_version = software_version
        self.device_name = name
        self.model = model
        self.model_name = MODEL_NAMES.get(model, model)
        self.capabilities = capabilities or {}
        self.slave_id = slave_id
        self.client = DimplexModbusClient(host, port, slave_id=slave_id)
        self._write_enabled = False  # Default: read-only mode
        self._base_interval = timedelta(seconds=scan_interval)
        self._consecutive_failures = 0
        # data key -> (written value, monotonic deadline)
        self._pending_writes: dict[str, tuple[Any, float]] = {}
        # WPM software version from registers 65..67 ("M3.16"), read once
        self.controller_software: str | None = None
        self._controller_software_checked = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._base_interval,
            config_entry=config_entry,
        )
        _LOGGER.info(
            "Initialized Dimplex coordinator for %s at %s:%s with %d second update interval",
            name,
            host,
            port,
            scan_interval,
        )

    @property
    def cooling_enabled(self) -> bool:
        """Return whether cooling is enabled for this installation."""
        return self.capabilities.get("cooling_enabled", False)

    @property
    def passive_cooling_enabled(self) -> bool:
        """Return whether passive cooling is available (brine/water source)."""
        return bool(self.capabilities.get("passive_cooling", False))

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

    # ------------------------------------------------------------ version
    async def _read_controller_software(self) -> None:
        """Read registers 65..67 once and warn if they contradict the setup."""
        try:
            version = await self.client.read_controller_software()
        except Exception as err:  # noqa: BLE001 - never fail a poll for this
            _LOGGER.debug("Reading the WPM software version failed: %s", err)
            return
        if version is None:
            return
        self.controller_software = version
        if self._controller_software_checked:
            return
        self._controller_software_checked = True
        family = controller_software_family(version)
        if family is not None and family != self.software_version:
            _LOGGER.warning(
                "The WPM reports software %s, but the integration is configured "
                "for the %s register map. Check the software version in the "
                "integration options.",
                version,
                self.software_version.name,
            )
        else:
            _LOGGER.info("WPM software version: %s", version)

    # ------------------------------------------------------------ writes
    @callback
    def hold_written_value(self, key: str, value: Any) -> None:
        """Show a just-written value until the device confirms it.

        The WPM applies a write with a delay. Without this, the refresh
        right after the write read the old value back and the entity
        snapped back in the UI until a later poll picked up the new value.
        The written value is kept for WRITE_HOLD_SECONDS or until the
        device reports it, whichever comes first.
        """
        self._pending_writes[key] = (value, time.monotonic() + WRITE_HOLD_SECONDS)
        if self.data is not None:
            self.data[key] = value

    def _apply_pending_writes(self, data: dict[str, Any]) -> None:
        """Overlay unconfirmed writes on freshly polled data."""
        now = time.monotonic()
        for key, (value, deadline) in list(self._pending_writes.items()):
            if key in data and _same_value(data[key], value):
                del self._pending_writes[key]
            elif now >= deadline:
                del self._pending_writes[key]
                _LOGGER.warning(
                    "Device still reports %s=%s %ss after %s was written",
                    key,
                    data.get(key),
                    WRITE_HOLD_SECONDS,
                    value,
                )
            else:
                data[key] = value

    # ------------------------------------------------------------ backoff
    def _register_success(self) -> None:
        """Reset the polling interval after a successful update."""
        if self._consecutive_failures:
            _LOGGER.info(
                "Dimplex device reachable again, polling every %ds",
                self._base_interval.total_seconds(),
            )
        self._consecutive_failures = 0
        self.update_interval = self._base_interval

    def _register_failure(self) -> None:
        """Exponentially back off (up to MAX_BACKOFF_INTERVAL) on repeated failures."""
        self._consecutive_failures += 1
        # 1st failure: 2x base, 2nd: 4x, ... capped at MAX_BACKOFF_INTERVAL
        seconds = min(
            self._base_interval.total_seconds() * (2**self._consecutive_failures),
            MAX_BACKOFF_INTERVAL,
        )
        self.update_interval = timedelta(seconds=seconds)
        _LOGGER.debug(
            "Dimplex update failed %d time(s) in a row, next attempt in %ds",
            self._consecutive_failures,
            seconds,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Dimplex device.

        Returns:
            Dictionary containing all device data

        Raises:
            UpdateFailed: If communication with device fails

        """
        try:
            data = await self._fetch()
        except UpdateFailed:
            self._register_failure()
            raise
        self._register_success()
        self._apply_pending_writes(data)
        return data

    async def _fetch(self) -> dict[str, Any]:
        """Do one complete poll of the device."""
        _LOGGER.debug("Starting data update from Dimplex device")
        try:
            # Ensure connection
            if not self.client.is_connected:
                _LOGGER.info(
                    "Reconnecting to Dimplex device at %s:%s", self.host, self.port
                )
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
                _LOGGER.warning(
                    "Incomplete system status data received: %s", system_status
                )
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
                "error": get_error_message(
                    system_status.get("error_code", 0), self.software_version
                ),
                "connected": True,
                "name": self.device_name,
            }

            if self.controller_software is None:
                await self._read_controller_software()
            if self.controller_software is not None:
                data["controller_software"] = self.controller_software

            # Read sensor error if available (L/M software only)
            sensor_error_reg = get_sensor_error_register(self.software_version)
            if sensor_error_reg is not None:
                sensor_error = await self.client.read_holding_registers(
                    sensor_error_reg, count=1
                )
                if sensor_error:
                    data["sensor_error_code"] = sensor_error[0]

            # Read operating data (temperatures, pressures, power, energy, runtime)
            # Continue even if some reads fail - partial data is better than no data
            try:
                async with asyncio.timeout(30):
                    operating_data = await self.client.read_operating_data(
                        self.software_version
                    )
                    if operating_data:
                        data.update(operating_data)
                    else:
                        _LOGGER.warning(
                            "No operating data received, but continuing with system status data"
                        )
                    # HC2 settings live behind the selector register 5082.
                    # Switching the selector is a write, so it only happens
                    # while Write Enable is on; otherwise the block is read
                    # only if it already refers to HC2.
                    if self.second_hc_enabled:
                        data.update(
                            await self.client.read_hc_settings(
                                self.software_version,
                                allow_select=self._write_enabled,
                            )
                        )
            except TimeoutError:
                _LOGGER.warning(
                    "Timeout reading operating data, but continuing with system status data"
                )
            except Exception as err:
                _LOGGER.warning(
                    "Error reading operating data: %s, but continuing with system status data",
                    err,
                )

            _LOGGER.debug(
                "Successfully updated data from Dimplex device. "
                "Keys: %s, Data points: %d",
                list(data.keys()),
                len(data),
            )
            return data

        except UpdateFailed:
            # Already a well-formed coordinator error (e.g. no valid status data);
            # don't wrap it in a generic "Unexpected error".
            raise
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
        """Disconnect from the device and stop the coordinator."""
        await self.client.disconnect()
        await super().async_shutdown()


def _same_value(reported: Any, written: Any) -> bool:
    """Compare a polled value with a written one (floats with tolerance)."""
    if isinstance(reported, (int, float)) and isinstance(written, (int, float)):
        return abs(float(reported) - float(written)) < 1e-6
    return reported == written
