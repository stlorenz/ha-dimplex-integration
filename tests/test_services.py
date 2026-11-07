"""Tests for Dimplex services."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import SupportsResponse
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

    with pytest.raises(Exception):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_WRITE_REGISTER,
            {"entry_id": entry.entry_id, "address": 200, "value": 123, "unit_id": 1},
            blocking=True,
            return_response=True,
        )


@pytest.mark.asyncio
async def test_diagnose_registers_returns_all_interpretations(hass):
    """The diagnose service returns raw + every plausible decode."""
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    client = Mock()
    client.is_connected = True
    client.connect = AsyncMock(return_value=True)

    # Pressure regs 32 (=230) and 33 (=180); aux temps 20-23 with one negative;
    # 32-bit counters all return [hi=0, lo=12345] so big-endian gives 12345.
    async def fake_read(address: int, count: int = 1, slave: int = 1):
        if count == 2:
            return [0, 12345]
        # 16-bit reads
        return {
            32: [230],
            33: [180],
            20: [65484],  # -52 as 16-bit signed -> -5.2 °C
            21: [250],
            22: [180],
            23: [350],
        }.get(address, [0])

    client.read_holding_registers = AsyncMock(side_effect=fake_read)

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

    # Pressure: both scales reported
    brine = resp["pressure_registers"]["brine_pressure"]
    assert brine["raw"] == 230
    assert brine["scale_0_01_bar"] == 2.30
    assert brine["scale_0_1_bar"] == 23.0

    # Aux temp: signed vs unsigned reported
    evap = resp["aux_temperature_registers"]["evaporator_temperature"]
    assert evap["raw"] == 65484
    assert evap["signed_0_1_celsius"] == -5.2
    assert evap["unsigned_0_1_celsius"] == 6548.4

    # 32-bit: both endiannesses reported
    runtime = resp["thirtytwo_bit_registers"]["compressor_runtime_total"]
    assert runtime["raw_words"] == [0, 12345]
    assert runtime["big_endian_unsigned"] == 12345
    assert runtime["little_endian_unsigned"] == 12345 << 16



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
        },
        blocking=True,
        return_response=True,
    )

    calls = client.write_register.await_args_list
    assert calls[0].kwargs == {"address": 5065, "value": 4, "slave": 1}
    written = [(c.kwargs["address"], c.kwargs["value"]) for c in calls[1:]]
    assert written == list(zip(range(5066, 5082), expected_block))
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
