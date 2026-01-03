"""Modbus TCP client for Dimplex heat pump."""
from __future__ import annotations

import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .modbus_registers_extended import (
    EnergyRegisters,
    OperatingDataRegisters,
    RegisterDefinition,
    RuntimeRegisters,
    get_register_definition,
    read_32bit_value,
    scale_value,
)
from .modbus_registers import SoftwareVersion

_LOGGER = logging.getLogger(__name__)

# Default Modbus TCP port
DEFAULT_PORT = 502


class DimplexModbusClient:
    """Dimplex Modbus TCP client wrapper."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        """Initialize the Modbus client.

        Args:
            host: IP address or hostname of the Dimplex device
            port: Modbus TCP port (default: 502)

        """
        self.host = host
        self.port = port
        self._client: AsyncModbusTcpClient | None = None
        self._connected = False
        # pymodbus renamed the slave/unit parameter over time.
        # Cache which kw name works for this runtime ("device_id", "unit", "slave").
        self._unit_id_kw: str | None = None

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
        try:
            self._client = AsyncModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=10,
            )
            await self._client.connect()
            self._connected = self._client.connected

            if self._connected:
                _LOGGER.info("Connected to Dimplex device at %s:%s", self.host, self.port)
            else:
                _LOGGER.error("Failed to connect to Dimplex device at %s:%s", self.host, self.port)

            return self._connected
        except OSError as err:
            _LOGGER.error("Network error connecting to Dimplex device: %s", err)
            self._connected = False
            return False
        except ModbusException as err:
            _LOGGER.error("Modbus error connecting to device: %s", err)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the Modbus device."""
        if self._client:
            self._client.close()
            self._connected = False
            _LOGGER.info("Disconnected from Dimplex device")

    @property
    def is_connected(self) -> bool:
        """Return connection status."""
        return self._connected and self._client is not None and self._client.connected

    async def read_holding_registers(
        self, address: int, count: int = 1, slave: int = 1
    ) -> list[int] | None:
        """Read holding registers from the device.

        Args:
            address: Starting register address
            count: Number of registers to read
            slave: Modbus slave ID (default: 1)

        Returns:
            List of register values or None on error

        """
        if not self.is_connected or self._client is None:
            _LOGGER.warning("Cannot read registers: not connected")
            return None

        try:
            result = await self._call_with_unit_id(
                self._client.read_holding_registers,
                address=address,
                count=count,
                unit_id=slave,
            )

            if result.isError():
                _LOGGER.error("Error reading holding registers at %s: %s", address, result)
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
        self, address: int, count: int = 1, slave: int = 1
    ) -> list[int] | None:
        """Read input registers from the device.

        Args:
            address: Starting register address
            count: Number of registers to read
            slave: Modbus slave ID (default: 1)

        Returns:
            List of register values or None on error

        """
        if not self.is_connected or self._client is None:
            _LOGGER.warning("Cannot read registers: not connected")
            return None

        try:
            result = await self._call_with_unit_id(
                self._client.read_input_registers,
                address=address,
                count=count,
                unit_id=slave,
            )

            if result.isError():
                _LOGGER.error("Error reading input registers at %s: %s", address, result)
                return None

            return result.registers
        except ModbusException as err:
            _LOGGER.error("Modbus exception reading input registers: %s", err)
            return None
        except OSError as err:
            _LOGGER.error("Network error reading input registers: %s", err)
            self._connected = False
            return None

    async def write_register(
        self, address: int, value: int, slave: int = 1
    ) -> bool:
        """Write a single register to the device.

        Args:
            address: Register address
            value: Value to write
            slave: Modbus slave ID (default: 1)

        Returns:
            True if write successful, False otherwise

        """
        if not self.is_connected or self._client is None:
            _LOGGER.warning("Cannot write register: not connected")
            return False

        try:
            result = await self._call_with_unit_id(
                self._client.write_register,
                address=address,
                value=value,
                unit_id=slave,
            )

            if result.isError():
                _LOGGER.error("Error writing register at %s: %s", address, result)
                return False

            _LOGGER.debug("Successfully wrote value %s to register %s", value, address)
            return True
        except ModbusException as err:
            _LOGGER.error("Modbus exception writing register: %s", err)
            return False
        except OSError as err:
            _LOGGER.error("Network error writing register: %s", err)
            self._connected = False
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

    async def read_system_status(self, status_reg: int, lock_reg: int, error_reg: int) -> dict[str, Any]:
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
        slave: int = 1,
    ) -> float | None:
        """Read a register using its definition and return scaled value.
        
        Args:
            register_def: Register definition with address, scale, etc.
            slave: Modbus slave ID
            
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
            
        # Combine registers for 32-bit values
        if count == 2:
            raw_value = read_32bit_value(result)
        else:
            raw_value = result[0]
            
        return scale_value(raw_value, register_def)

    async def read_operating_data(
        self, software_version: SoftwareVersion
    ) -> dict[str, Any]:
        """Read all operating data (temperatures, pressures, power, etc.).
        
        Args:
            software_version: WPM software version to determine register addresses
            
        Returns:
            Dictionary with all operating data values
        """
        data: dict[str, Any] = {}
        
        # Read temperature values
        temp_registers = [
            ("flow_temperature", OperatingDataRegisters.FLOW_TEMPERATURE),
            ("return_temperature", OperatingDataRegisters.RETURN_TEMPERATURE),
            ("outside_temperature", OperatingDataRegisters.OUTSIDE_TEMPERATURE),
            ("hot_water_temperature", OperatingDataRegisters.HOT_WATER_TEMPERATURE),
            ("heat_source_inlet_temperature", OperatingDataRegisters.HEAT_SOURCE_INLET_TEMP),
            ("heat_source_outlet_temperature", OperatingDataRegisters.HEAT_SOURCE_OUTLET_TEMP),
            ("room_temperature", OperatingDataRegisters.ROOM_TEMPERATURE),
            ("flow_setpoint", OperatingDataRegisters.FLOW_SETPOINT),
            ("hot_water_setpoint", OperatingDataRegisters.HOT_WATER_SETPOINT),
            ("evaporator_temperature", OperatingDataRegisters.EVAPORATOR_TEMPERATURE),
            ("condenser_temperature", OperatingDataRegisters.CONDENSER_TEMPERATURE),
            ("suction_gas_temperature", OperatingDataRegisters.SUCTION_GAS_TEMPERATURE),
            ("discharge_gas_temperature", OperatingDataRegisters.DISCHARGE_GAS_TEMPERATURE),
        ]
        
        for key, register_dict in temp_registers:
            reg_def = get_register_definition(register_dict, software_version)
            if reg_def:
                value = await self._read_register_with_definition(reg_def)
                if value is not None:
                    data[key] = value
        
        # Read pressure values
        pressure_registers = [
            ("high_pressure", OperatingDataRegisters.HIGH_PRESSURE),
            ("low_pressure", OperatingDataRegisters.LOW_PRESSURE),
            ("brine_pressure", OperatingDataRegisters.BRINE_PRESSURE),
            ("water_pressure", OperatingDataRegisters.WATER_PRESSURE),
        ]
        
        for key, register_dict in pressure_registers:
            reg_def = get_register_definition(register_dict, software_version)
            if reg_def:
                value = await self._read_register_with_definition(reg_def)
                if value is not None:
                    data[key] = value
        
        # Read power and energy values
        energy_registers = [
            ("current_power_consumption", EnergyRegisters.CURRENT_POWER_CONSUMPTION),
            ("current_heating_power", EnergyRegisters.CURRENT_HEATING_POWER),
            ("total_energy_consumed", EnergyRegisters.TOTAL_ENERGY_CONSUMED),
            ("total_heat_generated", EnergyRegisters.TOTAL_HEAT_GENERATED),
            ("heating_energy", EnergyRegisters.HEATING_ENERGY),
            ("hot_water_energy", EnergyRegisters.HOT_WATER_ENERGY),
            ("cooling_energy", EnergyRegisters.COOLING_ENERGY),
        ]
        
        for key, register_dict in energy_registers:
            reg_def = get_register_definition(register_dict, software_version)
            if reg_def:
                value = await self._read_register_with_definition(reg_def)
                if value is not None:
                    data[key] = value
        
        # Read runtime and counter values
        runtime_registers = [
            ("compressor_runtime_total", RuntimeRegisters.COMPRESSOR_RUNTIME_TOTAL),
            ("compressor_starts", RuntimeRegisters.COMPRESSOR_STARTS),
            ("heating_runtime", RuntimeRegisters.HEATING_RUNTIME),
            ("hot_water_runtime", RuntimeRegisters.HOT_WATER_RUNTIME),
            ("cooling_runtime", RuntimeRegisters.COOLING_RUNTIME),
            ("auxiliary_heater_runtime", RuntimeRegisters.AUXILIARY_HEATER_RUNTIME),
            ("defrost_cycles", RuntimeRegisters.DEFROST_CYCLES),
        ]
        
        for key, register_dict in runtime_registers:
            reg_def = get_register_definition(register_dict, software_version)
            if reg_def:
                value = await self._read_register_with_definition(reg_def)
                if value is not None:
                    data[key] = value
        
        # Calculate COP if we have both power values
        if "current_power_consumption" in data and "current_heating_power" in data:
            power_in = data["current_power_consumption"]
            power_out = data["current_heating_power"]
            if power_in > 0:
                data["cop"] = round(power_out / power_in, 2)
        
        _LOGGER.debug("Read operating data: %s", data)
        return data