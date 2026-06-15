"""Modbus register definitions for Dimplex heat pump integration."""
from __future__ import annotations

from enum import IntEnum
from typing import Final

# Software version detection will determine which register set to use
# Default to L/M (latest) version


class SoftwareVersion(IntEnum):
    """WPM Software versions."""

    H = 1
    J = 2
    L_M = 3  # Latest versions L and M


class RegisterAddress:
    """Modbus register addresses for different software versions."""

    # System Status Registers - varies by software version
    STATUS_MESSAGE = {
        SoftwareVersion.H: 14,
        SoftwareVersion.J: 43,
        SoftwareVersion.L_M: 103,
    }

    LOCK_MESSAGE = {
        SoftwareVersion.H: 94,
        SoftwareVersion.J: 59,
        SoftwareVersion.L_M: 104,
    }

    ERROR_MESSAGE = {
        SoftwareVersion.H: 13,
        SoftwareVersion.J: 42,
        SoftwareVersion.L_M: 105,
    }

    SENSOR_ERROR = {
        SoftwareVersion.H: None,  # Not available
        SoftwareVersion.J: None,  # Not available
        SoftwareVersion.L_M: 106,
    }


# Status Messages (Statusmeldungen)
# Reference: https://dimplex.atlassian.net/wiki/spaces/DW/pages/3340960438/Modbus+TCP+-+Statusmeldungen
STATUS_MESSAGES_LM: Final[dict[int, str]] = {
    0: "off",
    2: "heating",
    3: "pool",
    4: "hot_water",
    5: "cooling",
    10: "defrost",
    11: "flow_monitoring",
    24: "delay_mode_switch",
    30: "locked",
}

STATUS_MESSAGES_HJ: Final[dict[int, str]] = {
    0: "off",
    1: "heat_pump_on_heating",
    2: "heat_pump_on_heating",
    3: "heat_pump_on_pool",
    4: "heat_pump_on_hot_water",
    5: "heat_pump_on_heating_auxiliary",
    6: "heat_pump_on_pool_auxiliary",
    7: "heat_pump_on_hot_water_auxiliary",
    8: "primary_pump_flow",
    9: "heating_purge",
    10: "locked",
    11: "lower_operation_limit",
    12: "low_pressure_limit",
    13: "low_pressure_shutdown",
    14: "high_pressure_safety",
    15: "anti_cycling",
    16: "minimum_standby",
    17: "load_management",
    18: "flow_monitoring",
    19: "auxiliary_heater",
    20: "low_pressure_brine",
    21: "heat_pump_on_defrost",
    22: "upper_operation_limit",
    23: "external_lock",
    24: "cooling_mode",
    25: "frost_protection",
    26: "flow_limit",
    27: "dew_point_monitor",
    28: "dew_point",
    29: "passive_cooling",
}

# Lock Messages (Sperrmeldungen)
# Reference: https://dimplex.atlassian.net/wiki/spaces/DW/pages/3341091050/Modbus+TCP+-+Sperrmeldungen
LOCK_MESSAGES_LM: Final[dict[int, str]] = {
    0: "none",
    2: "flow_rate",
    5: "function_control",
    6: "operation_limit_auxiliary",
    7: "system_control",
    8: "delay_cooling_switch",
    9: "pump_prerun",
    10: "minimum_standby",
    11: "load_management",
    12: "anti_cycling",
    13: "hot_water_post_heating",
    14: "regenerative",
    15: "utility_lock",
    16: "soft_starter",
    17: "flow_rate_monitoring",
    18: "heat_pump_operation_limit",
    19: "high_pressure",
    20: "low_pressure",
    21: "heat_source_limit",
    23: "system_limit",
    24: "primary_circuit_load",
    25: "external_lock",
    29: "inverter",
    31: "warm_up",
    33: "evd_initialization",
    34: "auxiliary_heater_enabled",
    35: "error_active",
}

LOCK_MESSAGES_J: Final[dict[int, str]] = {
    0: "none",
    1: "operation_limit_auxiliary",
    2: "heat_pump_operation_limit",
    3: "regenerative",
    5: "hot_water_post_heating",
    6: "system_control",
    7: "utility_lock",
    9: "high_pressure",
    10: "low_pressure",
    11: "flow_rate",
    12: "soft_starter",
    36: "pump_prerun",
    37: "minimum_standby",
    38: "load_management",
    39: "anti_cycling",
    40: "heat_source_limit",
    41: "external_lock",
    42: "auxiliary_heater",
    43: "error_active",
}

LOCK_MESSAGES_H: Final[dict[int, str]] = {
    0: "none",
    1: "outside_temperature",
    2: "bivalent_alternative",
    3: "bivalent_regenerative",
    4: "return_temperature",
    5: "hot_water",
    6: "system_control",
    7: "utility_lock",
}

# Error Messages (Störmeldungen)
# Source: Dimplex WPM Touch operating instructions, FD 0101 (452117.66.02-EN),
# §11 "Error history" (F1..F31). The Modbus error register holds the numeric
# code; the F-prefix in the WPM UI maps 1:1 to that number.
# Reference: https://dimplex.atlassian.net/wiki/spaces/DW/pages/3340960678/Modbus+TCP+-+Stoermeldungen
#
# Note: Codes 4, 9, 11..14, 17, 18, 27 are documented as "reserved / unused"
# in WPM Touch FD 0101 — they're intentionally absent from this map.
ERROR_MESSAGES: Final[dict[int, str]] = {
    0: "none",
    1: "extension_n17_1_general_cooling",
    2: "extension_n17_2_active_cooling",
    3: "extension_n17_3_passive_cooling",
    5: "extension_n17_cooling",
    6: "electronic_expansion_valve",
    7: "rth_room_modulator",
    8: "odu_extension",
    10: "wpio_extension",
    15: "sensors",
    16: "brine_pressure_monitor",
    19: "primary_circuit",
    20: "defrost",
    21: "brine_pressure_monitor",
    22: "domestic_hot_water",
    23: "compressor_load",
    24: "coding",
    25: "low_pressure",
    26: "frost_protection",
    28: "high_pressure",
    29: "temperature_difference",
    30: "hot_gas_thermostat",
    31: "flow",
}

ERROR_TRANSLATIONS_EN: Final[dict[str, str]] = {
    "none": "No Fault",
    "extension_n17_1_general_cooling":
        "F1 — Extension N17.1 (General Cooling) not detected",
    "extension_n17_2_active_cooling":
        "F2 — Extension N17.2 (Active Cooling) not detected",
    "extension_n17_3_passive_cooling":
        "F3 — Extension N17.3 (Passive Cooling) not detected",
    "extension_n17_cooling": "F5 — Extension N17 (Cooling) not detected",
    "electronic_expansion_valve": "F6 — Electronic expansion valve not detected",
    "rth_room_modulator": "F7 — RTH room modulator not detected",
    "odu_extension": "F8 — ODU / refrigeration circuit controller not detected",
    "wpio_extension": "F10 — WPIO extension fault",
    "sensors": "F15 — Sensor fault (cause shown on WPM display)",
    "brine_pressure_monitor": "F16/F21 — Brine pressure monitor tripped",
    "primary_circuit":
        "F19 — Primary circuit fault (pump/fan motor protection)",
    "defrost": "F20 — Defrost could not start or finish properly",
    "domestic_hot_water":
        "F22 — Domestic hot water temperature below 35 °C in heat-pump mode",
    "compressor_load":
        "F23 — Compressor load fault (rotation, phase, undervoltage, etc.)",
    "coding": "F24 — Coding does not match heat pump type",
    "low_pressure": "F25 — Heat source delivering insufficient energy",
    "frost_protection": "F26 — Flow temperature below 7 °C (frost protection)",
    "high_pressure":
        "F28 — High pressure sensor / pressostat tripped",
    "temperature_difference":
        "F29 — Flow/return temperature difference too large or negative",
    "hot_gas_thermostat": "F30 — Hot gas thermostat",
    "flow": "F31 — No flow in primary or secondary circuit",
}

# Sensor Error Messages (Sensorfehler) - L/M software only.
# Reference: range 1..27 in the sensor-error register. The number identifies
# which physical sensor (R1, R2, R3, …) is broken or short-circuited.
# The Dimplex WPM Touch manual lumps all of these into the generic "F15 Sensors"
# fault; the per-sensor mapping is not published in the public docs.
#
# UNVERIFIED: Codes 1..27 listed here follow the standard WPM sensor labelling
# (R1 = outside, R2 = return, R3 = DHW, …). Replace with verified values once
# Dimplex's Modbus reference for register 106 is available.
SENSOR_ERROR_MESSAGES: Final[dict[int, str]] = {
    0: "none",
    # Numeric → identifier mapping not yet authoritatively documented for
    # Modbus register 106. Codes are surfaced as the raw integer until then.
}


# Human-readable translations for status codes
STATUS_TRANSLATIONS_EN: Final[dict[str, str]] = {
    "off": "Off",
    "heating": "Heating",
    "pool": "Swimming Pool",
    "hot_water": "Hot Water",
    "cooling": "Cooling",
    "defrost": "Defrost",
    "flow_monitoring": "Flow Monitoring",
    "delay_mode_switch": "Delay Mode Switch",
    "locked": "Locked",
    "heat_pump_on_heating": "Heat Pump On - Heating",
    "heat_pump_on_pool": "Heat Pump On - Pool",
    "heat_pump_on_hot_water": "Heat Pump On - Hot Water",
    "heat_pump_on_heating_auxiliary": "Heat Pump On - Heating + Auxiliary",
    "heat_pump_on_pool_auxiliary": "Heat Pump On - Pool + Auxiliary",
    "heat_pump_on_hot_water_auxiliary": "Heat Pump On - Hot Water + Auxiliary",
    "primary_pump_flow": "Primary Pump Flow",
    "heating_purge": "Heating Purge",
    "lower_operation_limit": "Lower Operation Limit",
    "low_pressure_limit": "Low Pressure Limit",
    "low_pressure_shutdown": "Low Pressure Shutdown",
    "high_pressure_safety": "High Pressure Safety",
    "anti_cycling": "Anti-Cycling Protection",
    "minimum_standby": "Minimum Standby Time",
    "load_management": "Load Management",
    "auxiliary_heater": "Auxiliary Heater",
    "low_pressure_brine": "Low Pressure Brine",
    "heat_pump_on_defrost": "Heat Pump On - Defrost",
    "upper_operation_limit": "Upper Operation Limit",
    "external_lock": "External Lock",
    "cooling_mode": "Cooling Mode",
    "frost_protection": "Frost Protection",
    "flow_limit": "Flow Limit",
    "dew_point_monitor": "Dew Point Monitor",
    "dew_point": "Dew Point",
    "passive_cooling": "Passive Cooling",
}

LOCK_TRANSLATIONS_EN: Final[dict[str, str]] = {
    "none": "No Lock",
    "flow_rate": "Flow Rate",
    "function_control": "Function Control",
    "operation_limit_auxiliary": "Operation Limit - Auxiliary Heater",
    "system_control": "System Control",
    "delay_cooling_switch": "Delay - Cooling Switch",
    "pump_prerun": "Pump Pre-run",
    "minimum_standby": "Minimum Standby Time",
    "load_management": "Load Management",
    "anti_cycling": "Anti-Cycling Protection",
    "hot_water_post_heating": "Hot Water Post-Heating",
    "regenerative": "Regenerative",
    "utility_lock": "Utility Company Lock (EVU)",
    "soft_starter": "Soft Starter",
    "flow_rate_monitoring": "Flow Rate Monitoring",
    "heat_pump_operation_limit": "Heat Pump Operation Limit",
    "high_pressure": "High Pressure",
    "low_pressure": "Low Pressure",
    "heat_source_limit": "Heat Source Limit",
    "system_limit": "System Limit",
    "primary_circuit_load": "Primary Circuit Load",
    "external_lock": "External Lock",
    "inverter": "Inverter",
    "warm_up": "Warm-Up",
    "evd_initialization": "EvD Initialization",
    "auxiliary_heater_enabled": "Auxiliary Heater Enabled",
    "error_active": "Error Active",
    "outside_temperature": "Outside Temperature",
    "bivalent_alternative": "Bivalent Alternative",
    "bivalent_regenerative": "Bivalent Regenerative",
    "return_temperature": "Return Temperature",
    "hot_water": "Hot Water",
}


def get_status_message(value: int, software_version: SoftwareVersion) -> str:
    """Get status message for a given value and software version.

    Args:
        value: The register value (0-30)
        software_version: The WPM software version

    Returns:
        Status message key string

    """
    if software_version == SoftwareVersion.L_M:
        return STATUS_MESSAGES_LM.get(value, f"unknown_{value}")
    return STATUS_MESSAGES_HJ.get(value, f"unknown_{value}")


def get_lock_message(value: int, software_version: SoftwareVersion) -> str:
    """Get lock message for a given value and software version.

    Args:
        value: The register value (0-42)
        software_version: The WPM software version

    Returns:
        Lock message key string

    """
    if software_version == SoftwareVersion.L_M:
        return LOCK_MESSAGES_LM.get(value, f"unknown_{value}")
    if software_version == SoftwareVersion.J:
        return LOCK_MESSAGES_J.get(value, f"unknown_{value}")
    return LOCK_MESSAGES_H.get(value, f"unknown_{value}")


def get_status_register(software_version: SoftwareVersion) -> int:
    """Get the correct status register address for the software version."""
    return RegisterAddress.STATUS_MESSAGE[software_version]


def get_lock_register(software_version: SoftwareVersion) -> int:
    """Get the correct lock register address for the software version."""
    return RegisterAddress.LOCK_MESSAGE[software_version]


def get_error_register(software_version: SoftwareVersion) -> int:
    """Get the correct error register address for the software version."""
    return RegisterAddress.ERROR_MESSAGE[software_version]


def get_sensor_error_register(software_version: SoftwareVersion) -> int | None:
    """Get the correct sensor error register address for the software version."""
    return RegisterAddress.SENSOR_ERROR.get(software_version)


def get_error_message(value: int, software_version: SoftwareVersion) -> str:
    """Map a numeric error register value to a stable string identifier.

    The published WPM Touch (FD 0101) F-code table is treated as authoritative
    for software L/M; H and J return the same mapping until version-specific
    differences are documented.
    """
    # Currently no per-version differences known; ERROR_MESSAGES is shared.
    del software_version  # placeholder for future per-version splits
    return ERROR_MESSAGES.get(value, f"unknown_{value}")

