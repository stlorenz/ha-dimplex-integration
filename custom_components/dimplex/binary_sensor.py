"""Binary sensor platform for Dimplex integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DimplexDataUpdateCoordinator


@dataclass
class DimplexBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Dimplex binary sensor entity."""

    value_fn: Callable[[dict[str, Any]], bool] | None = None


BINARY_SENSOR_TYPES: tuple[DimplexBinarySensorEntityDescription, ...] = (
    DimplexBinarySensorEntityDescription(
        key="error_active",
        name="Error Active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.get("error_code", 0) > 0,
    ),
    DimplexBinarySensorEntityDescription(
        key="lock_active",
        name="Lock Active",
        device_class=BinarySensorDeviceClass.LOCK,
        icon="mdi:lock-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("lock_code", 0) > 0,
    ),
    DimplexBinarySensorEntityDescription(
        key="heat_pump_running",
        name="Heat Pump Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:heat-pump",
        value_fn=lambda data: data.get("status") in (
            "heating",
            "pool",
            "hot_water",
            "cooling",
            "heat_pump_on_heating",
            "heat_pump_on_pool",
            "heat_pump_on_hot_water",
            "heat_pump_on_heating_auxiliary",
            "heat_pump_on_pool_auxiliary",
            "heat_pump_on_hot_water_auxiliary",
            "heat_pump_on_defrost",
        ),
    ),
    DimplexBinarySensorEntityDescription(
        key="defrost_active",
        name="Defrost Active",
        icon="mdi:snowflake-melt",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("status") in ("defrost", "heat_pump_on_defrost"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex binary sensor platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        DimplexBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_TYPES
    ]

    async_add_entities(entities)


class DimplexBinarySensor(
    CoordinatorEntity[DimplexDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Dimplex binary sensor."""

    entity_description: DimplexBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: DimplexDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DimplexBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get("name", "Dimplex Heat Pump"),
            "manufacturer": "Dimplex",
            "model": coordinator.model_name,
        }

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        # Get device name from coordinator data or entry data
        if self.coordinator.data:
            device_name = self.coordinator.data.get("name")
        else:
            device_name = None
        if not device_name:
            device_name = self._entry.data.get("name", "Dimplex")
        
        # Get entity name from translation or description
        entity_name = self.entity_description.name or self.entity_description.key.replace("_", " ").title()
        return f"{device_name} {entity_name}"

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        if self.entity_description.value_fn is None:
            return None
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.get("connected", False)
            and self.entity_description.value_fn is not None
        )

