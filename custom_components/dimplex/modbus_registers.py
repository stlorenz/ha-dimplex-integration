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

# Error Messages (Störmeldungen) - Will be populated when documentation is available
# Reference: https://dimplex.atlassian.net/wiki/spaces/DW/pages/3340960678/Modbus+TCP+-+Störmeldungen
ERROR_MESSAGES: Final[dict[int, str]] = {
    0: "none",
    # TODO: Add complete error message mappings when documentation is accessed
    # Error codes range from 1-31
}

# Sensor Error Messages (Sensorfehler) - Available only in L/M software
# Reference: Mentioned in system status, range 1-27
SENSOR_ERROR_MESSAGES: Final[dict[int, str]] = {
    0: "none",
    # TODO: Add sensor error mappings when documentation is accessed
    # Sensor error codes range from 1-27
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

