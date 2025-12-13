"""Switch platform for Dimplex integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DOMAIN
from .coordinator import DimplexDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


SWITCH_DESCRIPTION = SwitchEntityDescription(
    key="write_enable",
    translation_key="write_enable",
    icon="mdi:pencil-lock",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex switch platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DimplexWriteEnableSwitch(coordinator, entry)])


class DimplexWriteEnableSwitch(
    CoordinatorEntity[DimplexDataUpdateCoordinator], SwitchEntity
):
    """Switch to enable/disable write operations on the Dimplex device.

    By default, the integration operates in read-only mode for safety.
    This switch must be enabled to allow writing values to the heat pump.
    """

    _attr_has_entity_name = True
    entity_description = SWITCH_DESCRIPTION

    def __init__(
        self,
        coordinator: DimplexDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the write enable switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_write_enable"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get(CONF_NAME, "Dimplex Heat Pump"),
            "manufacturer": "Dimplex",
            "model": coordinator.model_name,
        }

    @property
    def is_on(self) -> bool:
        """Return True if write mode is enabled."""
        return self.coordinator.write_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable write mode."""
        self.coordinator.set_write_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable write mode (read-only)."""
        self.coordinator.set_write_enabled(False)
        self.async_write_ha_state()

