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
            address=103, count=2, device_id=1
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
            address=200, value=50, device_id=1
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
        async def mock_read(address, count, device_id=1):
            mock_response = Mock()
            mock_response.isError.return_value = False
            if address == 103:  # Status
                mock_response.registers = [2]
            elif address == 104 or address == 105:  # Lock
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


def _connected_client() -> DimplexModbusClient:
    """Return a client whose pymodbus connection is mocked as connected."""
    client = DimplexModbusClient("192.168.1.100", 502)
    client._client = Mock()
    client._client.connected = True
    client._connected = True
    return client


@pytest.mark.asyncio
async def test_read_coils_returns_trimmed_bool_list():
    client = _connected_client()
    response = Mock()
    response.isError.return_value = False
    response.bits = [
        True,
        False,
        True,
        False,
        False,
        False,
        False,
        False,
    ]  # padded byte
    client._client.read_coils = AsyncMock(return_value=response)

    result = await client.read_coils(3, count=4)

    assert result == [True, False, True, False]
    client._client.read_coils.assert_awaited_once()
    _, kwargs = client._client.read_coils.await_args
    assert kwargs["address"] == 3
    assert kwargs["count"] == 4


@pytest.mark.asyncio
async def test_read_coils_error_returns_none():
    client = _connected_client()
    response = Mock()
    response.isError.return_value = True
    client._client.read_coils = AsyncMock(return_value=response)

    assert await client.read_coils(41, count=31) is None


@pytest.mark.asyncio
async def test_read_operating_data_reads_registry_coils_and_derives_values():
    """Datapoints come from REGISTER_DATAPOINTS, coils from two block reads."""
    from custom_components.dimplex.modbus_registers import SoftwareVersion

    client = _connected_client()

    async def fake_holding(address, count=1, slave=None):
        table = {
            1: [-35 & 0xFFFF],  # outside -3.5 degC
            2: [305],  # return 30.5
            5: [352],  # flow 35.2 (wiki: Temperatur Vorlauf R9)
            46: [215],  # HC1 room setpoint 21.5
            5036: [19],  # parallel shift 0 K
            5015: [1],  # Betriebsmodus Winter
            5170: [250],  # 2500 W in
            5168: [900],  # 9000 W out
            72: [12000],  # compressor 1 h
            73: [0],  # compressor 2 h
            5096: [4567, 123, 0],  # heating energy 1 234 567 kWh
            5099: [1, 0, 0],  # hot water 1 kWh
        }
        if address in table:
            return table[address]
        return None  # everything else: read failed -> key absent

    async def fake_coils(address, count=1, slave=None):
        if address == 3:
            return [False, False, True, False]  # EVU lock active
        if address == 41:
            bits = [False] * 31
            bits[0] = True  # compressor 1
            bits[46 - 41] = True  # hot water pump
            return bits
        return None

    client.read_holding_registers = AsyncMock(side_effect=fake_holding)
    client.read_coils = AsyncMock(side_effect=fake_coils)

    data = await client.read_operating_data(SoftwareVersion.L_M)

    assert data["outside_temperature"] == pytest.approx(-3.5)
    assert data["flow_temperature"] == pytest.approx(35.2)
    assert data["hc1_room_setpoint"] == pytest.approx(21.5)
    assert data["hc1_parallel_shift"] == 0
    assert data["operating_mode_code"] == 1
    assert data["operating_mode"] == "winter"
    assert data["current_power_consumption"] == 2500
    assert data["cop"] == pytest.approx(3.6)
    assert data["compressor_runtime_total"] == 12000
    assert data["heating_energy"] == 1_234_567
    assert data["total_heat_generated"] == 1_234_568
    # coils
    assert data["evu_lock"] is True
    assert data["smart_grid_1"] is False
    assert data["compressor_1"] is True
    assert data["compressor_2"] is False
    assert data["hot_water_pump"] is True
    # failed reads simply leave the key out
    assert "room_temperature" not in data
    # exactly two coil block reads
    assert client.read_coils.await_count == 2


@pytest.mark.asyncio
async def test_read_operating_data_skips_everything_on_software_h():
    from custom_components.dimplex.modbus_registers import SoftwareVersion

    client = _connected_client()
    client.read_holding_registers = AsyncMock(return_value=[1])
    client.read_coils = AsyncMock(return_value=[True])

    data = await client.read_operating_data(SoftwareVersion.H)

    assert data == {}
    client.read_holding_registers.assert_not_awaited()
    client.read_coils.assert_not_awaited()
