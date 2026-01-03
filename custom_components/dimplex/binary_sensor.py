"""Binary sensor platform for Dimplex integration."""
# pyright: reportIncompatibleVariableOverride=false
# pylint: disable=unexpected-keyword-arg
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import UNDEFINED
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DimplexDataUpdateCoordinator


@dataclass(frozen=True)
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

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DimplexDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DimplexBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._description = description
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get("name", "Dimplex Heat Pump"),
            "manufacturer": "Dimplex",
            "model": coordinator.model_name,
        }
        # Use Home Assistant's naming model (see Sensor impl for details).
        desc_name = self._description.name
        if desc_name is UNDEFINED or desc_name is None:
            self._attr_name = self._description.key.replace("_", " ").title()
        else:
            self._attr_name = cast(str, desc_name)

        # Initialize dynamic attributes immediately.
        self._sync_from_coordinator()

    @property
    def available(self) -> bool:
        """Return if entity is available.

        CoordinatorEntity.available only reflects the last update success.
        For this integration we also gate availability on the coordinator's
        connection flag.
        """
        data = self.coordinator.data
        return (
            super().available
            and data is not None
            and data.get("connected", False)
            and getattr(self, "_attr_available", True)
        )

    def _sync_from_coordinator(self) -> None:
        """Sync dynamic state from coordinator into _attr_* fields."""
        desc = self._description
        data = self.coordinator.data

        self._attr_is_on = None
        self._attr_available = False

        if (
            not self.coordinator.last_update_success
            or data is None
            or not data.get("connected", False)
            or desc.value_fn is None
        ):
            return

        self._attr_is_on = desc.value_fn(data)
        self._attr_available = True

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._sync_from_coordinator()
        super()._handle_coordinator_update()

