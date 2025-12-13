"""Common fixtures for Dimplex tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.dimplex.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_NAME,
    CONF_PORT,
    DOMAIN,
    HeatPumpModel,
)


@pytest.fixture
def mock_modbus_client() -> Generator[Mock, None, None]:
    """Mock the Modbus TCP client."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        client_instance = Mock()
        client_instance.connected = True
        client_instance.connect = AsyncMock(return_value=True)
        client_instance.close = Mock()
        
        # Mock successful register reads
        mock_response = Mock()
        mock_response.isError.return_value = False
        mock_response.registers = [0]  # Default value
        
        client_instance.read_holding_registers = AsyncMock(return_value=mock_response)
        client_instance.read_input_registers = AsyncMock(return_value=mock_response)
        client_instance.write_register = AsyncMock(return_value=mock_response)
        
        mock_client.return_value = client_instance
        yield mock_client


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.dimplex.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_config_entry() -> dict:
    """Return a mock config entry."""
    return {
        "entry_id": "test_entry_id",
        "domain": DOMAIN,
        "data": {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            CONF_NAME: "Test Dimplex",
            CONF_MODEL: HeatPumpModel.LA1422C,
        },
        "options": {
            "cooling_enabled": False,
            "dhw_enabled": True,
            "pool_enabled": False,
            "second_heating_circuit": False,
        },
        "title": "Test Dimplex",
        "unique_id": "test_unique_id",
    }


@pytest.fixture
async def mock_dimplex_coordinator(hass: HomeAssistant) -> AsyncMock:
    """Return a mocked coordinator."""
    coordinator = AsyncMock()
    coordinator.data = {
        "status_code": 2,
        "lock_code": 0,
        "error_code": 0,
        "status": "heating",
        "lock": "none",
        "connected": True,
        "name": "Test Dimplex",  # Add device name
    }
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.last_update_success = True
    # Add model attributes
    coordinator.model = HeatPumpModel.LA1422C
    coordinator.model_name = "LA 1422C (Air/Water)"
    coordinator.cooling_enabled = False
    coordinator.dhw_enabled = True
    coordinator.pool_enabled = False
    coordinator.second_hc_enabled = False
    return coordinator

