"""Config flow for Dimplex integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_NAME,
    CONF_PORT,
    CONF_SLAVE_ID,
    CONF_SOFTWARE_VERSION,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    MODEL_NAMES,
    OPT_BRINE_CIRCUIT,
    OPT_COOLING_ENABLED,
    OPT_DEFROST,
    OPT_DHW_ENABLED,
    OPT_HEAT_SOURCE,
    OPT_MAX_HEATING_POWER_KW,
    OPT_MIN_HEATING_POWER_KW,
    OPT_PASSIVE_COOLING,
    OPT_POOL_ENABLED,
    OPT_SECOND_HEATING_CIRCUIT,
    HeatPumpModel,
    get_model_capabilities,
)
from .modbus_client import DimplexModbusClient
from .modbus_registers import SoftwareVersion

_LOGGER = logging.getLogger(__name__)

# Build model selection options
MODEL_OPTIONS = {model: name for model, name in MODEL_NAMES.items()}

# Software version selection: stored as the IntEnum's int value in entry.data.
SOFTWARE_VERSION_OPTIONS = {
    int(SoftwareVersion.L_M): "WPM Software L / M (latest)",
    int(SoftwareVersion.J): "WPM Software J",
    int(SoftwareVersion.H): "WPM Software H",
}

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_MODEL, default=HeatPumpModel.LA1422C): vol.In(MODEL_OPTIONS),
        vol.Required(
            CONF_SOFTWARE_VERSION, default=int(SoftwareVersion.L_M)
        ): vol.In(SOFTWARE_VERSION_OPTIONS),
        vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=247)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    client = DimplexModbusClient(
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
        slave_id=data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID),
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
        """Get the options flow for this handler.

        Note: the config entry is resolved through OptionsFlow.config_entry
        (a base-class property keyed off the flow context). Do not pass it in.
        """
        return DimplexOptionsFlowHandler()

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
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            await self.async_set_unique_id(f"{host.lower()}:{port}")
            self._abort_if_unique_id_configured()

            info = await validate_input(self.hass, user_input)
        except AbortFlow:
            # Let Home Assistant handle aborts (e.g. already_configured)
            raise
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
    """Handle Dimplex options.

    HA >= 2025.12 forbids assigning ``self.config_entry`` in ``__init__`` and
    provides it as a property resolved from the flow context. We rely on the
    base-class property here.
    """

    _model: str | None = None
    _software_version: int | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """First step: Model + software version."""
        if user_input is not None:
            # Stash for the next step; do not persist until features are confirmed.
            self._model = user_input[CONF_MODEL]
            self._software_version = user_input[CONF_SOFTWARE_VERSION]
            return await self.async_step_features()

        # Prefer in-progress selection (back-button), then options override, then entry data.
        current_model = (
            self._model
            or self.config_entry.options.get(CONF_MODEL)
            or self.config_entry.data.get(CONF_MODEL, HeatPumpModel.GENERIC)
        )
        current_sw = (
            self._software_version
            if self._software_version is not None
            else self.config_entry.options.get(
                CONF_SOFTWARE_VERSION,
                self.config_entry.data.get(
                    CONF_SOFTWARE_VERSION, int(SoftwareVersion.L_M)
                ),
            )
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL, default=current_model): vol.In(
                        MODEL_OPTIONS
                    ),
                    vol.Required(
                        CONF_SOFTWARE_VERSION, default=current_sw
                    ): vol.In(SOFTWARE_VERSION_OPTIONS),
                }
            ),
        )

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Second step: Feature configuration."""
        if user_input is not None:
            options = user_input.copy()
            if self._model is not None:
                options[CONF_MODEL] = self._model
            if self._software_version is not None:
                options[CONF_SOFTWARE_VERSION] = self._software_version
            return self.async_create_entry(title="", data=options)

        # Model in scope: prefer just-picked value, else entry data.
        model = self._model or self.config_entry.data.get(
            CONF_MODEL, HeatPumpModel.GENERIC
        )
        # Get user overrides from current options
        current_options = self.config_entry.options.copy()
        user_overrides = {
            OPT_PASSIVE_COOLING: current_options.get(OPT_PASSIVE_COOLING),
            OPT_DEFROST: current_options.get(OPT_DEFROST),
            OPT_BRINE_CIRCUIT: current_options.get(OPT_BRINE_CIRCUIT),
            OPT_HEAT_SOURCE: current_options.get(OPT_HEAT_SOURCE),
            OPT_MAX_HEATING_POWER_KW: current_options.get(OPT_MAX_HEATING_POWER_KW),
            OPT_MIN_HEATING_POWER_KW: current_options.get(OPT_MIN_HEATING_POWER_KW),
        }
        capabilities = get_model_capabilities(model, user_overrides)

        # Build options schema
        schema_dict: dict[vol.Marker, Any] = {}

        # Basic feature toggles
        if capabilities.get("cooling_capable", False):
            schema_dict[
                vol.Optional(
                    OPT_COOLING_ENABLED,
                    default=current_options.get(
                        OPT_COOLING_ENABLED, capabilities.get("cooling_default", False)
                    ),
                )
            ] = bool

        if capabilities.get("dhw_capable", True):
            schema_dict[
                vol.Optional(
                    OPT_DHW_ENABLED,
                    default=current_options.get(
                        OPT_DHW_ENABLED, capabilities.get("dhw_default", True)
                    ),
                )
            ] = bool

        if capabilities.get("pool_capable", False):
            schema_dict[
                vol.Optional(
                    OPT_POOL_ENABLED,
                    default=current_options.get(
                        OPT_POOL_ENABLED, capabilities.get("pool_default", False)
                    ),
                )
            ] = bool

        if capabilities.get("second_hc_capable", False):
            schema_dict[
                vol.Optional(
                    OPT_SECOND_HEATING_CIRCUIT,
                    default=current_options.get(
                        OPT_SECOND_HEATING_CIRCUIT,
                        capabilities.get("second_hc_default", False),
                    ),
                )
            ] = bool

        # Advanced capability overrides
        schema_dict[
            vol.Optional(
                OPT_PASSIVE_COOLING,
                default=current_options.get(
                    OPT_PASSIVE_COOLING, capabilities.get("passive_cooling", False)
                ),
            )
        ] = bool

        schema_dict[
            vol.Optional(
                OPT_DEFROST,
                default=current_options.get(OPT_DEFROST, capabilities.get("defrost", True)),
            )
        ] = bool

        schema_dict[
            vol.Optional(
                OPT_BRINE_CIRCUIT,
                default=current_options.get(
                    OPT_BRINE_CIRCUIT, capabilities.get("brine_circuit", False)
                ),
            )
        ] = bool

        # Heat source selection
        heat_source_options = ["air", "brine", "water", "unknown"]
        schema_dict[
            vol.Optional(
                OPT_HEAT_SOURCE,
                default=current_options.get(
                    OPT_HEAT_SOURCE, capabilities.get("heat_source", "unknown")
                ),
            )
        ] = vol.In(heat_source_options)

        # Power limits (optional numeric values)
        max_power = current_options.get(
            OPT_MAX_HEATING_POWER_KW, capabilities.get("max_heating_power_kw")
        )
        min_power = current_options.get(
            OPT_MIN_HEATING_POWER_KW, capabilities.get("min_heating_power_kw")
        )

        schema_dict[
            vol.Optional(
                OPT_MAX_HEATING_POWER_KW,
                default=max_power,
            )
        ] = vol.Any(vol.Coerce(float), None)

        schema_dict[
            vol.Optional(
                OPT_MIN_HEATING_POWER_KW,
                default=min_power,
            )
        ] = vol.Any(vol.Coerce(float), None)

        return self.async_show_form(
            step_id="features",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "model": MODEL_NAMES.get(model, model),
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

