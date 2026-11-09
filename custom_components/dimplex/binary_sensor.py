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
from .entity import build_device_info

# Status values (see modbus_registers.py) that mean the compressor is running.
_RUNNING_STATES = (
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
)


@dataclass(frozen=True)
class DimplexBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Dimplex binary sensor entity."""

    value_fn: Callable[[dict[str, Any]], bool] | None = None
    coil_key: str | None = None
    """Coordinator data key of the coil this sensor mirrors (None = derived)."""
    requires_cooling: bool = False
    requires_pool: bool = False
    requires_second_hc: bool = False


def _heat_pump_running(data: dict[str, Any]) -> bool:
    """Prefer the compressor output coils, fall back to the status message."""
    if "compressor_1" in data or "compressor_2" in data:
        return bool(data.get("compressor_1")) or bool(data.get("compressor_2"))
    return data.get("status") in _RUNNING_STATES


def _coil(
    key: str,
    name: str,
    *,
    device_class: BinarySensorDeviceClass | None = BinarySensorDeviceClass.RUNNING,
    icon: str | None = None,
    diagnostic: bool = True,
    enabled_default: bool = True,
    requires_cooling: bool = False,
    requires_pool: bool = False,
    requires_second_hc: bool = False,
) -> DimplexBinarySensorEntityDescription:
    """Describe a binary sensor that mirrors one WPM coil."""
    return DimplexBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        name=name,
        device_class=device_class,
        icon=icon,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
        entity_registry_enabled_default=enabled_default,
        coil_key=key,
        value_fn=lambda data, _k=key: bool(data.get(_k)),
        requires_cooling=requires_cooling,
        requires_pool=requires_pool,
        requires_second_hc=requires_second_hc,
    )


BINARY_SENSOR_TYPES: tuple[DimplexBinarySensorEntityDescription, ...] = (
    # --- Derived from the system status registers --------------------------
    DimplexBinarySensorEntityDescription(
        key="error_active",
        translation_key="error_active",
        name="Error Active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.get("error_code", 0) > 0,
    ),
    DimplexBinarySensorEntityDescription(
        key="lock_active",
        translation_key="lock_active",
        name="Lock Active",
        device_class=BinarySensorDeviceClass.LOCK,
        icon="mdi:lock-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("lock_code", 0) > 0,
    ),
    DimplexBinarySensorEntityDescription(
        key="heat_pump_running",
        translation_key="heat_pump_running",
        name="Heat Pump Running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:heat-pump",
        value_fn=_heat_pump_running,
    ),
    DimplexBinarySensorEntityDescription(
        key="defrost_active",
        translation_key="defrost_active",
        name="Defrost Active",
        icon="mdi:snowflake-melt",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("status") in ("defrost", "heat_pump_on_defrost"),
    ),
    # --- Digital inputs (wiki "Eingaenge", coils 3..6) ---------------------
    _coil(
        "evu_lock",
        "Utility Lock (EVU)",
        device_class=BinarySensorDeviceClass.LOCK,
        icon="mdi:transmission-tower-off",
    ),
    _coil(
        "external_lock",
        "External Lock",
        device_class=BinarySensorDeviceClass.LOCK,
        icon="mdi:lock-outline",
    ),
    _coil(
        "smart_grid_1", "Smart Grid 1", device_class=None, icon="mdi:transmission-tower"
    ),
    _coil(
        "smart_grid_2", "Smart Grid 2", device_class=None, icon="mdi:transmission-tower"
    ),
    # --- Digital outputs (wiki "Ausgaenge", coils 41..71) ------------------
    # Verified on an LA 1422C (2026-11-09): 41-46, 49-51 match the WPM screen.
    # 48 (M21 zu) is permanently on when the HC1 mixer is not configured.
    # 59 (M14) and 60 (M17) were on although the WPM lists neither output.
    _coil("compressor_1", "Compressor 1", icon="mdi:engine", diagnostic=False),
    _coil("compressor_2", "Compressor 2", icon="mdi:engine", enabled_default=False),
    _coil("primary_pump_fan", "Primary Pump / Fan", icon="mdi:fan"),
    _coil(
        "second_heat_generator",
        "Second Heat Generator",
        icon="mdi:fire",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    _coil("heating_pump_m13", "Heating Pump (M13)", icon="mdi:pump"),
    _coil("hot_water_pump", "Hot Water Pump (M18)", icon="mdi:pump"),
    _coil(
        "aux_circ_pump",
        "Generator Circuit Pump (M16)",
        icon="mdi:pump",
    ),
    _coil(
        "flange_heater",
        "Flange Heater (E9)",
        icon="mdi:radiator",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    _coil(
        "heating_pump_m15",
        "Heating Pump HC2 (M15)",
        icon="mdi:pump",
        requires_second_hc=True,
    ),
    _coil(
        "mixer_m21_open",
        "Mixer HC1 Opening (M21)",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:valve-open",
        enabled_default=False,
    ),
    _coil(
        "mixer_m21_close",
        "Mixer HC1 Closing (M21)",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:valve-closed",
        enabled_default=False,
    ),
    _coil(
        "heating_pump_m20",
        "Heating Pump (M20)",
        icon="mdi:pump",
        enabled_default=False,
    ),
    _coil(
        "mixer_m22_open",
        "Mixer HC2 Opening (M22)",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:valve-open",
        requires_second_hc=True,
    ),
    _coil(
        "mixer_m22_close",
        "Mixer HC2 Closing (M22)",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:valve-closed",
        requires_second_hc=True,
    ),
    _coil(
        "heating_pump_m14", "Heating Pump (M14)", icon="mdi:pump", enabled_default=False
    ),
    _coil("pool_pump", "Pool Pump (M19)", icon="mdi:pool", requires_pool=True),
    _coil(
        "cooling_pump",
        "Cooling Pump (M17)",
        icon="mdi:snowflake",
        requires_cooling=True,
        enabled_default=False,
    ),
    _coil(
        "primary_pump_cooling",
        "Primary Pump Cooling (M12)",
        icon="mdi:snowflake",
        requires_cooling=True,
    ),
    _coil(
        "room_thermostat_cooling",
        "Room Thermostats Cooling Mode (N9)",
        device_class=None,
        icon="mdi:thermostat",
        requires_cooling=True,
    ),
    _coil(
        "solar_pump",
        "Solar Pump (M23)",
        icon="mdi:solar-power-variant",
        enabled_default=False,
    ),
    _coil(
        "collective_fault",
        "Collective Fault (H5)",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex binary sensor platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}

    entities = []
    for description in BINARY_SENSOR_TYPES:
        # Coil-backed sensors only exist when the coil was actually read
        # (software version J/L/M and the block read succeeded).
        if description.coil_key is not None and description.coil_key not in data:
            continue
        if description.requires_cooling and not coordinator.cooling_enabled:
            continue
        if description.requires_pool and not coordinator.pool_enabled:
            continue
        if description.requires_second_hc and not coordinator.second_hc_enabled:
            continue
        entities.append(DimplexBinarySensor(coordinator, entry, description))

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
        self._attr_device_info = build_device_info(coordinator, entry)
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

        # A coil that dropped out of the data (block read failed) is unavailable
        if desc.coil_key is not None and desc.coil_key not in data:
            return

        self._attr_is_on = desc.value_fn(data)
        self._attr_available = True

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._sync_from_coordinator()
        super()._handle_coordinator_update()
