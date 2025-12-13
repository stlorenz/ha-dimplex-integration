"""Config flow for Dimplex integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_NAME,
    CONF_PORT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
    MODEL_CAPABILITIES,
    MODEL_NAMES,
    OPT_COOLING_ENABLED,
    OPT_DHW_ENABLED,
    OPT_POOL_ENABLED,
    OPT_SECOND_HEATING_CIRCUIT,
    HeatPumpModel,
    get_model_capabilities,
)
from .modbus_client import DimplexModbusClient

_LOGGER = logging.getLogger(__name__)

# Build model selection options
MODEL_OPTIONS = {model: name for model, name in MODEL_NAMES.items()}

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_MODEL, default=HeatPumpModel.LA1422C): vol.In(MODEL_OPTIONS),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    client = DimplexModbusClient(
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
    )

    try:
        if not await client.test_connection():
            raise CannotConnect("Failed to connect to Dimplex device")
    finally:
        await client.disconnect()

    # Return info that you want to store in the config entry.
    return {"title": data[CONF_NAME]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dimplex."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> DimplexOptionsFlowHandler:
        """Get the options flow for this handler."""
        return DimplexOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors: dict[str, str] = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except (OSError, TimeoutError) as err:
            _LOGGER.warning("Connection error during setup: %s", err)
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception during config validation")
            errors["base"] = "unknown"
        else:
            # Set default options based on model capabilities
            model = user_input.get(CONF_MODEL, HeatPumpModel.GENERIC)
            capabilities = get_model_capabilities(model)

            # Create entry with default options from model capabilities
            return self.async_create_entry(
                title=info["title"],
                data=user_input,
                options={
                    OPT_COOLING_ENABLED: capabilities.get("cooling_default", False),
                    OPT_DHW_ENABLED: capabilities.get("dhw_default", True),
                    OPT_POOL_ENABLED: capabilities.get("pool_default", False),
                    OPT_SECOND_HEATING_CIRCUIT: capabilities.get(
                        "second_hc_default", False
                    ),
                },
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class DimplexOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Dimplex options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get model and its capabilities
        model = self.config_entry.data.get(CONF_MODEL, HeatPumpModel.GENERIC)
        capabilities = get_model_capabilities(model)

        # Build options schema based on what the model supports
        schema_dict: dict[vol.Marker, Any] = {}

        # Only show cooling option if the model supports it
        if capabilities.get("cooling_capable", False):
            schema_dict[
                vol.Optional(
                    OPT_COOLING_ENABLED,
                    default=self.config_entry.options.get(
                        OPT_COOLING_ENABLED, capabilities.get("cooling_default", False)
                    ),
                )
            ] = bool

        # DHW option
        if capabilities.get("dhw_capable", True):
            schema_dict[
                vol.Optional(
                    OPT_DHW_ENABLED,
                    default=self.config_entry.options.get(
                        OPT_DHW_ENABLED, capabilities.get("dhw_default", True)
                    ),
                )
            ] = bool

        # Pool option
        if capabilities.get("pool_capable", False):
            schema_dict[
                vol.Optional(
                    OPT_POOL_ENABLED,
                    default=self.config_entry.options.get(
                        OPT_POOL_ENABLED, capabilities.get("pool_default", False)
                    ),
                )
            ] = bool

        # Second heating circuit option
        if capabilities.get("second_hc_capable", False):
            schema_dict[
                vol.Optional(
                    OPT_SECOND_HEATING_CIRCUIT,
                    default=self.config_entry.options.get(
                        OPT_SECOND_HEATING_CIRCUIT,
                        capabilities.get("second_hc_default", False),
                    ),
                )
            ] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "model": MODEL_NAMES.get(model, model),
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

