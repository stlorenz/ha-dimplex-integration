"""Extended Modbus register definitions for Dimplex heat pump integration.

This file contains additional register definitions beyond system status.
Register addresses need to be filled in from the Dimplex documentation.

Documentation references:
- Operating Mode: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Betriebsmodus
- Operating Data: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Betriebsdaten
- Runtime Counters: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Laufzeiten
- Heat and Energy: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Wärme-+und+Energiemengen
- Inputs: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Eingänge
- Outputs: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Ausgänge
- Settings: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Einstellungen
"""
from __future__ import annotations

from typing import Final

from .modbus_registers import SoftwareVersion


# TODO: Fill in register addresses from Dimplex documentation
# Operating Mode Registers (Betriebsmodus)
class OperatingModeRegisters:
    """Operating mode register addresses."""

    # TODO: Get from documentation
    CURRENT_MODE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    MODE_HEATING = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    MODE_COOLING = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    MODE_HOT_WATER = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }


# Operating Data Registers (Betriebsdaten)
class OperatingDataRegisters:
    """Operating data register addresses - temperatures, pressures, etc."""

    # Temperature Sensors
    FLOW_TEMPERATURE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in from documentation
    }

    RETURN_TEMPERATURE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    OUTSIDE_TEMPERATURE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    HOT_WATER_TEMPERATURE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    HEAT_SOURCE_INLET_TEMP = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    HEAT_SOURCE_OUTLET_TEMP = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    ROOM_TEMPERATURE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    # Setpoints
    FLOW_SETPOINT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    HOT_WATER_SETPOINT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    # Pressures (if available)
    HIGH_PRESSURE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    LOW_PRESSURE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }


# Runtime Counters (Laufzeiten)
class RuntimeRegisters:
    """Runtime counter register addresses."""

    COMPRESSOR_RUNTIME_TOTAL = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in - might be 2 registers (32-bit)
    }

    COMPRESSOR_STARTS = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    HEATING_RUNTIME = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    HOT_WATER_RUNTIME = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    AUXILIARY_HEATER_RUNTIME = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }


# Heat and Energy Quantities (Wärme- und Energiemengen)
class EnergyRegisters:
    """Energy and heat quantity register addresses."""

    # Power measurements
    CURRENT_POWER_CONSUMPTION = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    CURRENT_HEATING_POWER = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    # Energy totals (likely 32-bit values = 2 registers)
    TOTAL_ENERGY_CONSUMED = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in - start register for 32-bit value
    }

    TOTAL_HEAT_GENERATED = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in - start register for 32-bit value
    }

    HEATING_ENERGY = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    HOT_WATER_ENERGY = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }


# Input/Output States
class IORegisters:
    """Digital input and output register addresses."""

    # Binary inputs
    EXTERNAL_LOCK_INPUT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    EVU_LOCK_INPUT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    # Binary outputs
    COMPRESSOR_OUTPUT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    CIRCULATION_PUMP_OUTPUT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }

    AUXILIARY_HEATER_OUTPUT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in
    }


# Settings Registers (Read/Write)
class SettingsRegisters:
    """Settings register addresses - many are read/write."""

    # Heating Circuit 1
    HC1_COMFORT_SETPOINT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in - R/W
    }

    HC1_REDUCED_SETPOINT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in - R/W
    }

    HC1_HEATING_CURVE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in - R/W
    }

    # Hot Water
    HOT_WATER_COMFORT_SETPOINT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in - R/W
    }

    HOT_WATER_REDUCED_SETPOINT = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None,
        SoftwareVersion.L_M: None,  # TODO: Fill in - R/W
    }


# Data scaling factors and units
REGISTER_SCALING: Final[dict[str, dict]] = {
    "temperature": {
        "factor": 0.1,  # Most temps are in 0.1°C units
        "unit": "°C",
    },
    "pressure": {
        "factor": 0.1,  # Pressures typically in 0.1 bar units
        "unit": "bar",
    },
    "power": {
        "factor": 1.0,  # Power typically in W
        "unit": "W",
    },
    "energy": {
        "factor": 1.0,  # Energy typically in kWh
        "unit": "kWh",
    },
    "runtime": {
        "factor": 1.0,  # Runtime typically in hours
        "unit": "h",
    },
}


def scale_temperature(raw_value: int) -> float:
    """Scale raw temperature value to °C."""
    return raw_value * REGISTER_SCALING["temperature"]["factor"]


def scale_pressure(raw_value: int) -> float:
    """Scale raw pressure value to bar."""
    return raw_value * REGISTER_SCALING["pressure"]["factor"]


def scale_power(raw_value: int) -> float:
    """Scale raw power value to W."""
    return raw_value * REGISTER_SCALING["power"]["factor"]


def read_32bit_value(registers: list[int]) -> int:
    """Combine two 16-bit registers into a 32-bit value.

    Args:
        registers: List of 2 register values [high, low]

    Returns:
        32-bit integer value

    """
    if len(registers) < 2:
        return 0
    return (registers[0] << 16) | registers[1]

