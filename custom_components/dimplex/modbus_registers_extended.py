"""Extended Modbus register definitions for Dimplex heat pump integration.

This file contains additional register definitions beyond system status.
Register addresses are based on Dimplex WPM III documentation.

Documentation references:
- Operating Mode: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Betriebsmodus
- Operating Data: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Betriebsdaten
- Runtime Counters: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Laufzeiten
- Heat and Energy: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Wärme-+und+Energiemengen
- Inputs: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Eingänge
- Outputs: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Ausgänge
- Settings: https://dimplex.atlassian.net/wiki/spaces/DW/pages/.../Modbus+TCP+-+Einstellungen

Note: Register addresses follow Modbus convention (0-based addressing).
Values are typically 16-bit signed/unsigned integers.
Temperature values are in 0.1°C units (divide by 10).
Pressure values are in 0.01 bar units (divide by 100).
Energy values may span 2 registers (32-bit).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Final

from .modbus_registers import SoftwareVersion


@dataclass
class RegisterDefinition:
    """Definition of a Modbus register."""
    
    address: int | None
    """Register address (None if not available for this software version)"""
    
    scale: float = 1.0
    """Scale factor to convert raw value to final value"""
    
    signed: bool = True
    """Whether the register value is signed"""
    
    size: int = 1
    """Number of registers (1 = 16-bit, 2 = 32-bit)"""
    
    unit: str = ""
    """Unit of the value after scaling"""


class RegisterType(Enum):
    """Types of register data."""
    
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    POWER = "power"
    ENERGY = "energy"
    RUNTIME = "runtime"
    COUNTER = "counter"
    PERCENTAGE = "percentage"
    BOOLEAN = "boolean"


class OperatingMode(IntEnum):
    """Operating mode values for register 5015 (Betriebsmodus).

    Documentation (WPM Software J/L/M):
      0: Sommer
      1: Winter
      2: Urlaub
      3: Party
      4: 2. Wärmeerzeuger
      5: Kühlen
    """

    SUMMER = 0
    WINTER = 1
    VACATION = 2
    PARTY = 3
    SECOND_HEAT_GENERATOR = 4
    COOLING = 5


# Operating Mode Registers (Betriebsmodus)
class OperatingModeRegisters:
    """Operating mode register addresses.
    
    These registers control the operating mode of the heat pump.

    Note: The operating mode is a VALUE written to register 5015 (not a
    software-version-specific "mode"). The register availability varies by
    software version.
    """

    CURRENT_MODE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: 5015,  # Betriebsmodus (R/W), values: see OperatingMode
        SoftwareVersion.L_M: 5015,  # Betriebsmodus (R/W), values: see OperatingMode
    }

    PARTY_HOURS = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: 5016,  # Anzahl Partystunden (0..72) [hour]
        SoftwareVersion.L_M: 5016,  # Anzahl Partystunden (0..72) [hour]
    }

    VACATION_DAYS = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: 5017,  # Anzahl Urlaubstage (0..150) [day]
        SoftwareVersion.L_M: 5017,  # Anzahl Urlaubstage (0..150) [day]
    }

    VENTILATION_STAGE = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: 5034,  # Lüftung Stufen (0..5)
        SoftwareVersion.L_M: 5034,  # Lüftung Stufen (0..5)
    }

    BOOST_VENTILATION_TIME = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: 127,  # Zeitwert Stoßlüften (15..90)
        SoftwareVersion.L_M: 127,  # Zeitwert Stoßlüften (15..90)
    }


# Operating Data Registers (Betriebsdaten)
# These are the main measurement registers for temperatures, pressures, etc.
class OperatingDataRegisters:
    """Operating data register addresses - temperatures, pressures, etc.
    
    Temperature values are stored in 0.1°C units.
    Pressure values are stored in 0.01 bar units.
    """

    # Temperature Sensors (in 0.1°C units, signed)
    FLOW_TEMPERATURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=10, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=10, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=10, scale=0.1, unit="°C"),
    }

    RETURN_TEMPERATURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=11, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=11, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=11, scale=0.1, unit="°C"),
    }

    OUTSIDE_TEMPERATURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=12, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=12, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=12, scale=0.1, unit="°C"),
    }

    HOT_WATER_TEMPERATURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=13, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=13, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=13, scale=0.1, unit="°C"),
    }

    HEAT_SOURCE_INLET_TEMP: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=14, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=14, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=14, scale=0.1, unit="°C"),
    }

    HEAT_SOURCE_OUTLET_TEMP: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=15, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=15, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=15, scale=0.1, unit="°C"),
    }

    ROOM_TEMPERATURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=16, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=16, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=16, scale=0.1, unit="°C"),
    }

    # Setpoints (in 0.1°C units)
    FLOW_SETPOINT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=17, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=17, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=17, scale=0.1, unit="°C"),
    }

    HOT_WATER_SETPOINT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=18, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=18, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=18, scale=0.1, unit="°C"),
    }

    # Additional temperature sensors for refrigerant circuit (diagnostic)
    EVAPORATOR_TEMPERATURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=20, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=20, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=20, scale=0.1, unit="°C"),
    }

    CONDENSER_TEMPERATURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=21, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=21, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=21, scale=0.1, unit="°C"),
    }

    SUCTION_GAS_TEMPERATURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=22, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=22, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=22, scale=0.1, unit="°C"),
    }

    DISCHARGE_GAS_TEMPERATURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=23, scale=0.1, unit="°C"),
        SoftwareVersion.J: RegisterDefinition(address=23, scale=0.1, unit="°C"),
        SoftwareVersion.L_M: RegisterDefinition(address=23, scale=0.1, unit="°C"),
    }

    # Pressure sensors (in 0.01 bar units)
    # High Pressure (condensation pressure)
    HIGH_PRESSURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=30, scale=0.01, unit="bar", signed=False),
        SoftwareVersion.J: RegisterDefinition(address=30, scale=0.01, unit="bar", signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=30, scale=0.01, unit="bar", signed=False),
    }

    # Low Pressure (evaporation pressure)
    LOW_PRESSURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=31, scale=0.01, unit="bar", signed=False),
        SoftwareVersion.J: RegisterDefinition(address=31, scale=0.01, unit="bar", signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=31, scale=0.01, unit="bar", signed=False),
    }

    # Brine circuit pressure (for ground source heat pumps)
    BRINE_PRESSURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=32, scale=0.01, unit="bar", signed=False),
        SoftwareVersion.J: RegisterDefinition(address=32, scale=0.01, unit="bar", signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=32, scale=0.01, unit="bar", signed=False),
    }

    # Heating water system pressure
    WATER_PRESSURE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=33, scale=0.01, unit="bar", signed=False),
        SoftwareVersion.J: RegisterDefinition(address=33, scale=0.01, unit="bar", signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=33, scale=0.01, unit="bar", signed=False),
    }


# Runtime Counters (Laufzeiten)
class RuntimeRegisters:
    """Runtime counter register addresses.
    
    Runtime values are typically in hours.
    Counter values are unitless (number of starts/cycles).
    Large values may use 2 registers (32-bit).
    """

    COMPRESSOR_RUNTIME_TOTAL: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=50, scale=1.0, unit="h", size=2),
        SoftwareVersion.J: RegisterDefinition(address=50, scale=1.0, unit="h", size=2),
        SoftwareVersion.L_M: RegisterDefinition(address=50, scale=1.0, unit="h", size=2),
    }

    COMPRESSOR_STARTS: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=52, scale=1.0, unit="", size=2),
        SoftwareVersion.J: RegisterDefinition(address=52, scale=1.0, unit="", size=2),
        SoftwareVersion.L_M: RegisterDefinition(address=52, scale=1.0, unit="", size=2),
    }

    HEATING_RUNTIME: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=54, scale=1.0, unit="h", size=2),
        SoftwareVersion.J: RegisterDefinition(address=54, scale=1.0, unit="h", size=2),
        SoftwareVersion.L_M: RegisterDefinition(address=54, scale=1.0, unit="h", size=2),
    }

    HOT_WATER_RUNTIME: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=56, scale=1.0, unit="h", size=2),
        SoftwareVersion.J: RegisterDefinition(address=56, scale=1.0, unit="h", size=2),
        SoftwareVersion.L_M: RegisterDefinition(address=56, scale=1.0, unit="h", size=2),
    }

    COOLING_RUNTIME: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=58, scale=1.0, unit="h", size=2),
        SoftwareVersion.J: RegisterDefinition(address=58, scale=1.0, unit="h", size=2),
        SoftwareVersion.L_M: RegisterDefinition(address=58, scale=1.0, unit="h", size=2),
    }

    AUXILIARY_HEATER_RUNTIME: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=60, scale=1.0, unit="h", size=2),
        SoftwareVersion.J: RegisterDefinition(address=60, scale=1.0, unit="h", size=2),
        SoftwareVersion.L_M: RegisterDefinition(address=60, scale=1.0, unit="h", size=2),
    }

    DEFROST_CYCLES: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=62, scale=1.0, unit="", size=2),
        SoftwareVersion.J: RegisterDefinition(address=62, scale=1.0, unit="", size=2),
        SoftwareVersion.L_M: RegisterDefinition(address=62, scale=1.0, unit="", size=2),
    }


# Heat and Energy Quantities (Wärme- und Energiemengen)
class EnergyRegisters:
    """Energy and heat quantity register addresses.
    
    Power values are in Watts.
    Energy values are in kWh (may use 2 registers for 32-bit values).
    """

    # Current power consumption (electrical input power in W)
    CURRENT_POWER_CONSUMPTION: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=70, scale=1.0, unit="W", signed=False),
        SoftwareVersion.J: RegisterDefinition(address=70, scale=1.0, unit="W", signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=70, scale=1.0, unit="W", signed=False),
    }

    # Current heating power (thermal output power in W)
    CURRENT_HEATING_POWER: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=71, scale=1.0, unit="W", signed=False),
        SoftwareVersion.J: RegisterDefinition(address=71, scale=1.0, unit="W", signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=71, scale=1.0, unit="W", signed=False),
    }

    # Total electrical energy consumed (kWh, 32-bit)
    TOTAL_ENERGY_CONSUMED: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=80, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.J: RegisterDefinition(address=80, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=80, scale=0.1, unit="kWh", size=2, signed=False),
    }

    # Total thermal energy generated (kWh, 32-bit)
    TOTAL_HEAT_GENERATED: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=82, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.J: RegisterDefinition(address=82, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=82, scale=0.1, unit="kWh", size=2, signed=False),
    }

    # Heating energy (kWh, 32-bit)
    HEATING_ENERGY: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=84, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.J: RegisterDefinition(address=84, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=84, scale=0.1, unit="kWh", size=2, signed=False),
    }

    # Hot water energy (kWh, 32-bit)
    HOT_WATER_ENERGY: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=86, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.J: RegisterDefinition(address=86, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=86, scale=0.1, unit="kWh", size=2, signed=False),
    }

    # Cooling energy (kWh, 32-bit)
    COOLING_ENERGY: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=88, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.J: RegisterDefinition(address=88, scale=0.1, unit="kWh", size=2, signed=False),
        SoftwareVersion.L_M: RegisterDefinition(address=88, scale=0.1, unit="kWh", size=2, signed=False),
    }


# Input/Output States
class IORegisters:
    """Digital input and output register addresses."""

    # Binary inputs
    EXTERNAL_LOCK_INPUT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=90),
    }

    EVU_LOCK_INPUT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=91),
    }

    # Binary outputs
    COMPRESSOR_OUTPUT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=92),
    }

    CIRCULATION_PUMP_OUTPUT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=93),
    }

    AUXILIARY_HEATER_OUTPUT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=94),
    }


# Settings Registers (Read/Write)
class SettingsRegisters:
    """Settings register addresses - many are read/write."""

    # Heating Circuit 1
    HC1_COMFORT_SETPOINT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=200, scale=0.1, unit="°C"),
    }

    HC1_REDUCED_SETPOINT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=201, scale=0.1, unit="°C"),
    }

    HC1_HEATING_CURVE: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=202, scale=0.01, unit=""),
    }

    # Hot Water
    HOT_WATER_COMFORT_SETPOINT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=210, scale=0.1, unit="°C"),
    }

    HOT_WATER_REDUCED_SETPOINT: dict[SoftwareVersion, RegisterDefinition] = {
        SoftwareVersion.H: RegisterDefinition(address=None),
        SoftwareVersion.J: RegisterDefinition(address=None),
        SoftwareVersion.L_M: RegisterDefinition(address=211, scale=0.1, unit="°C"),
    }


# Data scaling factors and units (legacy - kept for backward compatibility)
REGISTER_SCALING: Final[dict[str, dict]] = {
    "temperature": {
        "factor": 0.1,  # Most temps are in 0.1°C units
        "unit": "°C",
    },
    "pressure": {
        "factor": 0.01,  # Pressures typically in 0.01 bar units
        "unit": "bar",
    },
    "power": {
        "factor": 1.0,  # Power typically in W
        "unit": "W",
    },
    "energy": {
        "factor": 0.1,  # Energy typically in 0.1 kWh units
        "unit": "kWh",
    },
    "runtime": {
        "factor": 1.0,  # Runtime typically in hours
        "unit": "h",
    },
}


def get_register_definition(
    register_dict: dict[SoftwareVersion, RegisterDefinition],
    software_version: SoftwareVersion,
) -> RegisterDefinition | None:
    """Get register definition for a specific software version.
    
    Args:
        register_dict: Dictionary mapping software versions to register definitions
        software_version: The software version to look up
        
    Returns:
        RegisterDefinition if found and has valid address, None otherwise
    """
    reg_def = register_dict.get(software_version)
    if reg_def is None or reg_def.address is None:
        return None
    return reg_def


def scale_value(raw_value: int, register_def: RegisterDefinition) -> float:
    """Scale raw register value using the register definition.
    
    Args:
        raw_value: Raw integer value from register
        register_def: Register definition with scale factor
        
    Returns:
        Scaled float value
    """
    # Handle signed values for temperatures (they can be negative)
    if register_def.signed and raw_value > 32767:
        raw_value = raw_value - 65536
    
    return raw_value * register_def.scale


def scale_temperature(raw_value: int) -> float:
    """Scale raw temperature value to °C."""
    # Handle signed values (temperatures can be negative)
    if raw_value > 32767:
        raw_value = raw_value - 65536
    return raw_value * REGISTER_SCALING["temperature"]["factor"]


def scale_pressure(raw_value: int) -> float:
    """Scale raw pressure value to bar."""
    return raw_value * REGISTER_SCALING["pressure"]["factor"]


def scale_power(raw_value: int) -> float:
    """Scale raw power value to W."""
    return raw_value * REGISTER_SCALING["power"]["factor"]


def scale_energy(raw_value: int) -> float:
    """Scale raw energy value to kWh."""
    return raw_value * REGISTER_SCALING["energy"]["factor"]


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


# All temperature registers for batch reading
TEMPERATURE_REGISTERS: Final[list[str]] = [
    "FLOW_TEMPERATURE",
    "RETURN_TEMPERATURE",
    "OUTSIDE_TEMPERATURE",
    "HOT_WATER_TEMPERATURE",
    "HEAT_SOURCE_INLET_TEMP",
    "HEAT_SOURCE_OUTLET_TEMP",
    "ROOM_TEMPERATURE",
    "FLOW_SETPOINT",
    "HOT_WATER_SETPOINT",
    "EVAPORATOR_TEMPERATURE",
    "CONDENSER_TEMPERATURE",
    "SUCTION_GAS_TEMPERATURE",
    "DISCHARGE_GAS_TEMPERATURE",
]

# All pressure registers for batch reading
PRESSURE_REGISTERS: Final[list[str]] = [
    "HIGH_PRESSURE",
    "LOW_PRESSURE",
    "BRINE_PRESSURE",
    "WATER_PRESSURE",
]

# All energy registers for batch reading
ENERGY_REGISTERS: Final[list[str]] = [
    "CURRENT_POWER_CONSUMPTION",
    "CURRENT_HEATING_POWER",
    "TOTAL_ENERGY_CONSUMED",
    "TOTAL_HEAT_GENERATED",
    "HEATING_ENERGY",
    "HOT_WATER_ENERGY",
    "COOLING_ENERGY",
]

# All runtime registers for batch reading
RUNTIME_REGISTERS: Final[list[str]] = [
    "COMPRESSOR_RUNTIME_TOTAL",
    "COMPRESSOR_STARTS",
    "HEATING_RUNTIME",
    "HOT_WATER_RUNTIME",
    "COOLING_RUNTIME",
    "AUXILIARY_HEATER_RUNTIME",
    "DEFROST_CYCLES",
]
