"""Tests for the Dimplex coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.dimplex.coordinator import DimplexDataUpdateCoordinator
from custom_components.dimplex.modbus_registers import SoftwareVersion


@pytest.mark.asyncio
async def test_coordinator_initialization(hass: HomeAssistant):
    """Test coordinator initialization."""
    coordinator = DimplexDataUpdateCoordinator(
        hass,
        host="192.168.1.100",
        port=502,
        software_version=SoftwareVersion.L_M,
    )
    
    assert coordinator.host == "192.168.1.100"
    assert coordinator.port == 502
    assert coordinator.software_version == SoftwareVersion.L_M
    assert coordinator.client is not None


@pytest.mark.asyncio
async def test_coordinator_update_success(hass: HomeAssistant):
    """Test successful data update."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_response = Mock()
        mock_response.isError.return_value = False
        
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.connect = AsyncMock(return_value=True)
        
        # Mock system status response
        async def mock_read_system_status(status_reg, lock_reg, error_reg):
            return {
                "status_code": 2,
                "lock_code": 0,
                "error_code": 0,
            }
        
        mock_instance.read_holding_registers = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        
        coordinator = DimplexDataUpdateCoordinator(
            hass,
            host="192.168.1.100",
            port=502,
        )
        
        # Patch the client's read_system_status method and is_connected property
        coordinator.client.read_system_status = AsyncMock(
            return_value=mock_read_system_status(103, 104, 105)
        )
        # Mock the is_connected property
        type(coordinator.client).is_connected = property(lambda self: True)
        
        data = await coordinator._async_update_data()
        
        assert data["status_code"] == 2
        assert data["lock_code"] == 0
        assert data["error_code"] == 0
        assert data["status"] == "heating"
        assert data["lock"] == "none"
        assert data["connected"] is True


@pytest.mark.asyncio
async def test_coordinator_update_connection_failure(hass: HomeAssistant):
    """Test update with connection failure."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.connected = False
        mock_instance.connect = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance
        
        coordinator = DimplexDataUpdateCoordinator(
            hass,
            host="192.168.1.100",
            port=502,
        )
        # Mock the is_connected property to return False
        type(coordinator.client).is_connected = property(lambda self: False)
        coordinator.client.connect = AsyncMock(return_value=False)
        
        with pytest.raises(UpdateFailed, match="Failed to connect"):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_no_data(hass: HomeAssistant):
    """Test update with no data received."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.connect = AsyncMock(return_value=True)
        mock_client.return_value = mock_instance
        
        coordinator = DimplexDataUpdateCoordinator(
            hass,
            host="192.168.1.100",
            port=502,
        )
        # Mock the is_connected property
        type(coordinator.client).is_connected = property(lambda self: True)
        coordinator.client.read_system_status = AsyncMock(return_value={})
        
        with pytest.raises(UpdateFailed, match="No data received"):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_timeout(hass: HomeAssistant):
    """Test update with timeout."""
    import asyncio
    
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.connect = AsyncMock(return_value=True)
        mock_client.return_value = mock_instance
        
        coordinator = DimplexDataUpdateCoordinator(
            hass,
            host="192.168.1.100",
            port=502,
        )
        # Mock the is_connected property
        type(coordinator.client).is_connected = property(lambda self: True)
        
        # Simulate timeout
        async def slow_read(*args, **kwargs):
            await asyncio.sleep(15)
            return {"status_code": 0}
        
        coordinator.client.read_system_status = slow_read
        
        with pytest.raises(UpdateFailed, match="Timeout"):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_with_sensor_error(hass: HomeAssistant):
    """Test update including sensor error register."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_response = Mock()
        mock_response.isError.return_value = False
        mock_response.registers = [5]  # Sensor error value
        
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.connect = AsyncMock(return_value=True)
        mock_instance.read_holding_registers = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        
        coordinator = DimplexDataUpdateCoordinator(
            hass,
            host="192.168.1.100",
            port=502,
            software_version=SoftwareVersion.L_M,  # Supports sensor errors
        )
        
        # Mock the is_connected property
        type(coordinator.client).is_connected = property(lambda self: True)
        coordinator.client.read_system_status = AsyncMock(
            return_value={
                "status_code": 0,
                "lock_code": 0,
                "error_code": 0,
            }
        )
        
        data = await coordinator._async_update_data()
        
        assert "sensor_error_code" in data
        assert data["sensor_error_code"] == 5


@pytest.mark.asyncio
async def test_coordinator_shutdown(hass: HomeAssistant):
    """Test coordinator shutdown."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.close = Mock()
        mock_client.return_value = mock_instance
        
        coordinator = DimplexDataUpdateCoordinator(
            hass,
            host="192.168.1.100",
            port=502,
        )
        coordinator.client.disconnect = AsyncMock()
        
        await coordinator.async_shutdown()
        
        coordinator.client.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_coordinator_different_software_versions(hass: HomeAssistant):
    """Test coordinator with different software versions."""
    for version in [SoftwareVersion.H, SoftwareVersion.J, SoftwareVersion.L_M]:
        coordinator = DimplexDataUpdateCoordinator(
            hass,
            host="192.168.1.100",
            port=502,
            software_version=version,
        )
        
        assert coordinator.software_version == version

