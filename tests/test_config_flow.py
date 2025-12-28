"""Tests for the Dimplex config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
async def test_config_flow_step_user(hass: HomeAssistant):
    """Test config flow shows the form."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {}

    result = await flow.async_step_user()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    # When no user_input, errors may not be included in result
    assert result.get("errors") is None or result.get("errors") == {}


@pytest.mark.asyncio
async def test_config_flow_step_user_success(hass: HomeAssistant):
    """Test config flow step user with successful validation."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {}

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        new=AsyncMock(return_value={"title": "Test Dimplex"}),
    ):
        result2 = await flow.async_step_user(
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
                CONF_MODEL: HeatPumpModel.LA1422C,
            }
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test Dimplex"
    assert result2["data"][CONF_HOST] == "192.168.1.100"
    assert result2["data"][CONF_PORT] == 502
    assert result2["data"][CONF_NAME] == "Test Dimplex"
    assert result2["data"][CONF_MODEL] == HeatPumpModel.LA1422C
    assert result2["options"]["cooling_enabled"] is False
    assert result2["options"]["dhw_enabled"] is True


@pytest.mark.asyncio
async def test_config_flow_step_user_cannot_connect(hass: HomeAssistant):
    """Test config flow step user with connection error."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {}

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        new=AsyncMock(side_effect=CannotConnect),
    ):
        result2 = await flow.async_step_user(
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
                CONF_MODEL: HeatPumpModel.LA1422C,
            }
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_config_flow_step_user_timeout(hass: HomeAssistant):
    """Test config flow step user with timeout error."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {}

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        new=AsyncMock(side_effect=TimeoutError("Connection timed out")),
    ):
        result2 = await flow.async_step_user(
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
                CONF_MODEL: HeatPumpModel.LA1422C,
            }
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_config_flow_step_user_unknown_error(hass: HomeAssistant):
    """Test config flow step user with unknown error."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {}

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        new=AsyncMock(side_effect=ValueError("Unknown error")),
    ):
        result2 = await flow.async_step_user(
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
                CONF_MODEL: HeatPumpModel.LA1422C,
            }
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


@pytest.mark.asyncio
async def test_config_flow_duplicate_aborts(hass: HomeAssistant):
    """Test duplicate host/port aborts with already_configured."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.1.100:502",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502},
    )
    existing.add_to_hass(hass)
    assert (
        hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, "192.168.1.100:502")
        is not None
    )

    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {}
    # Ensure handler is set for unique_id lookup (depends on HA internals)
    if getattr(flow, "handler", None) != DOMAIN:
        object.__setattr__(flow, "handler", DOMAIN)

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        new=AsyncMock(return_value={"title": "Test Dimplex 2"}),
    ):
        with pytest.raises(AbortFlow, match="already_configured"):
            await flow.async_step_user(
                user_input={
                    CONF_HOST: "192.168.1.100",
                    CONF_PORT: 502,
                    CONF_NAME: "Test Dimplex 2",
                    CONF_MODEL: HeatPumpModel.LA1422C,
                }
            )
