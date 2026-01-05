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

# COP smoothing parameters
# Minimum power thresholds (W) to avoid calculating COP during unstable transitions
MIN_POWER_IN_FOR_COP = 2000  # Minimum 2kW input power
MIN_POWER_OUT_FOR_COP = 3000  # Minimum 3kW output power
# Maximum realistic COP value (filters out unrealistic spikes)
MAX_REALISTIC_COP = 8.0
# Exponential moving average alpha (0.0-1.0, lower = more smoothing)
# 0.3 means new value has 30% weight, previous smoothed value has 70% weight
COP_SMOOTHING_ALPHA = 0.3


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
            try:
                self._client.close()
            except Exception:
                pass
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
                _LOGGER.info("Connected to Dimplex device at %s:%s", self.host, self.port)
            else:
                _LOGGER.error("Failed to connect to Dimplex device at %s:%s", self.host, self.port)

            return self._connected
        except OSError as err:
            _LOGGER.error("Network error connecting to Dimplex device: %s", err)
            self._connected = False
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            return False
        except ModbusException as err:
            _LOGGER.error("Modbus error connecting to device: %s", err)
            self._connected = False
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
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
            
        # Custom decoder (used e.g. for BCD-packed multi-word counters)
        if register_def.decoder is not None:
            decoded = register_def.decoder(result)
            if decoded is None:
                return None
            return float(decoded) * register_def.scale

        # Default decoding: 16-bit or 32-bit.
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
            ("return_setpoint", OperatingDataRegisters.RETURN_SETPOINT),
            ("hot_water_setpoint", OperatingDataRegisters.HOT_WATER_SETPOINT),
            ("hc2_setpoint", OperatingDataRegisters.HC2_SETPOINT),
            ("hc3_setpoint", OperatingDataRegisters.HC3_SETPOINT),
            ("hc2_temperature", OperatingDataRegisters.HC2_TEMPERATURE),
            ("hc3_temperature", OperatingDataRegisters.HC3_TEMPERATURE),
            ("room_temperature_2", OperatingDataRegisters.ROOM_TEMPERATURE_2),
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
            ("pv_surplus", EnergyRegisters.PV_SURPLUS),
            ("total_energy_consumed", EnergyRegisters.TOTAL_ENERGY_CONSUMED),
            ("total_heat_generated", EnergyRegisters.TOTAL_HEAT_GENERATED),
            ("heating_energy", EnergyRegisters.HEATING_ENERGY),
            ("hot_water_energy", EnergyRegisters.HOT_WATER_ENERGY),
            ("cooling_energy", EnergyRegisters.COOLING_ENERGY),
            ("pool_energy", EnergyRegisters.POOL_ENERGY),
            ("environmental_energy", EnergyRegisters.ENVIRONMENTAL_ENERGY),
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
            ("compressor_1_runtime", RuntimeRegisters.COMPRESSOR_1_RUNTIME),
            ("compressor_2_runtime", RuntimeRegisters.COMPRESSOR_2_RUNTIME),
            ("primary_pump_fan_runtime", RuntimeRegisters.PRIMARY_PUMP_FAN_RUNTIME),
            ("second_heat_generator_runtime", RuntimeRegisters.SECOND_HEAT_GENERATOR_RUNTIME),
            ("heating_pump_runtime", RuntimeRegisters.HEATING_PUMP_RUNTIME),
            ("hot_water_pump_runtime", RuntimeRegisters.HOT_WATER_PUMP_RUNTIME),
            ("immersion_heater_runtime", RuntimeRegisters.IMMERSION_HEATER_RUNTIME),
            ("pool_pump_runtime", RuntimeRegisters.POOL_PUMP_RUNTIME),
            ("aux_circ_pump_runtime", RuntimeRegisters.AUX_CIRC_PUMP_RUNTIME),
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
            
            # Only calculate COP when both power values are above minimum thresholds
            # This avoids unrealistic spikes during mode transitions (e.g., when pump switches)
            if power_in >= MIN_POWER_IN_FOR_COP and power_out >= MIN_POWER_OUT_FOR_COP:
                raw_cop = power_out / power_in
                
                # Cap unrealistic values (e.g., from measurement artifacts during transitions)
                if raw_cop > MAX_REALISTIC_COP:
                    _LOGGER.debug(
                        "Capping unrealistic COP value %.2f (power_in=%.0fW, power_out=%.0fW)",
                        raw_cop, power_in, power_out
                    )
                    raw_cop = MAX_REALISTIC_COP
                
                # Apply exponential moving average smoothing
                if self._smoothed_cop is not None:
                    # EMA: new_value = alpha * raw_value + (1 - alpha) * previous_smoothed_value
                    smoothed_cop = COP_SMOOTHING_ALPHA * raw_cop + (1 - COP_SMOOTHING_ALPHA) * self._smoothed_cop
                else:
                    # First value: use raw COP as starting point
                    smoothed_cop = raw_cop
                
                # Update stored smoothed value
                self._smoothed_cop = smoothed_cop
                
                # Round to 2 decimal places for display
                data["cop"] = round(smoothed_cop, 2)
            elif power_in > 0:
                # Power values below threshold - don't calculate new COP
                # but keep previous smoothed value if available
                if self._smoothed_cop is not None:
                    data["cop"] = round(self._smoothed_cop, 2)
                # If no previous value, don't set COP (will be None/unavailable)
        
        _LOGGER.debug("Read operating data: %s", data)
        return data