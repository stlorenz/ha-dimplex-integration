"""Tests for the Dimplex integration init."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.dimplex import async_setup_entry, async_unload_entry
from custom_components.dimplex.const import CONF_HOST, CONF_PORT, DOMAIN


@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, mock_modbus_client):
    """Test successful setup entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 502,
    }
    entry.runtime_data = None
    
    with patch(
        "custom_components.dimplex.coordinator.DimplexDataUpdateCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = AsyncMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator
        
        with patch.object(hass.config_entries, "async_forward_entry_setups", new=AsyncMock(return_value=True)) as mock_forward:
            result = await async_setup_entry(hass, entry)
            
            assert result is True
            assert DOMAIN in hass.data
            assert entry.entry_id in hass.data[DOMAIN]
            
            # Verify coordinator was created with correct parameters
            mock_coordinator_class.assert_called_once()
            call_kwargs = mock_coordinator_class.call_args[1]
            assert call_kwargs["host"] == "192.168.1.100"
            assert call_kwargs["port"] == 502
            
            # Verify coordinator refresh was called
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()
            
            # Verify platforms were forwarded
            mock_forward.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry(hass: HomeAssistant):
    """Test successful unload entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.runtime_data = None
    
    # Setup coordinator mock
    mock_coordinator = AsyncMock()
    mock_coordinator.async_shutdown = AsyncMock()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = mock_coordinator
    
    with patch.object(
        hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True)
    ) as mock_unload:
        result = await async_unload_entry(hass, entry)
        
        assert result is True
        assert entry.entry_id not in hass.data[DOMAIN]
        
        # Verify coordinator shutdown was called
        mock_coordinator.async_shutdown.assert_called_once()
        
        # Verify platforms were unloaded
        mock_unload.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_failure(hass: HomeAssistant):
    """Test unload entry failure."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.runtime_data = None
    
    mock_coordinator = AsyncMock()
    mock_coordinator.async_shutdown = AsyncMock()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = mock_coordinator
    
    with patch.object(
        hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=False)
    ):
        result = await async_unload_entry(hass, entry)
        
        assert result is False
        # Entry should still be in data if unload failed
        assert entry.entry_id in hass.data[DOMAIN]

