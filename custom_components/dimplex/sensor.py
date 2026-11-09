"""Sensor platform for Dimplex integration."""

# pyright: reportArgumentType=false
# pyright: reportIncompatibleVariableOverride=false
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import UNDEFINED
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DimplexDataUpdateCoordinator
from .entity import build_device_info
from .modbus_registers import (
    ERROR_MESSAGES,
    LOCK_MESSAGES_H,
    LOCK_MESSAGES_J,
    LOCK_MESSAGES_LM,
    STATUS_MESSAGES_HJ,
    STATUS_MESSAGES_LM,
    SoftwareVersion,
)
from .modbus_registers_extended import REGISTER_DATAPOINTS, get_register_definition

# Derived datapoints and the register datapoint they depend on. A derived
# sensor is only created when its source register exists for the software
# version in use.
_COMPUTED_SENSOR_SOURCES: dict[str, str] = {
    "cop": "current_power_consumption",
    "compressor_runtime_total": "compressor_1_runtime",
    "total_heat_generated": "heating_energy",
}


def _get_all_status_options() -> list[str]:
    """Get all possible status options from all software versions."""
    options = set(STATUS_MESSAGES_LM.values())
    options.update(STATUS_MESSAGES_HJ.values())
    return sorted(options)


def _get_all_lock_options() -> list[str]:
    """Get all possible lock options from all software versions."""
    options = set(LOCK_MESSAGES_LM.values())
    options.update(LOCK_MESSAGES_J.values())
    options.update(LOCK_MESSAGES_H.values())
    return sorted(options)


def _get_all_error_options() -> list[str]:
    """Get all error identifiers (currently shared across software versions)."""
    return sorted(ERROR_MESSAGES.values())


@dataclass(frozen=True)
class DimplexSensorEntityDescription(SensorEntityDescription):
    """Describes Dimplex sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any] | None = None


def _value(key: str) -> Callable[[dict[str, Any]], Any]:
    return lambda data: data.get(key)


def _temperature(
    key: str,
    name: str,
    icon: str,
    *,
    diagnostic: bool = False,
    enabled_default: bool = True,
) -> DimplexSensorEntityDescription:
    """Describe a 0.1 degC temperature sensor."""
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        name=name,
        icon=icon,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
        entity_registry_enabled_default=enabled_default,
        value_fn=_value(key),
    )


def _runtime(key: str, name: str, icon: str) -> DimplexSensorEntityDescription:
    """Describe an hours runtime counter."""
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        name=name,
        icon=icon,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_value(key),
    )


def _energy(
    key: str, name: str, icon: str, *, precision: int = 0
) -> DimplexSensorEntityDescription:
    """Describe a kWh energy counter."""
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        name=name,
        icon=icon,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=precision,
        value_fn=_value(key),
    )


def _power(
    key: str, name: str, icon: str, *, diagnostic: bool = False
) -> DimplexSensorEntityDescription:
    """Describe a W power sensor."""
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        name=name,
        icon=icon,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
        value_fn=_value(key),
    )


# Status and diagnostic sensors (enum types)
STATUS_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    DimplexSensorEntityDescription(
        key="status",
        translation_key="status",
        name="Status",
        icon="mdi:heat-pump",
        device_class=SensorDeviceClass.ENUM,
        options=_get_all_status_options(),
        value_fn=lambda data: data.get("status", "off"),
    ),
    DimplexSensorEntityDescription(
        key="status_code",
        translation_key="status_code",
        name="Status Code",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("status_code", 0),
    ),
    DimplexSensorEntityDescription(
        key="lock",
        translation_key="lock",
        name="Lock Status",
        icon="mdi:lock",
        device_class=SensorDeviceClass.ENUM,
        options=_get_all_lock_options(),
        value_fn=lambda data: data.get("lock", "none"),
    ),
    DimplexSensorEntityDescription(
        key="lock_code",
        translation_key="lock_code",
        name="Lock Code",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("lock_code", 0),
    ),
    DimplexSensorEntityDescription(
        key="error_code",
        translation_key="error_code",
        name="Error Code",
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("error_code", 0),
    ),
    DimplexSensorEntityDescription(
        key="error",
        translation_key="error",
        name="Error",
        icon="mdi:alert-circle",
        device_class=SensorDeviceClass.ENUM,
        options=_get_all_error_options(),
        value_fn=lambda data: data.get("error", "none"),
    ),
    DimplexSensorEntityDescription(
        key="sensor_error_code",
        translation_key="sensor_error_code",
        name="Sensor Error Code",
        icon="mdi:thermometer-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("sensor_error_code"),
    ),
)


# Temperature sensors (wiki "Betriebsdaten")
TEMPERATURE_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    _temperature("flow_temperature", "Flow Temperature", "mdi:thermometer-water"),
    _temperature("return_temperature", "Return Temperature", "mdi:thermometer-water"),
    _temperature("outside_temperature", "Outside Temperature", "mdi:thermometer"),
    _temperature(
        "hot_water_temperature", "Hot Water Temperature", "mdi:water-thermometer"
    ),
    _temperature(
        "heat_source_inlet_temperature",
        "Heat Source Inlet Temperature",
        "mdi:thermometer-chevron-down",
    ),
    _temperature(
        "heat_source_outlet_temperature",
        "Heat Source Outlet Temperature",
        "mdi:thermometer-chevron-up",
    ),
    _temperature("room_temperature", "Room Temperature", "mdi:home-thermometer"),
    _temperature("room_temperature_2", "Room Temperature 2", "mdi:home-thermometer"),
    DimplexSensorEntityDescription(
        key="room_humidity",
        translation_key="room_humidity",
        name="Room Humidity",
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=_value("room_humidity"),
    ),
    DimplexSensorEntityDescription(
        key="room_humidity_2",
        translation_key="room_humidity_2",
        name="Room Humidity 2",
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=_value("room_humidity_2"),
    ),
    _temperature("return_setpoint", "Return Setpoint", "mdi:thermometer-lines"),
    _temperature(
        "hot_water_setpoint", "Hot Water Setpoint", "mdi:water-thermometer-outline"
    ),
    _temperature("hc2_setpoint", "HC2 Setpoint", "mdi:thermostat"),
    _temperature("hc2_temperature", "HC2 Temperature", "mdi:radiator"),
    _temperature("hc3_setpoint", "HC3 Setpoint", "mdi:thermostat"),
    _temperature("hc3_temperature", "HC3 Temperature", "mdi:radiator"),
    _temperature(
        "passive_cooling_flow_temperature",
        "Passive Cooling Flow Temperature",
        "mdi:snowflake-thermometer",
    ),
    _temperature(
        "passive_cooling_return_temperature",
        "Passive Cooling Return Temperature",
        "mdi:snowflake-thermometer",
    ),
    _temperature(
        "primary_circuit_return_temperature",
        "Primary Circuit Return Temperature",
        "mdi:thermometer-water",
        diagnostic=True,
    ),
    _temperature(
        "solar_storage_temperature",
        "Solar Storage Temperature",
        "mdi:solar-power-variant",
        enabled_default=False,
    ),
)


# Pressure sensors (EMPIRICAL registers 8 / 101, 0.1 bar)
PRESSURE_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    DimplexSensorEntityDescription(
        key="high_pressure",
        translation_key="high_pressure",
        name="High Pressure",
        icon="mdi:gauge-full",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=1,
        value_fn=_value("high_pressure"),
    ),
    DimplexSensorEntityDescription(
        key="low_pressure",
        translation_key="low_pressure",
        name="Low Pressure",
        icon="mdi:gauge-low",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=1,
        value_fn=_value("low_pressure"),
    ),
)


# Power and energy sensors
POWER_ENERGY_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    _power("current_power_consumption", "Current Power Consumption", "mdi:flash"),
    _power("current_heating_power", "Current Heating Power", "mdi:fire"),
    _power("pv_surplus", "PV Surplus", "mdi:solar-power", diagnostic=True),
    _energy("total_heat_generated", "Total Heat Generated", "mdi:fire-circle"),
    _energy("heating_energy", "Heating Energy", "mdi:radiator"),
    _energy("hot_water_energy", "Hot Water Energy", "mdi:water-boiler"),
    _energy("pool_energy", "Pool Energy", "mdi:pool"),
    _energy("environmental_energy", "Environmental Energy", "mdi:leaf"),
    DimplexSensorEntityDescription(
        key="cop",
        translation_key="cop",
        name="Coefficient of Performance",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_value("cop"),
    ),
)


# Runtime counters (wiki "Laufzeiten")
RUNTIME_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    _runtime("compressor_runtime_total", "Compressor Runtime Total", "mdi:timer"),
    _runtime("compressor_1_runtime", "Compressor 1 Runtime", "mdi:timer-outline"),
    _runtime("compressor_2_runtime", "Compressor 2 Runtime", "mdi:timer-outline"),
    _runtime("primary_pump_fan_runtime", "Primary Pump / Fan Runtime", "mdi:fan"),
    _runtime(
        "second_heat_generator_runtime", "Second Heat Generator Runtime", "mdi:fire"
    ),
    _runtime("heating_pump_runtime", "Heating Pump Runtime", "mdi:pump"),
    _runtime("hot_water_pump_runtime", "Hot Water Pump Runtime", "mdi:pump"),
    _runtime("immersion_heater_runtime", "Immersion Heater Runtime", "mdi:radiator"),
    _runtime("pool_pump_runtime", "Pool Pump Runtime", "mdi:pool"),
    _runtime("aux_circ_pump_runtime", "Auxiliary Circulation Pump Runtime", "mdi:pump"),
)


# Combine all sensor types
ALL_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    STATUS_SENSOR_TYPES
    + TEMPERATURE_SENSOR_TYPES
    + PRESSURE_SENSOR_TYPES
    + POWER_ENERGY_SENSOR_TYPES
    + RUNTIME_SENSOR_TYPES
)

# Sensors that only make sense when a feature is installed.
_COOLING_KEYS = {
    "passive_cooling_flow_temperature",
    "passive_cooling_return_temperature",
}
_POOL_KEYS = {"pool_energy", "pool_pump_runtime"}

# Optional probes: the WPM reports exactly 0 for sensors that are not fitted
# (observed on an LA 1422C: heat source in/out, HC3, room sensors, humidity,
# passive cooling, solar, primary circuit return all read 0). A real reading
# of exactly 0.0 on these is practically impossible, so an entity is only
# created when the first poll delivered a non-zero value.
_OPTIONAL_PROBE_KEYS = {
    "heat_source_inlet_temperature",
    "heat_source_outlet_temperature",
    "hc3_temperature",
    "room_temperature",
    "room_temperature_2",
    "room_humidity",
    "room_humidity_2",
    "passive_cooling_flow_temperature",
    "passive_cooling_return_temperature",
    "primary_circuit_return_temperature",
    "solar_storage_temperature",
}


def _supported_by_version(key: str, sw_version: Any) -> bool:
    """Return False when the datapoint can never exist for this software version."""
    if not isinstance(sw_version, SoftwareVersion):
        return True
    source_key = _COMPUTED_SENSOR_SOURCES.get(key, key)
    register_dict = REGISTER_DATAPOINTS.get(source_key)
    if register_dict is None:
        return True
    return get_register_definition(register_dict, sw_version) is not None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex sensor platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    sw_version = getattr(coordinator, "software_version", None)

    entities = []
    for description in ALL_SENSOR_TYPES:
        key = description.key

        # Skip sensors that have no data available
        if key == "sensor_error_code" and "sensor_error_code" not in coordinator.data:
            continue

        # Skip sensors that are not supported by the current software version
        # (prevents always-unavailable entities for version-specific registers).
        if not _supported_by_version(key, sw_version):
            continue

        # Skip passive cooling temperatures unless passive cooling is available
        if key in _COOLING_KEYS and not coordinator.passive_cooling_enabled:
            continue

        # Skip pool-related sensors if pool is not enabled
        if key in _POOL_KEYS and not coordinator.pool_enabled:
            continue

        # Skip probes that are not fitted (WPM reports a constant 0)
        if key in _OPTIONAL_PROBE_KEYS and not (coordinator.data or {}).get(key):
            continue

        entities.append(DimplexSensor(coordinator, entry, description))

    async_add_entities(entities)


class DimplexSensor(CoordinatorEntity[DimplexDataUpdateCoordinator], SensorEntity):
    """Representation of a Dimplex sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DimplexDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DimplexSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._description = description
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = build_device_info(coordinator, entry)
        # Use Home Assistant's naming model: entity name is the "suffix" and the
        # device name is provided via device_info (since _attr_has_entity_name=True).
        desc_name = self._description.name
        if desc_name is UNDEFINED or desc_name is None:
            self._attr_name = self._description.key.replace("_", " ").title()
        else:
            self._attr_name = cast(str, desc_name)

        # Initialize dynamic attributes once so they are correct immediately
        # (and not only after the first coordinator refresh callback).
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

        # Default state when unavailable
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
        self._attr_available = False

        if (
            not self.coordinator.last_update_success
            or data is None
            or not data.get("connected", False)
            or desc.value_fn is None
        ):
            return

        value = desc.value_fn(data)

        # For ENUM sensors, ensure value is in options list
        if (
            desc.device_class == SensorDeviceClass.ENUM
            and desc.options
            and value not in desc.options
        ):
            value = None

        self._attr_native_value = value

        # Availability rules (mirrors previous logic)
        if desc.device_class == SensorDeviceClass.ENUM or desc.key in (
            "status_code",
            "lock_code",
            "error_code",
            "sensor_error_code",
        ):
            self._attr_available = True
        else:
            self._attr_available = value is not None

        # Add raw code for enum sensors
        if desc.key in ("status", "lock", "error"):
            code_key = f"{desc.key}_code"
            if code_key in data:
                self._attr_extra_state_attributes["code"] = data[code_key]

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._sync_from_coordinator()
        super()._handle_coordinator_update()
