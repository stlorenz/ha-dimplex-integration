"""Tests for Dimplex Modbus register definitions."""
from __future__ import annotations

import pytest

from custom_components.dimplex.modbus_registers import (
    SoftwareVersion,
    get_error_register,
    get_lock_message,
    get_lock_register,
    get_sensor_error_register,
    get_status_message,
    get_status_register,
)


def test_software_version_enum():
    """Test software version enum."""
    assert SoftwareVersion.H == 1
    assert SoftwareVersion.J == 2
    assert SoftwareVersion.L_M == 3


def test_get_status_register():
    """Test getting status register addresses."""
    assert get_status_register(SoftwareVersion.H) == 14
    assert get_status_register(SoftwareVersion.J) == 43
    assert get_status_register(SoftwareVersion.L_M) == 103


def test_get_lock_register():
    """Test getting lock register addresses."""
    assert get_lock_register(SoftwareVersion.H) == 94
    assert get_lock_register(SoftwareVersion.J) == 59
    assert get_lock_register(SoftwareVersion.L_M) == 104


def test_get_error_register():
    """Test getting error register addresses."""
    assert get_error_register(SoftwareVersion.H) == 13
    assert get_error_register(SoftwareVersion.J) == 42
    assert get_error_register(SoftwareVersion.L_M) == 105


def test_get_sensor_error_register():
    """Test getting sensor error register addresses."""
    assert get_sensor_error_register(SoftwareVersion.H) is None
    assert get_sensor_error_register(SoftwareVersion.J) is None
    assert get_sensor_error_register(SoftwareVersion.L_M) == 106


def test_get_status_message_lm():
    """Test getting status messages for L/M software."""
    assert get_status_message(0, SoftwareVersion.L_M) == "off"
    assert get_status_message(2, SoftwareVersion.L_M) == "heating"
    assert get_status_message(3, SoftwareVersion.L_M) == "pool"
    assert get_status_message(4, SoftwareVersion.L_M) == "hot_water"
    assert get_status_message(5, SoftwareVersion.L_M) == "cooling"
    assert get_status_message(10, SoftwareVersion.L_M) == "defrost"
    assert get_status_message(999, SoftwareVersion.L_M) == "unknown_999"


def test_get_status_message_hj():
    """Test getting status messages for H/J software."""
    assert get_status_message(0, SoftwareVersion.J) == "off"
    assert get_status_message(1, SoftwareVersion.J) == "heat_pump_on_heating"
    assert get_status_message(21, SoftwareVersion.J) == "heat_pump_on_defrost"
    assert get_status_message(24, SoftwareVersion.J) == "cooling_mode"


def test_get_lock_message_lm():
    """Test getting lock messages for L/M software."""
    assert get_lock_message(0, SoftwareVersion.L_M) == "none"
    assert get_lock_message(2, SoftwareVersion.L_M) == "flow_rate"
    assert get_lock_message(11, SoftwareVersion.L_M) == "load_management"
    assert get_lock_message(15, SoftwareVersion.L_M) == "utility_lock"
    assert get_lock_message(35, SoftwareVersion.L_M) == "error_active"
    assert get_lock_message(999, SoftwareVersion.L_M) == "unknown_999"


def test_get_lock_message_j():
    """Test getting lock messages for J software."""
    assert get_lock_message(0, SoftwareVersion.J) == "none"
    assert get_lock_message(7, SoftwareVersion.J) == "utility_lock"
    assert get_lock_message(43, SoftwareVersion.J) == "error_active"


def test_get_lock_message_h():
    """Test getting lock messages for H software."""
    assert get_lock_message(0, SoftwareVersion.H) == "none"
    assert get_lock_message(1, SoftwareVersion.H) == "outside_temperature"
    assert get_lock_message(7, SoftwareVersion.H) == "utility_lock"


def test_status_translations():
    """Test that all status keys have translations."""
    from custom_components.dimplex.modbus_registers import (
        STATUS_MESSAGES_LM,
        STATUS_TRANSLATIONS_EN,
    )
    
    for key in STATUS_MESSAGES_LM.values():
        if not key.startswith("unknown"):
            assert key in STATUS_TRANSLATIONS_EN, f"Missing translation for status: {key}"


def test_lock_translations():
    """Test that all lock keys have translations."""
    from custom_components.dimplex.modbus_registers import (
        LOCK_MESSAGES_LM,
        LOCK_TRANSLATIONS_EN,
    )
    
    for key in LOCK_MESSAGES_LM.values():
        if not key.startswith("unknown"):
            assert key in LOCK_TRANSLATIONS_EN, f"Missing translation for lock: {key}"

