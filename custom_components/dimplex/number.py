"""Number platform for Dimplex integration (writable hot water settings)."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DOMAIN
from .coordinator import DimplexDataUpdateCoordinator
from .modbus_registers import SoftwareVersion
from .modbus_registers_extended import (
    RegisterDefinition,
    SettingsRegisters,
    get_register_definition,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class DimplexNumberDescription(NumberEntityDescription):
    """Describe a writable Dimplex setting backed by a holding register."""

    register: dict[SoftwareVersion, RegisterDefinition]
    data_key: str
    requires_dhw: bool = False


NUMBER_DESCRIPTIONS: tuple[DimplexNumberDescription, ...] = (
    DimplexNumberDescription(
        key="hot_water_setpoint_setting",
        translation_key="hot_water_setpoint_setting",
        data_key="hot_water_setpoint_setting",
        register=SettingsRegisters.HOT_WATER_COMFORT_SETPOINT,
        requires_dhw=True,
        icon="mdi:water-thermometer",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=70,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hot_water_max_setpoint",
        translation_key="hot_water_max_setpoint",
        data_key="hot_water_max_setpoint",
        register=SettingsRegisters.HOT_WATER_MAX_SETPOINT,
        requires_dhw=True,
        icon="mdi:thermometer-high",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=85,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hot_water_min_setpoint",
        translation_key="hot_water_min_setpoint",
        data_key="hot_water_min_setpoint",
        register=SettingsRegisters.HOT_WATER_MIN_SETPOINT,
        requires_dhw=True,
        icon="mdi:thermometer-low",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=60,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hot_water_hysteresis",
        translation_key="hot_water_hysteresis",
        data_key="hot_water_hysteresis",
        register=SettingsRegisters.HOT_WATER_HYSTERESIS,
        requires_dhw=True,
        icon="mdi:delta",
        native_unit_of_measurement="K",
        native_min_value=2,
        native_max_value=15,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex number platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[DimplexNumber] = []
    for description in NUMBER_DESCRIPTIONS:
        if description.requires_dhw and not coordinator.dhw_enabled:
            continue
        reg_def = get_register_definition(
            description.register, coordinator.software_version
        )
        if reg_def is None:
            _LOGGER.debug(
                "Skipping number %s: register not available for software version %s",
                description.key,
                coordinator.software_version,
            )
            continue
        entities.append(DimplexNumber(coordinator, entry, description, reg_def))

    async_add_entities(entities)


class DimplexNumber(CoordinatorEntity[DimplexDataUpdateCoordinator], NumberEntity):
    """A writable Dimplex setting (Modbus holding register)."""

    _attr_has_entity_name = True
    entity_description: DimplexNumberDescription

    def __init__(
        self,
        coordinator: DimplexDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DimplexNumberDescription,
        reg_def: RegisterDefinition,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._reg_def = reg_def
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get(CONF_NAME, "Dimplex Heat Pump"),
            "manufacturer": "Dimplex",
            "model": coordinator.model_name,
        }

    @property
    def native_value(self) -> float | None:
        """Return the current value read from the device."""
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self.entity_description.data_key)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Write the value to the device."""
        if not self.coordinator.write_enabled:
            _LOGGER.warning(
                "Cannot set %s: write mode is disabled. "
                "Enable the 'Write Enable' switch to allow changes.",
                self.entity_description.key,
            )
            return

        if self._reg_def.address is None:
            return

        raw_value = int(round(value / self._reg_def.scale))
        success = await self.coordinator.client.write_register(
            address=self._reg_def.address,
            value=raw_value,
        )
        if not success:
            _LOGGER.error(
                "Failed to write %s=%s to register %s",
                self.entity_description.key,
                value,
                self._reg_def.address,
            )
            return

        _LOGGER.debug(
            "Wrote %s=%s (raw %s) to register %s",
            self.entity_description.key,
            value,
            raw_value,
            self._reg_def.address,
        )
        # The WPM applies the value with a short delay; optimistic update
        # keeps the UI responsive until the next poll confirms it.
        if self.coordinator.data is not None:
            self.coordinator.data[self.entity_description.data_key] = value
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
