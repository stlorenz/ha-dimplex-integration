"""Tests for Dimplex services."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import SupportsResponse
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dimplex.const import DOMAIN
from custom_components.dimplex.services import (
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

