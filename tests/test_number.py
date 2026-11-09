"""Tests for the Dimplex number platform (writable hot water settings)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.dimplex.modbus_registers import SoftwareVersion
from custom_components.dimplex.modbus_registers_extended import (
    get_register_definition,
)
from custom_components.dimplex.number import (
    NUMBER_DESCRIPTIONS,
    DimplexNumber,
    async_setup_entry,
)


def _coordinator(
    write_enabled: bool = True, dhw_enabled: bool = True, cooling_enabled: bool = False
):
    return SimpleNamespace(
        write_enabled=write_enabled,
        dhw_enabled=dhw_enabled,
        cooling_enabled=cooling_enabled,
        software_version=SoftwareVersion.L_M,
        model_name="LA 1422C (Air/Water)",
        data={"hot_water_setpoint_setting": 45.0, "hot_water_max_setpoint": 60.0},
        client=SimpleNamespace(write_register=AsyncMock(return_value=True)),
        async_request_refresh=AsyncMock(),
        last_update_success=True,
    )


def _entry():
    return SimpleNamespace(entry_id="entry1", data={"name": "Test Dimplex"})


def _setpoint_entity(coordinator):
    desc = next(d for d in NUMBER_DESCRIPTIONS if d.key == "hot_water_setpoint_setting")
    reg = get_register_definition(desc.register, SoftwareVersion.L_M)
    ent = DimplexNumber(coordinator, _entry(), desc, reg)  # type: ignore[arg-type]
    ent.async_write_ha_state = Mock()
    return ent


@pytest.mark.asyncio
async def test_number_reads_value_from_coordinator():
    ent = _setpoint_entity(_coordinator())
    assert ent.native_value == 45.0
    assert ent.unique_id == "entry1_hot_water_setpoint_setting"
    assert ent.device_info is not None


@pytest.mark.asyncio
async def test_number_writes_whole_degrees_to_register_5047():
    coordinator = _coordinator()
    ent = _setpoint_entity(coordinator)

    await ent.async_set_native_value(48)

    coordinator.client.write_register.assert_awaited_once_with(address=5047, value=48)
    assert coordinator.data["hot_water_setpoint_setting"] == 48
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_number_refuses_write_when_write_mode_disabled():
    coordinator = _coordinator(write_enabled=False)
    ent = _setpoint_entity(coordinator)

    await ent.async_set_native_value(48)

    coordinator.client.write_register.assert_not_awaited()
    assert coordinator.data["hot_water_setpoint_setting"] == 45.0


HC1_KEYS = {
    "hc1_parallel_shift",
    "hc1_heating_curve_endpoint",
    "hc1_fixed_setpoint",
    "hc1_hysteresis",
}
HOT_WATER_KEYS = {
    "hot_water_setpoint_setting",
    "hot_water_max_setpoint",
    "hot_water_min_setpoint",
    "hot_water_hysteresis",
}
COOLING_KEYS = {"hc1_cooling_setpoint", "hc1_cooling_setpoint_30"}


@pytest.mark.asyncio
async def test_setup_entry_respects_dhw_and_cooling_flags():
    added: list = []

    async def _run(dhw_enabled: bool, cooling_enabled: bool = False):
        added.clear()
        coordinator = _coordinator(
            dhw_enabled=dhw_enabled, cooling_enabled=cooling_enabled
        )
        hass = SimpleNamespace(data={"dimplex": {"entry1": coordinator}})
        await async_setup_entry(hass, _entry(), lambda ents: added.extend(ents))  # type: ignore[arg-type]
        return {e.entity_description.key for e in added}

    assert await _run(True) == HOT_WATER_KEYS | HC1_KEYS
    assert await _run(False) == HC1_KEYS
    assert (
        await _run(True, cooling_enabled=True)
        == HOT_WATER_KEYS | HC1_KEYS | COOLING_KEYS
    )


@pytest.mark.asyncio
async def test_parallel_shift_uses_offset_encoding():
    """Register 5036: raw 0..38 <-> -19..+19 K (raw 19 = 0 K)."""
    coordinator = _coordinator()
    coordinator.data["hc1_parallel_shift"] = -2.0
    desc = next(d for d in NUMBER_DESCRIPTIONS if d.key == "hc1_parallel_shift")
    reg = get_register_definition(desc.register, SoftwareVersion.L_M)
    ent = DimplexNumber(coordinator, _entry(), desc, reg)  # type: ignore[arg-type]
    ent.async_write_ha_state = Mock()

    assert ent.native_value == -2.0
    await ent.async_set_native_value(3)
    coordinator.client.write_register.assert_awaited_once_with(address=5036, value=22)


@pytest.mark.asyncio
async def test_hc1_hysteresis_written_in_tenths_of_kelvin():
    """Register 47 is 0.1 K (documented 5..50)."""
    coordinator = _coordinator()
    desc = next(d for d in NUMBER_DESCRIPTIONS if d.key == "hc1_hysteresis")
    reg = get_register_definition(desc.register, SoftwareVersion.L_M)
    ent = DimplexNumber(coordinator, _entry(), desc, reg)  # type: ignore[arg-type]
    ent.async_write_ha_state = Mock()

    await ent.async_set_native_value(2.5)
    coordinator.client.write_register.assert_awaited_once_with(address=47, value=25)


def test_hot_water_numbers_unavailable_on_software_h():
    for desc in NUMBER_DESCRIPTIONS:
        assert get_register_definition(desc.register, SoftwareVersion.H) is None
