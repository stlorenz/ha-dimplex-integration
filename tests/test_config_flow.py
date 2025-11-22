"""Tests for the Dimplex config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant import config_entries, setup
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dimplex.config_flow import CannotConnect, InvalidAuth
from custom_components.dimplex.const import CONF_HOST, CONF_NAME, CONF_PORT, DOMAIN


@pytest.fixture(autouse=True)
async def setup_integration(hass: HomeAssistant):
    """Set up the integration for testing."""
    # Register the config flow
    hass.config.components.add(DOMAIN)


@pytest.mark.asyncio
async def test_form_user(hass: HomeAssistant):
    """Test we get the user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_form_user_success(hass: HomeAssistant, mock_modbus_client):
    """Test successful user flow."""
    with patch(
        "custom_components.dimplex.config_flow.PlaceholderHub.authenticate",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
            },
        )
        
        await hass.async_block_till_done()
        
        assert result2["type"] == FlowResultType.CREATE_ENTRY
        assert result2["title"] == "Test Dimplex"
        assert result2["data"] == {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            CONF_NAME: "Test Dimplex",
        }


@pytest.mark.asyncio
async def test_form_cannot_connect(hass: HomeAssistant):
    """Test we handle cannot connect error."""
    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
            },
        )
        
        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_form_invalid_auth(hass: HomeAssistant):
    """Test we handle invalid auth error."""
    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        side_effect=InvalidAuth,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
            },
        )
        
        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_form_unknown_error(hass: HomeAssistant):
    """Test we handle unknown error."""
    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        side_effect=Exception("Test exception"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
            },
        )
        
        assert result2["type"] == FlowResultType.FORM
        assert result2["errors"] == {"base": "unknown"}


@pytest.mark.asyncio
async def test_form_default_values(hass: HomeAssistant):
    """Test form with default values."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    
    # Check that default values are in the schema
    schema = result["data_schema"].schema
    port_field = next((f for f in schema if str(f) == CONF_PORT), None)
    name_field = next((f for f in schema if str(f) == CONF_NAME), None)
    
    # Default values should be set
    assert port_field is not None
    assert name_field is not None

