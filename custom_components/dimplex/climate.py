"""Climate platform for Dimplex integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex climate platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DimplexClimate(coordinator, entry)])


class DimplexClimate(CoordinatorEntity, ClimateEntity):
    """Representation of a Dimplex climate device."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the climate device."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_name = entry.data.get("name", "Dimplex Climate")

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        # TODO: Return actual current temperature from coordinator
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        # TODO: Return actual target temperature from coordinator
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        # TODO: Return actual HVAC mode from coordinator
        return HVACMode.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        # TODO: Implement temperature setting
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        # TODO: Implement HVAC mode setting
        await self.coordinator.async_request_refresh()

