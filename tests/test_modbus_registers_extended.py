"""Tests for the extended register map against the Dimplex wiki datapoint list."""

from __future__ import annotations

import pytest

from custom_components.dimplex.modbus_registers import SoftwareVersion
from custom_components.dimplex.modbus_registers_extended import (
    COIL_DATAPOINTS,
    COMPUTED_DATAPOINTS,
    INPUT_COIL_BLOCK,
    OUTPUT_COIL_BLOCK,
    REGISTER_DATAPOINTS,
    InputCoils,
    OperatingDataRegisters,
    OutputCoils,
    RuntimeRegisters,
    SettingsRegisters,
    decode_digits_12,
    get_coil_address,
    get_register_definition,
    scale_value,
)

LM = SoftwareVersion.L_M


def test_every_extended_datapoint_is_unavailable_on_software_h():
    """Software H only exposes the system status registers."""
    for key, reg_map in REGISTER_DATAPOINTS.items():
        assert get_register_definition(reg_map, SoftwareVersion.H) is None, key
    for key, coil_map in COIL_DATAPOINTS.items():
        assert get_coil_address(coil_map, SoftwareVersion.H) is None, key


@pytest.mark.parametrize(
    ("attr", "address"),
    [
        ("OUTSIDE_TEMPERATURE", 1),
        ("RETURN_TEMPERATURE", 2),
        ("HOT_WATER_TEMPERATURE", 3),
        ("HEAT_SOURCE_INLET_TEMP", 6),
        ("HEAT_SOURCE_OUTLET_TEMP", 7),
        ("HC3_TEMPERATURE", 10),
        ("ROOM_TEMPERATURE", 11),
        ("ROOM_TEMPERATURE_2", 12),
        ("ROOM_HUMIDITY", 13),
        ("ROOM_HUMIDITY_2", 14),
        ("PASSIVE_COOLING_FLOW_TEMP", 19),
        ("PASSIVE_COOLING_RETURN_TEMP", 20),
        ("PRIMARY_CIRCUIT_RETURN_TEMP", 21),
        ("SOLAR_STORAGE_TEMPERATURE", 23),
        ("RETURN_SETPOINT", 53),
        ("HC2_SETPOINT", 54),
        ("HC3_SETPOINT", 55),
        ("HOT_WATER_SETPOINT", 58),
    ],
)
def test_operating_data_addresses_match_wiki(attr: str, address: int):
    reg = get_register_definition(getattr(OperatingDataRegisters, attr), LM)
    assert reg is not None
    assert reg.address == address
    assert reg.scale == 0.1


def test_flow_and_hc2_temperature_follow_the_wiki():
    """Verified 2026-11-09 with the compressor running: 5 = Vorlauf, 9 = 2. HK."""
    flow = get_register_definition(OperatingDataRegisters.FLOW_TEMPERATURE, LM)
    hc2 = get_register_definition(OperatingDataRegisters.HC2_TEMPERATURE, LM)
    assert flow.address == 5
    assert hc2.address == 9


def test_undocumented_registers_are_gone():
    """Refrigerant temps 20-23, pressures 32/33 and 32-bit counters were guesses."""
    for name in (
        "EVAPORATOR_TEMPERATURE",
        "CONDENSER_TEMPERATURE",
        "SUCTION_GAS_TEMPERATURE",
        "DISCHARGE_GAS_TEMPERATURE",
        "BRINE_PRESSURE",
        "WATER_PRESSURE",
    ):
        assert not hasattr(OperatingDataRegisters, name), name
    for name in ("COMPRESSOR_RUNTIME_TOTAL", "COMPRESSOR_STARTS", "DEFROST_CYCLES"):
        assert not hasattr(RuntimeRegisters, name), name
    assert "total_energy_consumed" not in REGISTER_DATAPOINTS
    assert "cooling_energy" not in REGISTER_DATAPOINTS


@pytest.mark.parametrize(
    ("attr", "address"),
    [
        ("COMPRESSOR_1_RUNTIME", 72),
        ("COMPRESSOR_2_RUNTIME", 73),
        ("PRIMARY_PUMP_FAN_RUNTIME", 74),
        ("SECOND_HEAT_GENERATOR_RUNTIME", 75),
        ("HEATING_PUMP_RUNTIME", 76),
        ("HOT_WATER_PUMP_RUNTIME", 77),
        ("IMMERSION_HEATER_RUNTIME", 78),
        ("POOL_PUMP_RUNTIME", 79),
    ],
)
def test_runtime_addresses_match_wiki(attr: str, address: int):
    reg = get_register_definition(getattr(RuntimeRegisters, attr), LM)
    assert reg.address == address
    assert reg.size == 1
    assert reg.signed is False
    assert reg.unit == "h"


def test_aux_circ_pump_runtime_is_lm_only():
    assert (
        get_register_definition(RuntimeRegisters.AUX_CIRC_PUMP_RUNTIME, LM).address
        == 71
    )
    assert (
        get_register_definition(
            RuntimeRegisters.AUX_CIRC_PUMP_RUNTIME, SoftwareVersion.J
        )
        is None
    )


def test_hc1_settings_match_wiki():
    """Wiki 'Einstellungen 1. Heiz-/Kuehlkreis'."""
    room = get_register_definition(SettingsRegisters.HC1_ROOM_SETPOINT, LM)
    assert (room.address, room.scale, room.min_value, room.max_value) == (
        46,
        0.1,
        15.0,
        30.0,
    )
    assert room.to_raw(22.5) == 225

    shift = get_register_definition(SettingsRegisters.HC1_PARALLEL_SHIFT, LM)
    assert shift.address == 5036
    assert scale_value(0, shift) == -19
    assert scale_value(19, shift) == 0
    assert scale_value(38, shift) == 19
    assert shift.to_raw(-19) == 0
    assert shift.to_raw(5) == 24

    assert (
        get_register_definition(SettingsRegisters.HC1_FIXED_SETPOINT, LM).address
        == 5037
    )
    assert (
        get_register_definition(
            SettingsRegisters.HC1_HEATING_CURVE_ENDPOINT, LM
        ).address
        == 5038
    )

    hyst = get_register_definition(SettingsRegisters.HC1_HYSTERESIS, LM)
    assert (hyst.address, hyst.scale) == (47, 0.1)
    assert hyst.to_raw(2.5) == 25

    assert (
        get_register_definition(SettingsRegisters.HC1_COOLING_SETPOINT, LM).address
        == 5043
    )
    assert (
        get_register_definition(SettingsRegisters.HC1_COOLING_SETPOINT_30, LM).address
        == 5134
    )
    assert (
        get_register_definition(
            SettingsRegisters.HC1_COOLING_SETPOINT_30, SoftwareVersion.J
        )
        is None
    )


def test_coil_addresses_match_wiki():
    assert get_coil_address(InputCoils.SMART_GRID_1, LM) == 3
    assert get_coil_address(InputCoils.EVU_LOCK, LM) == 5
    assert get_coil_address(InputCoils.EXTERNAL_LOCK, LM) == 6
    assert get_coil_address(OutputCoils.COMPRESSOR_1, LM) == 41
    assert get_coil_address(OutputCoils.HOT_WATER_PUMP, LM) == 46
    assert get_coil_address(OutputCoils.COLLECTIVE_FAULT, LM) == 57
    assert get_coil_address(OutputCoils.SOLAR_PUMP, LM) == 71


def test_coil_blocks_cover_every_coil():
    """Every coil must fall into one of the two block reads."""
    blocks = (INPUT_COIL_BLOCK, OUTPUT_COIL_BLOCK)
    for key, coil_map in COIL_DATAPOINTS.items():
        addr = get_coil_address(coil_map, LM)
        assert any(start <= addr < start + count for start, count in blocks), key


def test_decode_digits_12_uses_wiki_formula():
    """value = w3 * 10^8 + w2 * 10^4 + w1."""
    assert decode_digits_12([4567, 123, 0]) == 1_234_567
    assert decode_digits_12([0, 0, 1]) == 100_000_000
    assert decode_digits_12([10_000, 0, 0]) is None  # not a 4-digit chunk
    assert decode_digits_12([1, 2]) is None


def test_energy_counters_are_12_digit_and_documented():
    for key in (
        "heating_energy",
        "hot_water_energy",
        "pool_energy",
        "environmental_energy",
    ):
        reg = get_register_definition(REGISTER_DATAPOINTS[key], LM)
        assert reg.size == 3
        assert reg.decoder is decode_digits_12
    assert (
        get_register_definition(REGISTER_DATAPOINTS["heating_energy"], LM).address
        == 5096
    )
    assert (
        get_register_definition(REGISTER_DATAPOINTS["environmental_energy"], LM).address
        == 5127
    )


def test_power_registers_are_in_10w_steps():
    reg = get_register_definition(REGISTER_DATAPOINTS["current_power_consumption"], LM)
    assert reg.address == 5170
    assert scale_value(250, reg) == 2500.0
    reg = get_register_definition(REGISTER_DATAPOINTS["current_heating_power"], LM)
    assert reg.address == 5168


def test_computed_datapoints_are_not_read_from_registers():
    for key in COMPUTED_DATAPOINTS:
        assert key not in REGISTER_DATAPOINTS
        assert key not in COIL_DATAPOINTS


# ----------------------------------------------------------- HC2 settings
def test_hc2_settings_follow_the_wiki_page():
    """Wiki "Einstellungen 2./3. Heiz-/Kuehlkreis": shared block behind 5082."""
    from custom_components.dimplex.modbus_registers_extended import (
        HC2_SELECTOR_VALUE,
        HC2_SETTINGS_DATAPOINTS,
        HC3_SELECTOR_VALUE,
        HC_SETTINGS_SELECTOR,
        REGISTER_DATAPOINTS,
        HC2SettingsRegisters,
    )

    sel = get_register_definition(HC_SETTINGS_SELECTOR, SoftwareVersion.L_M)
    assert sel is not None and sel.address == 5082
    assert (sel.min_value, sel.max_value) == (2, 3)
    assert (HC2_SELECTOR_VALUE, HC3_SELECTOR_VALUE) == (2, 3)
    assert get_register_definition(HC_SETTINGS_SELECTOR, SoftwareVersion.H) is None

    expected = {
        "hc2_heating_curve_endpoint": (5084, 20, 70),
        "hc2_fixed_setpoint": (5085, 20, 60),
        "hc2_parallel_shift": (5086, -19, 19),
        "hc2_mixer_runtime": (5087, 1, 6),
        "hc2_mixer_hysteresis": (93, 0.5, 2.0),
        "hc2_max_temperature": (5088, 30, 70),
        "hc2_cooling_room_setpoint": (5089, 15.0, 30.0),
    }
    assert set(HC2_SETTINGS_DATAPOINTS) == set(expected)
    for key, (addr, lo, hi) in expected.items():
        reg = get_register_definition(HC2_SETTINGS_DATAPOINTS[key], SoftwareVersion.L_M)
        assert reg is not None, key
        assert (reg.address, reg.min_value, reg.max_value) == (addr, lo, hi), key
        assert reg.writable, key
        # the block must never be read without the selector -> not in the plain loop
        assert key not in REGISTER_DATAPOINTS

    shift = get_register_definition(
        HC2SettingsRegisters.PARALLEL_SHIFT, SoftwareVersion.J
    )
    assert shift is not None
    assert (
        scale_value(19, shift) == 0
        and shift.to_raw(-19) == 0
        and shift.to_raw(19) == 38
    )

    cool = get_register_definition(
        HC2SettingsRegisters.COOLING_ROOM_SETPOINT, SoftwareVersion.L_M
    )
    assert cool is not None
    assert scale_value(0, cool) == 15.0 and scale_value(30, cool) == 30.0
    assert cool.to_raw(22.5) == 15
