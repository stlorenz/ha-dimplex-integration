"""Modbus TCP client for Dimplex heat pump."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .modbus_registers import SoftwareVersion
from .modbus_registers_extended import (
    COIL_DATAPOINTS,
    INPUT_COIL_BLOCK,
    OPERATING_MODE_KEYS,
    OUTPUT_COIL_BLOCK,
    REGISTER_DATAPOINTS,
    RegisterDefinition,
    get_coil_address,
    get_register_definition,
    read_32bit_value,
    scale_value,
)

_LOGGER = logging.getLogger(__name__)

# Default Modbus TCP port
DEFAULT_PORT = 502

# COP smoothing parameters
# Minimum power thresholds (W) to avoid calculating COP during unstable transitions
MIN_POWER_IN_FOR_COP = 2000  # Minimum 2kW input power
MIN_POWER_OUT_FOR_COP = 3000  # Minimum 3kW output power
# Maximum realistic COP value (filters out unrealistic spikes)
MAX_REALISTIC_COP = 8.0
# Exponential moving average alpha (0.0-1.0, lower = more smoothing)
# 0.3 means new value has 30% weight, previous smoothed value has 70% weight
COP_SMOOTHING_ALPHA = 0.3

# Writes are retried once after a short pause (the WPM occasionally drops a
# request while it is busy updating its display).
WRITE_RETRIES = 2
WRITE_RETRY_DELAY = 0.5


class DimplexModbusClient:
    """Dimplex Modbus TCP client wrapper."""

    def __init__(self, host: str, port: int = DEFAULT_PORT, slave_id: int = 1) -> None:
        """Initialize the Modbus client.

        Args:
            host: IP address or hostname of the Dimplex device
            port: Modbus TCP port (default: 502)
            slave_id: Modbus unit/slave ID used as the default for all reads/writes
                (default: 1)

        """
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self._client: AsyncModbusTcpClient | None = None
        self._connected = False
        # pymodbus renamed the slave/unit parameter over time.
        # Cache which kw name works for this runtime ("device_id", "unit", "slave").
        self._unit_id_kw: str | None = None
        # COP smoothing state
        self._smoothed_cop: float | None = None

    async def _call_with_unit_id(
        self,
        method: Any,
        /,
        *args: Any,
        unit_id: int = 1,
        **kwargs: Any,
    ) -> Any:
        """Call a pymodbus method using the correct unit/slave/device id kw.

        - pymodbus 2.x: "unit"
        - older 3.x variants: "slave"
        - recent 3.x: "device_id"
        """
        if self._unit_id_kw is not None:
            return await method(*args, **kwargs, **{self._unit_id_kw: unit_id})

        for candidate in ("device_id", "unit", "slave"):
            try:
                result = await method(*args, **kwargs, **{candidate: unit_id})
            except TypeError as err:
                msg = str(err)
                if f"unexpected keyword argument '{candidate}'" in msg:
                    continue
                raise
            else:
                self._unit_id_kw = candidate
                return result

        raise TypeError("Unable to determine pymodbus unit/slave keyword")

    async def connect(self) -> bool:
        """Connect to the Modbus device.

        Returns:
            True if connection successful, False otherwise

        """
        # Disconnect existing connection if any
        if self._client is not None:
            with contextlib.suppress(Exception):
                self._client.close()
            self._client = None
            self._connected = False
            # Reset COP smoothing state on disconnect
            self._smoothed_cop = None

        try:
            self._client = AsyncModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=10,
            )
            await self._client.connect()
            self._connected = self._client.connected

            if self._connected:
                _LOGGER.info(
                    "Connected to Dimplex device at %s:%s", self.host, self.port
                )
            else:
                _LOGGER.error(
                    "Failed to connect to Dimplex device at %s:%s", self.host, self.port
                )

            return self._connected
        except OSError as err:
            _LOGGER.error("Network error connecting to Dimplex device: %s", err)
            self._connected = False
            if self._client is not None:
                with contextlib.suppress(Exception):
                    self._client.close()
                self._client = None
            return False
        except ModbusException as err:
            _LOGGER.error("Modbus error connecting to device: %s", err)
            self._connected = False
            if self._client is not None:
                with contextlib.suppress(Exception):
                    self._client.close()
                self._client = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from the Modbus device."""
        if self._client:
            self._client.close()
            self._connected = False
            # Reset COP smoothing state on disconnect
            self._smoothed_cop = None
            _LOGGER.info("Disconnected from Dimplex device")

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected and self._client is not None and self._client.connected

    async def read_holding_registers(
        self, address: int, count: int = 1, slave: int | None = None
    ) -> list[int] | None:
        """Read holding registers from the device.

        Args:
            address: Starting register address
            count: Number of registers to read
            slave: Modbus slave ID; falls back to the client's configured ID

        Returns:
            List of register values or None on error

        """
        if not self.is_connected or self._client is None:
            _LOGGER.warning("Cannot read registers: not connected")
            return None

        unit_id = slave if slave is not None else self.slave_id
        try:
            result = await self._call_with_unit_id(
                self._client.read_holding_registers,
                address=address,
                count=count,
                unit_id=unit_id,
            )

            if result.isError():
                _LOGGER.error(
                    "Error reading holding registers at %s: %s", address, result
                )
                return None

            return result.registers
        except ModbusException as err:
            _LOGGER.error("Modbus exception reading holding registers: %s", err)
            return None
        except OSError as err:
            _LOGGER.error("Network error reading holding registers: %s", err)
            self._connected = False
            return None

    async def read_input_registers(
        self, address: int, count: int = 1, slave: int | None = None
    ) -> list[int] | None:
        """Read input registers from the device.

        Args:
            address: Starting register address
            count: Number of registers to read
            slave: Modbus slave ID; falls back to the client's configured ID

        Returns:
            List of register values or None on error

        """
        if not self.is_connected or self._client is None:
            _LOGGER.warning("Cannot read registers: not connected")
            return None

        unit_id = slave if slave is not None else self.slave_id
        try:
            result = await self._call_with_unit_id(
                self._client.read_input_registers,
                address=address,
                count=count,
                unit_id=unit_id,
            )

            if result.isError():
                _LOGGER.error(
                    "Error reading input registers at %s: %s", address, result
                )
                return None

            return result.registers
        except ModbusException as err:
            _LOGGER.error("Modbus exception reading input registers: %s", err)
            return None
        except OSError as err:
            _LOGGER.error("Network error reading input registers: %s", err)
            self._connected = False
            return None

    async def read_coils(
        self, address: int, count: int = 1, slave: int | None = None
    ) -> list[bool] | None:
        """Read coils (digital inputs/outputs, FC01) from the device.

        Args:
            address: Starting coil address
            count: Number of coils to read
            slave: Modbus slave ID; falls back to the client's configured ID

        Returns:
            List of ``count`` booleans or None on error

        """
        if not self.is_connected or self._client is None:
            _LOGGER.warning("Cannot read coils: not connected")
            return None

        unit_id = slave if slave is not None else self.slave_id
        try:
            result = await self._call_with_unit_id(
                self._client.read_coils,
                address=address,
                count=count,
                unit_id=unit_id,
            )

            if result.isError():
                _LOGGER.error("Error reading coils at %s: %s", address, result)
                return None

            # pymodbus pads the bit list to a full byte; trim to what was asked.
            return [bool(bit) for bit in result.bits[:count]]
        except ModbusException as err:
            _LOGGER.error("Modbus exception reading coils: %s", err)
            return None
        except OSError as err:
            _LOGGER.error("Network error reading coils: %s", err)
            self._connected = False
            return None

    async def write_register(
        self, address: int, value: int, slave: int | None = None
    ) -> bool:
        """Write a single register to the device (with one retry).

        Args:
            address: Register address
            value: Value to write
            slave: Modbus slave ID; falls back to the client's configured ID

        Returns:
            True if write successful, False otherwise

        """
        unit_id = slave if slave is not None else self.slave_id

        for attempt in range(1, WRITE_RETRIES + 1):
            if not self.is_connected or self._client is None:
                if attempt == 1:
                    _LOGGER.warning("Cannot write register: not connected")
                    return False
                if not await self.connect():
                    return False
                assert self._client is not None

            try:
                result = await self._call_with_unit_id(
                    self._client.write_register,
                    address=address,
                    value=value,
                    unit_id=unit_id,
                )

                if result.isError():
                    _LOGGER.error("Error writing register at %s: %s", address, result)
                    return False

                _LOGGER.debug(
                    "Successfully wrote value %s to register %s", value, address
                )
                return True
            except ModbusException as err:
                _LOGGER.error("Modbus exception writing register: %s", err)
                return False
            except OSError as err:
                self._connected = False
                if attempt < WRITE_RETRIES:
                    _LOGGER.warning(
                        "Network error writing register %s (attempt %d/%d): %s - retrying",
                        address,
                        attempt,
                        WRITE_RETRIES,
                        err,
                    )
                    await asyncio.sleep(WRITE_RETRY_DELAY)
                    continue
                _LOGGER.error("Network error writing register: %s", err)
                return False

        return False

    async def test_connection(self) -> bool:
        """Test the connection by attempting to read a register.

        Returns:
            True if connection test successful, False otherwise

        """
        if not self.is_connected:
            if not await self.connect():
                return False

        # Try reading the status register (using L/M software address as default)
        result = await self.read_holding_registers(address=103, count=1)
        return result is not None

    async def read_system_status(
        self, status_reg: int, lock_reg: int, error_reg: int
    ) -> dict[str, Any]:
        """Read all system status registers.

        Args:
            status_reg: Status message register address
            lock_reg: Lock message register address
            error_reg: Error message register address

        Returns:
            Dictionary with status, lock, and error values

        """
        status_data = {}

        # Read status message
        result = await self.read_holding_registers(status_reg, count=1)
        if result:
            status_data["status_code"] = result[0]

        # Read lock message
        result = await self.read_holding_registers(lock_reg, count=1)
        if result:
            status_data["lock_code"] = result[0]

        # Read error message
        result = await self.read_holding_registers(error_reg, count=1)
        if result:
            status_data["error_code"] = result[0]

        return status_data

    async def _read_register_with_definition(
        self,
        register_def: RegisterDefinition,
        slave: int | None = None,
    ) -> float | None:
        """Read a register using its definition and return scaled value.

        Args:
            register_def: Register definition with address, scale, etc.
            slave: Modbus slave ID; falls back to the client's configured ID

        Returns:
            Scaled float value or None if read failed
        """
        if register_def.address is None:
            return None

        count = register_def.size
        # Pass unit id positionally to avoid keyword name churn ("slave"/"unit"/"device_id")
        # and to satisfy stricter type checkers.
        result = await self.read_holding_registers(register_def.address, count, slave)

        if result is None:
            return None

        # Custom decoder (used e.g. for 12-digit multi-word counters)
        if register_def.decoder is not None:
            decoded = register_def.decoder(result)
            if decoded is None:
                return None
            return float(decoded) * register_def.scale + register_def.offset

        # Default decoding: 16-bit or 32-bit.
        raw_value = read_32bit_value(result) if count == 2 else result[0]

        return scale_value(raw_value, register_def)

    async def _read_coil_block(
        self,
        software_version: SoftwareVersion,
        block: tuple[int, int],
        data: dict[str, Any],
    ) -> None:
        """Read one coil block and store every mapped coil in ``data``."""
        start, count = block
        wanted = {
            key: addr
            for key, coil_dict in COIL_DATAPOINTS.items()
            if (addr := get_coil_address(coil_dict, software_version)) is not None
            and start <= addr < start + count
        }
        if not wanted:
            return

        bits = await self.read_coils(start, count)
        if bits is None:
            return

        for key, addr in wanted.items():
            index = addr - start
            if index < len(bits):
                data[key] = bits[index]

    def _calculate_cop(self, data: dict[str, Any]) -> None:
        """Derive a smoothed COP from the current power values."""
        if (
            "current_power_consumption" not in data
            or "current_heating_power" not in data
        ):
            return

        power_in = data["current_power_consumption"]
        power_out = data["current_heating_power"]

        # Only calculate COP when both power values are above minimum thresholds
        # This avoids unrealistic spikes during mode transitions (e.g., when pump switches)
        if power_in >= MIN_POWER_IN_FOR_COP and power_out >= MIN_POWER_OUT_FOR_COP:
            raw_cop = power_out / power_in

            # Cap unrealistic values (e.g., from measurement artifacts during transitions)
            if raw_cop > MAX_REALISTIC_COP:
                _LOGGER.debug(
                    "Capping unrealistic COP value %.2f (power_in=%.0fW, power_out=%.0fW)",
                    raw_cop,
                    power_in,
                    power_out,
                )
                raw_cop = MAX_REALISTIC_COP

            # Apply exponential moving average smoothing
            if self._smoothed_cop is not None:
                smoothed_cop = (
                    COP_SMOOTHING_ALPHA * raw_cop
                    + (1 - COP_SMOOTHING_ALPHA) * self._smoothed_cop
                )
            else:
                smoothed_cop = raw_cop

            self._smoothed_cop = smoothed_cop
            data["cop"] = round(smoothed_cop, 2)
        elif power_in > 0:
            # Power values below threshold - don't calculate new COP
            # but keep previous smoothed value if available
            if self._smoothed_cop is not None:
                data["cop"] = round(self._smoothed_cop, 2)

    async def read_operating_data(
        self, software_version: SoftwareVersion
    ) -> dict[str, Any]:
        """Read all operating data (temperatures, pressures, power, etc.).

        Every datapoint in ``REGISTER_DATAPOINTS`` that has an address for the
        given software version is read individually; coils are read in two
        block requests. Derived values (COP, totals, operating mode name) are
        added at the end.

        Args:
            software_version: WPM software version to determine register addresses

        Returns:
            Dictionary with all operating data values
        """
        data: dict[str, Any] = {}

        for key, register_dict in REGISTER_DATAPOINTS.items():
            reg_def = get_register_definition(register_dict, software_version)
            if reg_def is None:
                continue
            value = await self._read_register_with_definition(reg_def)
            if value is not None:
                data[key] = value

        await self._read_coil_block(software_version, INPUT_COIL_BLOCK, data)
        await self._read_coil_block(software_version, OUTPUT_COIL_BLOCK, data)

        # --- Derived values ---------------------------------------------
        self._calculate_cop(data)

        runtimes = [
            data[k]
            for k in ("compressor_1_runtime", "compressor_2_runtime")
            if k in data
        ]
        if runtimes:
            data["compressor_runtime_total"] = sum(runtimes)

        heat = [
            data[k]
            for k in ("heating_energy", "hot_water_energy", "pool_energy")
            if k in data
        ]
        if heat:
            data["total_heat_generated"] = sum(heat)

        mode_code = data.get("operating_mode_code")
        if mode_code is not None:
            data["operating_mode"] = OPERATING_MODE_KEYS.get(
                int(mode_code), f"unknown_{int(mode_code)}"
            )

        _LOGGER.debug("Read operating data: %s", data)
        return data
