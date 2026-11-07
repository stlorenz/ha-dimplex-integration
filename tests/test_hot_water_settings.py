"""Tests for the verified hot water settings registers (Dimplex wiki, WPM J/L/M)."""
from custom_components.dimplex.modbus_registers import SoftwareVersion
from custom_components.dimplex.modbus_registers_extended import (
    SettingsRegisters,
    get_register_definition,
    scale_value,
)


def test_hot_water_settings_addresses_lm():
    """Addresses match 'Modbus TCP - Einstellungen Warmwasser' and are whole degrees."""
    expected = {
        "HOT_WATER_COMFORT_SETPOINT": 5047,
        "HOT_WATER_MAX_SETPOINT": 5048,
        "HOT_WATER_MIN_SETPOINT": 5145,
        "HOT_WATER_HYSTERESIS": 5045,
    }
    for name, address in expected.items():
        reg = get_register_definition(getattr(SettingsRegisters, name), SoftwareVersion.L_M)
        assert reg is not None, name
        assert reg.address == address, name
        assert reg.scale == 1.0, name
        assert reg.signed is False, name


def test_hot_water_settings_not_available_on_h():
    for name in ("HOT_WATER_COMFORT_SETPOINT", "HOT_WATER_MAX_SETPOINT",
                 "HOT_WATER_MIN_SETPOINT", "HOT_WATER_HYSTERESIS"):
        assert get_register_definition(getattr(SettingsRegisters, name), SoftwareVersion.H) is None


def test_hot_water_reduced_setpoint_is_unavailable():
    """There is no separate reduced DHW setpoint register on the WPM."""
    for sw in SoftwareVersion:
        assert get_register_definition(SettingsRegisters.HOT_WATER_REDUCED_SETPOINT, sw) is None


def test_hot_water_setpoint_raw_value_is_whole_degrees():
    """Empirically: register 5047 read 45 for a 45 °C setpoint (not 450)."""
    reg = get_register_definition(SettingsRegisters.HOT_WATER_COMFORT_SETPOINT, SoftwareVersion.L_M)
    assert scale_value(45, reg) == 45.0
    assert int(round(48 / reg.scale)) == 48
