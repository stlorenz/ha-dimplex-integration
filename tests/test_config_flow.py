"""Tests for the Dimplex config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dimplex.config_flow import (
    CannotConnect,
    ConfigFlow,
    validate_input,
)
from custom_components.dimplex.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_NAME,
    CONF_PORT,
    DOMAIN,
    HeatPumpModel,
)


@pytest.mark.asyncio
async def test_validate_input_success(hass: HomeAssistant):
    """Test successful input validation."""
    with patch(
        "custom_components.dimplex.config_flow.DimplexModbusClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock()
        mock_client_class.return_value = mock_client

        data = {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            CONF_NAME: "Test Dimplex",
        }

        result = await validate_input(hass, data)
        assert result == {"title": "Test Dimplex"}
        mock_client.test_connection.assert_called_once()
        mock_client.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_validate_input_connection_failure(hass: HomeAssistant):
    """Test input validation with connection failure."""
    with patch(
        "custom_components.dimplex.config_flow.DimplexModbusClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.test_connection = AsyncMock(return_value=False)
        mock_client.disconnect = AsyncMock()
        mock_client_class.return_value = mock_client

        data = {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            CONF_NAME: "Test Dimplex",
        }

        with pytest.raises(CannotConnect):
            await validate_input(hass, data)


@pytest.mark.asyncio
async def test_config_flow_step_user():
    """Test config flow step user."""
    flow = ConfigFlow()
    flow.hass = AsyncMock()

    result = await flow.async_step_user()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    # When no user_input, errors may not be included in result
    assert result.get("errors") is None or result.get("errors") == {}


@pytest.mark.asyncio
async def test_config_flow_step_user_success():
    """Test config flow step user with successful validation."""
    flow = ConfigFlow()
    flow.hass = AsyncMock()

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        return_value={"title": "Test Dimplex"},
    ):
        with patch.object(flow, "async_create_entry", return_value={"type": "create_entry"}) as mock_create:
            result = await flow.async_step_user(
                user_input={
                    CONF_HOST: "192.168.1.100",
                    CONF_PORT: 502,
                    CONF_NAME: "Test Dimplex",
                    CONF_MODEL: HeatPumpModel.LA1422C,
                }
            )

            # Verify create_entry was called with correct data including options
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["title"] == "Test Dimplex"
            assert call_kwargs["data"][CONF_HOST] == "192.168.1.100"
            assert call_kwargs["data"][CONF_PORT] == 502
            assert call_kwargs["data"][CONF_NAME] == "Test Dimplex"
            assert call_kwargs["data"][CONF_MODEL] == HeatPumpModel.LA1422C
            # Options should be set based on model defaults
            assert "options" in call_kwargs
            assert call_kwargs["options"]["cooling_enabled"] is False  # LA1422C default
            assert call_kwargs["options"]["dhw_enabled"] is True


@pytest.mark.asyncio
async def test_config_flow_step_user_cannot_connect():
    """Test config flow step user with connection error."""
    flow = ConfigFlow()
    flow.hass = AsyncMock()

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        side_effect=CannotConnect,
    ):
        result = await flow.async_step_user(
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_config_flow_step_user_timeout():
    """Test config flow step user with timeout error."""
    flow = ConfigFlow()
    flow.hass = AsyncMock()

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        side_effect=TimeoutError("Connection timed out"),
    ):
        result = await flow.async_step_user(
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_config_flow_step_user_unknown_error():
    """Test config flow step user with unknown error."""
    flow = ConfigFlow()
    flow.hass = AsyncMock()

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        side_effect=ValueError("Unknown error"),
    ):
        result = await flow.async_step_user(
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}
