"""Select platform for Dimplex integration (operating mode / Betriebsmodus)."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DimplexDataUpdateCoordinator
from .entity import build_device_info
from .modbus_registers_extended import OPERATING_MODE_KEYS, OperatingModeRegisters

_LOGGER = logging.getLogger(__name__)

OPERATING_MODE_DESCRIPTION = SelectEntityDescription(
    key="operating_mode",
    translation_key="operating_mode",
    name="Operating Mode",
    icon="mdi:sun-snowflake-variant",
    entity_category=EntityCategory.CONFIG,
    options=list(OPERATING_MODE_KEYS.values()),
)

_KEY_TO_VALUE: dict[str, int] = {
    name: int(code) for code, name in OPERATING_MODE_KEYS.items()
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex select platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    address = OperatingModeRegisters.CURRENT_MODE.get(coordinator.software_version)
    if address is None:
        _LOGGER.debug(
            "Skipping operating mode select: register 5015 not available for software version %s",
            coordinator.software_version,
        )
        return

    async_add_entities([DimplexOperatingModeSelect(coordinator, entry, address)])


class DimplexOperatingModeSelect(
    CoordinatorEntity[DimplexDataUpdateCoordinator], SelectEntity
):
    """Betriebsmodus (register 5015): Sommer/Winter/Urlaub/Party/2. WE/Kuehlen."""

    _attr_has_entity_name = True
    entity_description = OPERATING_MODE_DESCRIPTION

    def __init__(
        self,
        coordinator: DimplexDataUpdateCoordinator,
        entry: ConfigEntry,
        address: int,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._address = address
        self._attr_unique_id = f"{entry.entry_id}_operating_mode"
        self._attr_device_info = build_device_info(coordinator, entry)

    @property
    def options(self) -> list[str]:
        """Return the selectable modes (cooling only when installed)."""
        options = list(OPERATING_MODE_KEYS.values())
        if not self.coordinator.cooling_enabled:
            options.remove("cooling")
        return options

    @property
    def current_option(self) -> str | None:
        """Return the mode reported by the device."""
        if self.coordinator.data is None:
            return None
        mode = self.coordinator.data.get("operating_mode")
        return mode if mode in OPERATING_MODE_KEYS.values() else None

    async def async_select_option(self, option: str) -> None:
        """Write the selected mode to register 5015."""
        if not self.coordinator.write_enabled:
            _LOGGER.warning(
                "Cannot set operating mode: write mode is disabled. "
                "Enable the 'Write Enable' switch to allow changes."
            )
            return

        value = _KEY_TO_VALUE.get(option)
        if value is None:
            _LOGGER.error("Unknown operating mode %r", option)
            return

        success = await self.coordinator.client.write_register(
            address=self._address, value=value
        )
        if not success:
            _LOGGER.error("Failed to write operating mode %s (%d)", option, value)
            return

        if self.coordinator.data is not None:
            self.coordinator.data["operating_mode"] = option
            self.coordinator.data["operating_mode_code"] = value
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
