"""Sensor platform for Dimplex integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DimplexDataUpdateCoordinator
from .modbus_registers import (
    LOCK_TRANSLATIONS_EN,
    STATUS_TRANSLATIONS_EN,
)


@dataclass
class DimplexSensorEntityDescription(SensorEntityDescription):
    """Describes Dimplex sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any] | None = None
    translation_dict: dict[str, str] | None = None


SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    DimplexSensorEntityDescription(
        key="status",
        name="Status",
        icon="mdi:heat-pump",
        device_class=SensorDeviceClass.ENUM,
        options=list(STATUS_TRANSLATIONS_EN.keys()),
        translation_dict=STATUS_TRANSLATIONS_EN,
        value_fn=lambda data: data.get("status", "off"),
    ),
    DimplexSensorEntityDescription(
        key="status_code",
        name="Status Code",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("status_code", 0),
    ),
    DimplexSensorEntityDescription(
        key="lock",
        name="Lock Status",
        icon="mdi:lock",
        device_class=SensorDeviceClass.ENUM,
        options=list(LOCK_TRANSLATIONS_EN.keys()),
        translation_dict=LOCK_TRANSLATIONS_EN,
        value_fn=lambda data: data.get("lock", "none"),
    ),
    DimplexSensorEntityDescription(
        key="lock_code",
        name="Lock Code",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("lock_code", 0),
    ),
    DimplexSensorEntityDescription(
        key="error_code",
        name="Error Code",
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("error_code", 0),
    ),
    DimplexSensorEntityDescription(
        key="sensor_error_code",
        name="Sensor Error Code",
        icon="mdi:thermometer-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("sensor_error_code"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex sensor platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for description in SENSOR_TYPES:
        # Skip sensor error code for software versions that don't support it
        if description.key == "sensor_error_code" and "sensor_error_code" not in coordinator.data:
            continue

        entities.append(DimplexSensor(coordinator, entry, description))

    async_add_entities(entities)


class DimplexSensor(CoordinatorEntity[DimplexDataUpdateCoordinator], SensorEntity):
    """Representation of a Dimplex sensor."""

    entity_description: DimplexSensorEntityDescription

    def __init__(
        self,
        coordinator: DimplexDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DimplexSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get("name", "Dimplex Heat Pump"),
            "manufacturer": "Dimplex",
            "model": "Heat Pump",
        }

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        # Try to get device name from coordinator data, fallback to device_info
        device_name = self.coordinator.data.get("name")
        if not device_name and self._attr_device_info:
            device_name = self._attr_device_info.get("name", "Dimplex")
        return f"{device_name} {self.entity_description.name}"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.entity_description.value_fn:
            value = self.entity_description.value_fn(self.coordinator.data)

            # Skip None values
            if value is None:
                return None

            # For enum sensors, return the translated value
            if (
                self.entity_description.device_class == SensorDeviceClass.ENUM
                and self.entity_description.translation_dict
            ):
                return self.entity_description.translation_dict.get(
                    str(value), str(value)
                )

            return value

        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data.get("connected", False)
            and self.entity_description.value_fn is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}

        # Add raw code for translated sensors
        if self.entity_description.key in ("status", "lock"):
            code_key = f"{self.entity_description.key}_code"
            if code_key in self.coordinator.data:
                attrs["code"] = self.coordinator.data[code_key]

        return attrs

