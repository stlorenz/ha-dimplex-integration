"""Tests for the Dimplex sensor platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.dimplex.const import DOMAIN
from custom_components.dimplex.sensor import DimplexSensor, async_setup_entry


@pytest.mark.asyncio
async def test_sensor_setup(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test sensor platform setup."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = mock_dimplex_coordinator
    
    entities_added = []
    
    def mock_add_entities(entities):
        entities_added.extend(entities)
    
    await async_setup_entry(hass, config_entry, mock_add_entities)
    
    # Should create 6 sensors (status, status_code, lock, lock_code, error_code, sensor_error_code)
    # Note: sensor_error_code may not be created if not in coordinator data
    assert len(entities_added) >= 5


@pytest.mark.asyncio
async def test_sensor_status(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test status sensor."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.sensor import SENSOR_TYPES
    
    # Set device name in coordinator data
    mock_dimplex_coordinator.data["name"] = "Test Dimplex"
    
    status_description = next(d for d in SENSOR_TYPES if d.key == "status")
    sensor = DimplexSensor(mock_dimplex_coordinator, config_entry, status_description)
    
    assert sensor.unique_id == f"{config_entry.entry_id}_status"
    assert sensor.name == "Test Dimplex Status"
    # native_value returns the raw enum value, not translated
    assert sensor.native_value == "heating"
    assert sensor.available is True
    assert sensor.entity_description.device_class == SensorDeviceClass.ENUM


@pytest.mark.asyncio
async def test_sensor_status_code(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test status code sensor."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.sensor import SENSOR_TYPES
    
    status_code_description = next(d for d in SENSOR_TYPES if d.key == "status_code")
    sensor = DimplexSensor(
        mock_dimplex_coordinator, config_entry, status_code_description
    )
    
    assert sensor.unique_id == f"{config_entry.entry_id}_status_code"
    assert sensor.native_value == 2
    assert sensor.available is True


@pytest.mark.asyncio
async def test_sensor_lock(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test lock sensor."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.sensor import SENSOR_TYPES
    
    # Set device name in coordinator data
    mock_dimplex_coordinator.data["name"] = "Test Dimplex"
    
    lock_description = next(d for d in SENSOR_TYPES if d.key == "lock")
    sensor = DimplexSensor(mock_dimplex_coordinator, config_entry, lock_description)
    
    assert sensor.unique_id == f"{config_entry.entry_id}_lock"
    assert sensor.name == "Test Dimplex Lock Status"
    # native_value returns the raw enum value, not translated
    assert sensor.native_value == "none"
    assert sensor.available is True


@pytest.mark.asyncio
async def test_sensor_unavailable_when_disconnected(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test sensor is unavailable when disconnected."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    # Set coordinator to disconnected
    mock_dimplex_coordinator.data["connected"] = False
    
    from custom_components.dimplex.sensor import SENSOR_TYPES
    
    status_description = next(d for d in SENSOR_TYPES if d.key == "status")
    sensor = DimplexSensor(mock_dimplex_coordinator, config_entry, status_description)
    
    assert sensor.available is False


@pytest.mark.asyncio
async def test_sensor_extra_attributes(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test sensor extra attributes."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.sensor import SENSOR_TYPES
    
    status_description = next(d for d in SENSOR_TYPES if d.key == "status")
    sensor = DimplexSensor(mock_dimplex_coordinator, config_entry, status_description)
    
    attributes = sensor.extra_state_attributes
    assert "code" in attributes
    assert attributes["code"] == 2


@pytest.mark.asyncio
async def test_sensor_device_info(
    hass: HomeAssistant,
    mock_dimplex_coordinator: AsyncMock,
    mock_config_entry: dict,
):
    """Test sensor device info."""
    config_entry = Mock()
    config_entry.entry_id = mock_config_entry["entry_id"]
    config_entry.data = mock_config_entry["data"]
    
    from custom_components.dimplex.sensor import SENSOR_TYPES
    
    status_description = next(d for d in SENSOR_TYPES if d.key == "status")
    sensor = DimplexSensor(mock_dimplex_coordinator, config_entry, status_description)
    
    device_info = sensor._attr_device_info
    assert device_info["identifiers"] == {(DOMAIN, config_entry.entry_id)}
    assert device_info["name"] == "Test Dimplex"
    assert device_info["manufacturer"] == "Dimplex"
    assert device_info["model"] == "LA 1422C (Air/Water)"  # Now uses model_name from coordinator

