"""Tests for the Dimplex binary sensor platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant

from custom_components.dimplex.binary_sensor import (
    DimplexBinarySensor,
    async_setup_entry,
)
from custom_components.dimplex.const import DOMAIN


@pytest.mark.asyncio
async def test_binary_sensor_setup(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test binary sensor platform setup."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = mock_dimplex_coordinator
    
    entities_added = []
    
    def mock_add_entities(entities):
        entities_added.extend(entities)
    
    await async_setup_entry(hass, config_entry, mock_add_entities)
    
    # Should create 4 binary sensors
    assert len(entities_added) == 4


@pytest.mark.asyncio
async def test_error_active_sensor(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test error active binary sensor."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.binary_sensor import BINARY_SENSOR_TYPES
    
    # Set device name in coordinator data
    mock_dimplex_coordinator.data["name"] = "Test Dimplex"
    
    error_description = next(d for d in BINARY_SENSOR_TYPES if d.key == "error_active")
    sensor = DimplexBinarySensor(
        mock_dimplex_coordinator, config_entry, error_description
    )
    
    assert sensor.unique_id == f"{config_entry.entry_id}_error_active"
    assert sensor.name == "Error Active"
    assert sensor.is_on is False  # error_code is 0
    assert sensor.available is True
    assert sensor.entity_description.device_class == BinarySensorDeviceClass.PROBLEM


@pytest.mark.asyncio
async def test_error_active_sensor_with_error(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test error active binary sensor with error."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    # Set error code
    mock_dimplex_coordinator.data["error_code"] = 5
    
    from custom_components.dimplex.binary_sensor import BINARY_SENSOR_TYPES
    
    error_description = next(d for d in BINARY_SENSOR_TYPES if d.key == "error_active")
    sensor = DimplexBinarySensor(
        mock_dimplex_coordinator, config_entry, error_description
    )
    
    assert sensor.is_on is True


@pytest.mark.asyncio
async def test_lock_active_sensor(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test lock active binary sensor."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.binary_sensor import BINARY_SENSOR_TYPES
    
    lock_description = next(d for d in BINARY_SENSOR_TYPES if d.key == "lock_active")
    sensor = DimplexBinarySensor(
        mock_dimplex_coordinator, config_entry, lock_description
    )
    
    assert sensor.unique_id == f"{config_entry.entry_id}_lock_active"
    assert sensor.is_on is False  # lock_code is 0
    assert sensor.entity_description.device_class == BinarySensorDeviceClass.LOCK


@pytest.mark.asyncio
async def test_heat_pump_running_sensor(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test heat pump running binary sensor."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.binary_sensor import BINARY_SENSOR_TYPES
    
    running_description = next(
        d for d in BINARY_SENSOR_TYPES if d.key == "heat_pump_running"
    )
    sensor = DimplexBinarySensor(
        mock_dimplex_coordinator, config_entry, running_description
    )
    
    assert sensor.unique_id == f"{config_entry.entry_id}_heat_pump_running"
    assert sensor.is_on is True  # status is "heating"
    assert sensor.entity_description.device_class == BinarySensorDeviceClass.RUNNING


@pytest.mark.asyncio
async def test_heat_pump_running_sensor_off(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test heat pump running binary sensor when off."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    # Set status to off
    mock_dimplex_coordinator.data["status"] = "off"
    
    from custom_components.dimplex.binary_sensor import BINARY_SENSOR_TYPES
    
    running_description = next(
        d for d in BINARY_SENSOR_TYPES if d.key == "heat_pump_running"
    )
    sensor = DimplexBinarySensor(
        mock_dimplex_coordinator, config_entry, running_description
    )
    
    assert sensor.is_on is False


@pytest.mark.asyncio
async def test_defrost_active_sensor(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test defrost active binary sensor."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.binary_sensor import BINARY_SENSOR_TYPES
    
    defrost_description = next(
        d for d in BINARY_SENSOR_TYPES if d.key == "defrost_active"
    )
    sensor = DimplexBinarySensor(
        mock_dimplex_coordinator, config_entry, defrost_description
    )
    
    assert sensor.unique_id == f"{config_entry.entry_id}_defrost_active"
    assert sensor.is_on is False  # status is "heating", not "defrost"


@pytest.mark.asyncio
async def test_defrost_active_sensor_on(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test defrost active binary sensor when defrosting."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    # Set status to defrost
    mock_dimplex_coordinator.data["status"] = "defrost"
    
    from custom_components.dimplex.binary_sensor import BINARY_SENSOR_TYPES
    
    defrost_description = next(
        d for d in BINARY_SENSOR_TYPES if d.key == "defrost_active"
    )
    sensor = DimplexBinarySensor(
        mock_dimplex_coordinator, config_entry, defrost_description
    )
    
    assert sensor.is_on is True


@pytest.mark.asyncio
async def test_binary_sensor_unavailable_when_disconnected(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test binary sensor is unavailable when disconnected."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    # Set coordinator to disconnected
    mock_dimplex_coordinator.data["connected"] = False
    
    from custom_components.dimplex.binary_sensor import BINARY_SENSOR_TYPES
    
    error_description = next(d for d in BINARY_SENSOR_TYPES if d.key == "error_active")
    sensor = DimplexBinarySensor(
        mock_dimplex_coordinator, config_entry, error_description
    )
    
    assert sensor.available is False


@pytest.mark.asyncio
async def test_binary_sensor_device_info(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test binary sensor device info."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.binary_sensor import BINARY_SENSOR_TYPES
    
    error_description = next(d for d in BINARY_SENSOR_TYPES if d.key == "error_active")
    sensor = DimplexBinarySensor(
        mock_dimplex_coordinator, config_entry, error_description
    )
    
    device_info = sensor._attr_device_info
    assert device_info["identifiers"] == {(DOMAIN, config_entry.entry_id)}
    assert device_info["name"] == "Test Dimplex"
    assert device_info["manufacturer"] == "Dimplex"

