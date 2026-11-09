"""Tests for Dimplex services."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dimplex.const import DOMAIN
from custom_components.dimplex.modbus_registers import SoftwareVersion
from custom_components.dimplex.services import (
    SERVICE_DIAGNOSE_REGISTERS,
    SERVICE_READ_HOLDING,
    SERVICE_READ_INPUT,
    SERVICE_WRITE_REGISTER,
    async_register_services,
)


@pytest.mark.asyncio
async def test_services_registered(hass):
    """Test services are registered with response support."""
    await async_register_services(hass)

    for name in (SERVICE_READ_HOLDING, SERVICE_READ_INPUT, SERVICE_WRITE_REGISTER):
        service = hass.services.async_services()[DOMAIN][name]
        assert service.supports_response == SupportsResponse.ONLY


@pytest.mark.asyncio
async def test_read_holding_service_returns_values(hass):
    """Test reading holding registers via service."""
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    client = Mock()
    client.is_connected = True
    client.connect = AsyncMock(return_value=True)
    client.read_holding_registers = AsyncMock(return_value=[10, 20])

    coordinator = Mock()
    coordinator.client = client
    coordinator.write_enabled = False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await async_register_services(hass)

    resp = await hass.services.async_call(
        DOMAIN,
        SERVICE_READ_HOLDING,
        {"entry_id": entry.entry_id, "address": 103, "count": 2, "unit_id": 1},
        blocking=True,
        return_response=True,
    )

    assert resp["registers"] == [10, 20]
    client.read_holding_registers.assert_called_once_with(address=103, count=2, slave=1)


@pytest.mark.asyncio
async def test_write_register_requires_write_enabled(hass):
    """Test write service requires write mode enabled."""
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    client = Mock()
    client.is_connected = True
    client.connect = AsyncMock(return_value=True)
    client.write_register = AsyncMock(return_value=True)

    coordinator = Mock()
    coordinator.client = client
    coordinator.write_enabled = False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await async_register_services(hass)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_WRITE_REGISTER,
            {"entry_id": entry.entry_id, "address": 200, "value": 123, "unit_id": 1},
            blocking=True,
            return_response=True,
        )


@pytest.mark.asyncio
async def test_diagnose_registers_checks_documented_ranges(hass):
    """The diagnose service reads every mapped datapoint and flags range violations."""
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    client = Mock()
    client.is_connected = True
    client.connect = AsyncMock(return_value=True)

    async def fake_read(address: int, count: int = 1, slave: int = 1):
        if address == 5096:  # heating energy: 12-digit counter in 3 words
            return [1234, 5, 0]
        return {
            1: [152],  # outside temperature 15.2 degC
            5: [355],  # wiki: Vorlauf
            9: [301],  # wiki: 2. Heizkreis
            46: [50],  # HK1 room setpoint 5.0 degC -> below documented 15..30
            5036: [21],  # parallel shift raw 21 -> +2 K
        }.get(address, [0] * count)

    client.read_holding_registers = AsyncMock(side_effect=fake_read)
    client.read_coils = AsyncMock(return_value=[True])

    coordinator = Mock()
    coordinator.client = client
    coordinator.write_enabled = False
    coordinator.software_version = SoftwareVersion.L_M

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await async_register_services(hass)

    resp = await hass.services.async_call(
        DOMAIN,
        SERVICE_DIAGNOSE_REGISTERS,
        {"entry_id": entry.entry_id, "unit_id": 1},
        blocking=True,
        return_response=True,
    )

    regs = resp["registers"]
    assert regs["outside_temperature"]["address"] == 1
    assert regs["outside_temperature"]["value"] == 15.2
    assert regs["outside_temperature"]["verdict"] == "ok"

    assert regs["hc1_room_setpoint"]["value"] == 5.0
    assert regs["hc1_room_setpoint"]["verdict"] == "below_documented_range"
    assert any(p.startswith("hc1_room_setpoint") for p in resp["problems"])

    assert regs["hc1_parallel_shift"]["value"] == 2.0
    assert regs["heating_energy"]["value"] == 51234

    assert resp["coils"]["compressor_1"] == {"address": 41, "state": True}

    assert resp["wiki_cross_check"]["5"]["wiki_name"].startswith("Temperatur Vorlauf")
    assert resp["wiki_cross_check"]["5"]["value_celsius"] == 35.5
    assert resp["wiki_cross_check"]["9"]["integration_uses_it_as"] == "hc2_temperature"


@pytest.mark.asyncio
async def test_set_time_program_writes_selector_then_block(hass):
    """set_time_program selects the function (5065) and writes 5066..5081 in order."""
    from custom_components.dimplex.services import SERVICE_SET_TIME_PROGRAM

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    expected_block = [2, 0, 6, 0, 12, 0, 16, 0, 0, 0, 0, 0, 0, 0, 0, 4]
    client = Mock()
    client.is_connected = True
    client.connect = AsyncMock(return_value=True)
    client.write_register = AsyncMock(return_value=True)
    client.read_holding_registers = AsyncMock(return_value=expected_block)

    coordinator = Mock()
    coordinator.client = client
    coordinator.write_enabled = True
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await async_register_services(hass)

    resp = await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_TIME_PROGRAM,
        {
            "entry_id": entry.entry_id,
            "function": "hc2_raise",
            "window1_start": "02:00",
            "window1_end": "06:00",
            "window2_start": "12:00",
            "window2_end": "16:00",
            "value": 4,
            "readback_delay": 0,
        },
        blocking=True,
        return_response=True,
    )

    calls = client.write_register.await_args_list
    assert calls[0].kwargs == {"address": 5065, "value": 4, "slave": 1}
    written = [(c.kwargs["address"], c.kwargs["value"]) for c in calls[1:]]
    assert written == list(zip(range(5066, 5082), expected_block, strict=False))
    assert resp["success"] is True
    assert resp["readback"] == expected_block


@pytest.mark.asyncio
async def test_set_time_program_requires_write_enabled(hass):
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.dimplex.services import SERVICE_SET_TIME_PROGRAM

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)
    coordinator = Mock()
    coordinator.client = Mock()
    coordinator.client.write_register = AsyncMock(return_value=True)
    coordinator.write_enabled = False
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await async_register_services(hass)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_TIME_PROGRAM,
            {
                "entry_id": entry.entry_id,
                "function": "hc2_raise",
                "window1_start": "02:00",
                "window1_end": "06:00",
                "value": 4,
            },
            blocking=True,
            return_response=True,
        )
    coordinator.client.write_register.assert_not_awaited()


def test_cv_time_hhmm_validation():
    import voluptuous as vol

    from custom_components.dimplex.services import cv_time_hhmm

    assert cv_time_hhmm("02:00") == (2, 0)
    assert cv_time_hhmm("16:30:00") == (16, 30)
    for bad in ("24:00", "12:60", "abc", "12"):
        with pytest.raises(vol.Invalid):
            cv_time_hhmm(bad)


@pytest.mark.asyncio
async def test_set_time_program_rejects_midnight_crossing_window(hass):
    """The WPM silently rewrites windows that cross midnight; refuse them."""
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.dimplex.services import SERVICE_SET_TIME_PROGRAM

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)
    coordinator = Mock()
    coordinator.client = Mock()
    coordinator.client.is_connected = True
    coordinator.client.write_register = AsyncMock(return_value=True)
    coordinator.write_enabled = True
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await async_register_services(hass)

    with pytest.raises(HomeAssistantError, match="crossing midnight"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_TIME_PROGRAM,
            {
                "entry_id": entry.entry_id,
                "function": "hc2_lower",
                "window1_start": "06:00",
                "window1_end": "12:00",
                "window2_start": "16:00",
                "window2_end": "02:00",
                "value": 5,
            },
            blocking=True,
            return_response=True,
        )
    coordinator.client.write_register.assert_not_awaited()
