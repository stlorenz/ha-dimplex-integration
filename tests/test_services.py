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

