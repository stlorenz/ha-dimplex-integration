"""The Dimplex integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_NAME,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
    OPT_COOLING_ENABLED,
    OPT_DHW_ENABLED,
    OPT_POOL_ENABLED,
    OPT_SECOND_HEATING_CIRCUIT,
    HeatPumpModel,
    get_model_capabilities,
)
from .coordinator import DimplexDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dimplex from a config entry."""
    # Get model and capabilities
    model = entry.data.get(CONF_MODEL, HeatPumpModel.GENERIC)
    model_caps = get_model_capabilities(model)

    # Build effective capabilities from model defaults + user options
    capabilities = {
        "model": model,
        "cooling_enabled": entry.options.get(
            OPT_COOLING_ENABLED, model_caps.get("cooling_default", False)
        ),
        "cooling_capable": model_caps.get("cooling_capable", False),
        "passive_cooling": model_caps.get("passive_cooling", False),
        "dhw_enabled": entry.options.get(
            OPT_DHW_ENABLED, model_caps.get("dhw_default", True)
        ),
        "pool_enabled": entry.options.get(
            OPT_POOL_ENABLED, model_caps.get("pool_default", False)
        ),
        "second_hc_enabled": entry.options.get(
            OPT_SECOND_HEATING_CIRCUIT, model_caps.get("second_hc_default", False)
        ),
        "defrost": model_caps.get("defrost", True),
        "heat_source": model_caps.get("heat_source", "unknown"),
        "max_heating_power_kw": model_caps.get("max_heating_power_kw"),
        "min_heating_power_kw": model_caps.get("min_heating_power_kw"),
    }

    coordinator = DimplexDataUpdateCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        name=entry.data.get(CONF_NAME, "Dimplex"),
        model=model,
        capabilities=capabilities,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register listener for options updates
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    return True


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Disconnect from device
    await coordinator.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

