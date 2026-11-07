"""Tests for the Dimplex number platform (writable hot water settings)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.dimplex.modbus_registers import SoftwareVersion
from custom_components.dimplex.modbus_registers_extended import (
    SettingsRegisters,
    get_register_definition,
)
from custom_components.dimplex.number import (
    NUMBER_DESCRIPTIONS,
    DimplexNumber,
    async_setup_entry,
)


def _coordinator(write_enabled: bool = True, dhw_enabled: bool = True):
    return SimpleNamespace(
        write_enabled=write_enabled,
        dhw_enabled=dhw_enabled,
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


@pytest.mark.asyncio
async def test_setup_entry_creates_hot_water_numbers_only_with_dhw():
    added: list = []

    async def _run(dhw_enabled: bool):
        added.clear()
        coordinator = _coordinator(dhw_enabled=dhw_enabled)
        hass = SimpleNamespace(data={"dimplex": {"entry1": coordinator}})
        await async_setup_entry(hass, _entry(), lambda ents: added.extend(ents))  # type: ignore[arg-type]
        return {e.entity_description.key for e in added}

    assert await _run(True) == {
        "hot_water_setpoint_setting",
        "hot_water_max_setpoint",
        "hot_water_min_setpoint",
        "hot_water_hysteresis",
    }
    assert await _run(False) == set()


def test_hot_water_numbers_unavailable_on_software_h():
    for desc in NUMBER_DESCRIPTIONS:
        assert get_register_definition(desc.register, SoftwareVersion.H) is None
