"""Tests for the Dimplex config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow, FlowResultType
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
    CONF_SLAVE_ID,
    CONF_SOFTWARE_VERSION,
    DOMAIN,
    OPT_COOLING_ENABLED,
    OPT_DHW_ENABLED,
    OPT_HEAT_SOURCE,
    HeatPumpModel,
)
from custom_components.dimplex.modbus_registers import SoftwareVersion


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
        hass.config_entries.async_entry_for_domain_unique_id(
            DOMAIN, "192.168.1.100:502"
        )
        is not None
    )

    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {}
    # Ensure handler is set for unique_id lookup (depends on HA internals)
    if getattr(flow, "handler", None) != DOMAIN:
        object.__setattr__(flow, "handler", DOMAIN)

    with (
        patch(
            "custom_components.dimplex.config_flow.validate_input",
            new=AsyncMock(return_value={"title": "Test Dimplex 2"}),
        ),
        pytest.raises(AbortFlow, match="already_configured"),
    ):
        await flow.async_step_user(
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex 2",
                CONF_MODEL: HeatPumpModel.LA1422C,
            }
        )


@pytest.mark.asyncio
async def test_config_flow_persists_software_version_and_slave(
    hass: HomeAssistant,
):
    """User-step submission carries software_version and slave_id into entry data."""
    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {}

    with patch(
        "custom_components.dimplex.config_flow.validate_input",
        new=AsyncMock(return_value={"title": "Test Dimplex"}),
    ):
        result = await flow.async_step_user(
            user_input={
                CONF_HOST: "192.168.1.50",
                CONF_PORT: 502,
                CONF_NAME: "Test Dimplex",
                CONF_MODEL: HeatPumpModel.SI_SERIES,
                CONF_SOFTWARE_VERSION: int(SoftwareVersion.J),
                CONF_SLAVE_ID: 5,
            }
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SOFTWARE_VERSION] == int(SoftwareVersion.J)
    assert result["data"][CONF_SLAVE_ID] == 5
    assert result["data"][CONF_MODEL] == HeatPumpModel.SI_SERIES


@pytest.mark.asyncio
async def test_options_flow_two_steps_persists_overrides(
    hass: HomeAssistant, enable_custom_integrations
):
    """End-to-end options flow: init (model + sw version) -> features -> save.

    Goes through hass.config_entries.options so the OptionsFlow.config_entry
    context resolves correctly (verifies the HA 2025.12 deprecation fix).
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="opts-test",
        data={
            CONF_HOST: "10.0.0.5",
            CONF_PORT: 502,
            CONF_NAME: "Optstest",
            CONF_MODEL: HeatPumpModel.LA1422C,
            CONF_SOFTWARE_VERSION: int(SoftwareVersion.L_M),
            CONF_SLAVE_ID: 1,
        },
        options={},
    )
    entry.add_to_hass(hass)

    # Don't actually set up the platforms; we only care about the options flow.
    with patch(
        "custom_components.dimplex.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        # Step 1: open the options flow (renders init form)
        init_result = await hass.config_entries.options.async_init(entry.entry_id)
        assert init_result["type"] == FlowResultType.FORM
        assert init_result["step_id"] == "init"

        # Step 2: submit model + software version -> features form
        features_result = await hass.config_entries.options.async_configure(
            init_result["flow_id"],
            user_input={
                CONF_MODEL: HeatPumpModel.SI_SERIES,
                CONF_SOFTWARE_VERSION: int(SoftwareVersion.J),
            },
        )
        assert features_result["type"] == FlowResultType.FORM
        assert features_result["step_id"] == "features"

        # Step 3: submit feature overrides -> create entry
        done = await hass.config_entries.options.async_configure(
            features_result["flow_id"],
            user_input={
                OPT_COOLING_ENABLED: True,
                OPT_DHW_ENABLED: True,
                OPT_HEAT_SOURCE: "brine",
            },
        )
        assert done["type"] == FlowResultType.CREATE_ENTRY

    # Verify the persisted options include the model + sw override.
    assert entry.options[CONF_MODEL] == HeatPumpModel.SI_SERIES
    assert entry.options[CONF_SOFTWARE_VERSION] == int(SoftwareVersion.J)
    assert entry.options[OPT_COOLING_ENABLED] is True
    assert entry.options[OPT_HEAT_SOURCE] == "brine"


# ----------------------------------------------------------------- reconfigure
def _reconfigurable_entry(host: str = "10.0.0.5", unique_id: str | None = None):
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=unique_id or f"{host}:502",
        title="Keller",
        data={
            CONF_HOST: host,
            CONF_PORT: 502,
            CONF_NAME: "Keller",
            CONF_MODEL: HeatPumpModel.LA1422C,
            CONF_SOFTWARE_VERSION: int(SoftwareVersion.L_M),
            CONF_SLAVE_ID: 1,
        },
    )


async def _start_reconfigure(hass: HomeAssistant, entry: MockConfigEntry):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
    )


@pytest.mark.asyncio
async def test_reconfigure_updates_host_and_unique_id(
    hass: HomeAssistant, enable_custom_integrations
):
    """A new IP is written to the existing entry; entry_id and name survive."""
    entry = _reconfigurable_entry()
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.dimplex.async_setup_entry",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "custom_components.dimplex.config_flow.validate_input",
            new=AsyncMock(return_value={"title": "Keller"}),
        ) as validate,
    ):
        result = await _start_reconfigure(hass, entry)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"
        assert result["description_placeholders"] == {"name": "Keller"}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.0.0.99", CONF_PORT: 503, CONF_SLAVE_ID: 2},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    # validate_input saw the merged data (new host, old model/name)
    (_, data), _ = validate.await_args
    assert data[CONF_HOST] == "10.0.0.99"
    assert data[CONF_MODEL] == HeatPumpModel.LA1422C

    assert entry.data[CONF_HOST] == "10.0.0.99"
    assert entry.data[CONF_PORT] == 503
    assert entry.data[CONF_SLAVE_ID] == 2
    assert entry.data[CONF_NAME] == "Keller"  # untouched
    assert entry.data[CONF_SOFTWARE_VERSION] == int(SoftwareVersion.L_M)
    assert entry.unique_id == "10.0.0.99:503"
    assert entry.title == "Keller"


@pytest.mark.asyncio
async def test_reconfigure_cannot_connect_shows_error(
    hass: HomeAssistant, enable_custom_integrations
):
    entry = _reconfigurable_entry()
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.dimplex.async_setup_entry",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "custom_components.dimplex.config_flow.validate_input",
            new=AsyncMock(side_effect=CannotConnect),
        ),
    ):
        result = await _start_reconfigure(hass, entry)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_HOST: "10.0.0.99"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    # nothing persisted
    assert entry.data[CONF_HOST] == "10.0.0.5"
    assert entry.unique_id == "10.0.0.5:502"


@pytest.mark.asyncio
async def test_reconfigure_rejects_host_of_other_entry(
    hass: HomeAssistant, enable_custom_integrations
):
    entry = _reconfigurable_entry("10.0.0.5")
    other = _reconfigurable_entry("10.0.0.6")
    entry.add_to_hass(hass)
    other.add_to_hass(hass)

    with (
        patch(
            "custom_components.dimplex.async_setup_entry",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "custom_components.dimplex.config_flow.validate_input",
            new=AsyncMock(return_value={"title": "Keller"}),
        ) as validate,
    ):
        result = await _start_reconfigure(hass, entry)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_HOST: "10.0.0.6", CONF_PORT: 502}
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    validate.assert_not_awaited()
    assert entry.data[CONF_HOST] == "10.0.0.5"


@pytest.mark.asyncio
async def test_reconfigure_same_host_is_allowed(
    hass: HomeAssistant, enable_custom_integrations
):
    """Changing only the unit ID keeps host/port and must not trip the duplicate check."""
    entry = _reconfigurable_entry()
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.dimplex.async_setup_entry",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "custom_components.dimplex.config_flow.validate_input",
            new=AsyncMock(return_value={"title": "Keller"}),
        ),
    ):
        result = await _start_reconfigure(hass, entry)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "10.0.0.5", CONF_PORT: 502, CONF_SLAVE_ID: 7},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_SLAVE_ID] == 7
    assert entry.unique_id == "10.0.0.5:502"
