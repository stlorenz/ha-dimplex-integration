"""Tests for the Dimplex Modbus client."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pymodbus.exceptions import ModbusException

from custom_components.dimplex.modbus_client import DimplexModbusClient


@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = DimplexModbusClient("192.168.1.100", 502)
    
    assert client.host == "192.168.1.100"
    assert client.port == 502
    assert client._connected is False
    assert client._client is None


@pytest.mark.asyncio
async def test_client_connect_success():
    """Test successful connection."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.connect = AsyncMock(return_value=True)
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        result = await client.connect()
        
        assert result is True
        assert client.is_connected


@pytest.mark.asyncio
async def test_client_connect_failure():
    """Test connection failure."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.connected = False
        mock_instance.connect = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        result = await client.connect()
        
        assert result is False
        assert client._connected is False


@pytest.mark.asyncio
async def test_read_holding_registers_success():
    """Test reading holding registers successfully."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_response = Mock()
        mock_response.isError.return_value = False
        mock_response.registers = [100, 200]
        
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.read_holding_registers = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        client._client = mock_instance
        client._connected = True
        
        result = await client.read_holding_registers(103, 2)
        
        assert result == [100, 200]
        mock_instance.read_holding_registers.assert_called_once_with(
            address=103, count=2, slave=1
        )


@pytest.mark.asyncio
async def test_read_holding_registers_error():
    """Test reading holding registers with error."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_response = Mock()
        mock_response.isError.return_value = True
        
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.read_holding_registers = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        client._client = mock_instance
        client._connected = True
        
        result = await client.read_holding_registers(103, 1)
        
        assert result is None


@pytest.mark.asyncio
async def test_read_holding_registers_not_connected():
    """Test reading registers when not connected."""
    client = DimplexModbusClient("192.168.1.100", 502)
    
    result = await client.read_holding_registers(103, 1)
    
    assert result is None


@pytest.mark.asyncio
async def test_read_holding_registers_exception():
    """Test reading registers with exception."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.read_holding_registers = AsyncMock(
            side_effect=ModbusException("Test exception")
        )
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        client._client = mock_instance
        client._connected = True
        
        result = await client.read_holding_registers(103, 1)
        
        assert result is None


@pytest.mark.asyncio
async def test_write_register_success():
    """Test writing register successfully."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_response = Mock()
        mock_response.isError.return_value = False
        
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.write_register = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        client._client = mock_instance
        client._connected = True
        
        result = await client.write_register(200, 50)
        
        assert result is True
        mock_instance.write_register.assert_called_once_with(
            address=200, value=50, slave=1
        )


@pytest.mark.asyncio
async def test_write_register_error():
    """Test writing register with error."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_response = Mock()
        mock_response.isError.return_value = True
        
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.write_register = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        client._client = mock_instance
        client._connected = True
        
        result = await client.write_register(200, 50)
        
        assert result is False


@pytest.mark.asyncio
async def test_read_system_status():
    """Test reading system status registers."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.connected = True
        
        # Mock different responses for different registers
        async def mock_read(address, count, slave=1):
            mock_response = Mock()
            mock_response.isError.return_value = False
            if address == 103:  # Status
                mock_response.registers = [2]
            elif address == 104:  # Lock
                mock_response.registers = [0]
            elif address == 105:  # Error
                mock_response.registers = [0]
            return mock_response
        
        mock_instance.read_holding_registers = AsyncMock(side_effect=mock_read)
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        client._client = mock_instance
        client._connected = True
        
        result = await client.read_system_status(103, 104, 105)
        
        assert result["status_code"] == 2
        assert result["lock_code"] == 0
        assert result["error_code"] == 0


@pytest.mark.asyncio
async def test_disconnect():
    """Test disconnecting from device."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.close = Mock()
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        client._client = mock_instance
        client._connected = True
        
        await client.disconnect()
        
        assert client._connected is False
        mock_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_test_connection_success():
    """Test connection test success."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_response = Mock()
        mock_response.isError.return_value = False
        mock_response.registers = [0]
        
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.connect = AsyncMock()
        mock_instance.read_holding_registers = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        # Manually set connected state since we're mocking
        client._connected = True
        client._client = mock_instance
        
        result = await client.test_connection()
        
        assert result is True


@pytest.mark.asyncio
async def test_test_connection_failure():
    """Test connection test failure."""
    with patch(
        "custom_components.dimplex.modbus_client.AsyncModbusTcpClient"
    ) as mock_client:
        mock_instance = Mock()
        mock_instance.connected = False
        mock_instance.connect = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance
        
        client = DimplexModbusClient("192.168.1.100", 502)
        result = await client.test_connection()
        
        assert result is False

