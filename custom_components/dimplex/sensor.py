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
from .modbus_registers import SoftwareVersion
from .modbus_registers_extended import EnergyRegisters, get_register_definition
from .modbus_registers import (
    LOCK_MESSAGES_LM,
    STATUS_MESSAGES_LM,
    STATUS_MESSAGES_HJ,
    LOCK_MESSAGES_J,
    LOCK_MESSAGES_H,
)

_VERSION_DEPENDENT_SENSOR_REGISTERS: dict[str, dict[SoftwareVersion, Any]] = {
    # Power / energy datapoints depend on software version mappings (some are None on H).
    "current_power_consumption": EnergyRegisters.CURRENT_POWER_CONSUMPTION,
    "current_heating_power": EnergyRegisters.CURRENT_HEATING_POWER,
    "pv_surplus": EnergyRegisters.PV_SURPLUS,
    "total_energy_consumed": EnergyRegisters.TOTAL_ENERGY_CONSUMED,
    "total_heat_generated": EnergyRegisters.TOTAL_HEAT_GENERATED,
    "heating_energy": EnergyRegisters.HEATING_ENERGY,
    "hot_water_energy": EnergyRegisters.HOT_WATER_ENERGY,
    "cooling_energy": EnergyRegisters.COOLING_ENERGY,
    "pool_energy": EnergyRegisters.POOL_ENERGY,
    "environmental_energy": EnergyRegisters.ENVIRONMENTAL_ENERGY,
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


@dataclass(frozen=True)
class DimplexSensorEntityDescription(SensorEntityDescription):
    """Describes Dimplex sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any] | None = None


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
        key="sensor_error_code",
        translation_key="sensor_error_code",
        name="Sensor Error Code",
        icon="mdi:thermometer-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("sensor_error_code"),
    ),
)


# Temperature sensors - HA compliant for InfluxDB/Grafana
TEMPERATURE_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    DimplexSensorEntityDescription(
        key="flow_temperature",
        translation_key="flow_temperature",
        name="Flow Temperature",
        icon="mdi:thermometer-water",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("flow_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="return_temperature",
        translation_key="return_temperature",
        name="Return Temperature",
        icon="mdi:thermometer-water",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("return_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="outside_temperature",
        translation_key="outside_temperature",
        name="Outside Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("outside_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="hot_water_temperature",
        translation_key="hot_water_temperature",
        name="Hot Water Temperature",
        icon="mdi:water-thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("hot_water_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="heat_source_inlet_temperature",
        translation_key="heat_source_inlet_temperature",
        name="Heat Source Inlet Temperature",
        icon="mdi:thermometer-chevron-down",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("heat_source_inlet_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="heat_source_outlet_temperature",
        translation_key="heat_source_outlet_temperature",
        name="Heat Source Outlet Temperature",
        icon="mdi:thermometer-chevron-up",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("heat_source_outlet_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="room_temperature",
        translation_key="room_temperature",
        name="Room Temperature",
        icon="mdi:home-thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("room_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="flow_setpoint",
        translation_key="flow_setpoint",
        name="Flow Setpoint",
        icon="mdi:thermometer-lines",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("flow_setpoint"),
    ),
    DimplexSensorEntityDescription(
        key="hot_water_setpoint",
        translation_key="hot_water_setpoint",
        name="Hot Water Setpoint",
        icon="mdi:water-thermometer-outline",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("hot_water_setpoint"),
    ),
    DimplexSensorEntityDescription(
        key="evaporator_temperature",
        translation_key="evaporator_temperature",
        name="Evaporator Temperature",
        icon="mdi:snowflake-thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("evaporator_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="condenser_temperature",
        translation_key="condenser_temperature",
        name="Condenser Temperature",
        icon="mdi:radiator",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("condenser_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="suction_gas_temperature",
        translation_key="suction_gas_temperature",
        name="Suction Gas Temperature",
        icon="mdi:gas-cylinder",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("suction_gas_temperature"),
    ),
    DimplexSensorEntityDescription(
        key="discharge_gas_temperature",
        translation_key="discharge_gas_temperature",
        name="Discharge Gas Temperature",
        icon="mdi:gas-cylinder",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("discharge_gas_temperature"),
    ),
)


# Pressure sensors - HA compliant for InfluxDB/Grafana
# Using bar as unit (standard in HVAC) - HA will convert as needed
PRESSURE_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    DimplexSensorEntityDescription(
        key="high_pressure",
        translation_key="high_pressure",
        name="High Pressure",
        icon="mdi:gauge-full",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("high_pressure"),
    ),
    DimplexSensorEntityDescription(
        key="low_pressure",
        translation_key="low_pressure",
        name="Low Pressure",
        icon="mdi:gauge-low",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("low_pressure"),
    ),
    DimplexSensorEntityDescription(
        key="brine_pressure",
        translation_key="brine_pressure",
        name="Brine Pressure",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("brine_pressure"),
    ),
    DimplexSensorEntityDescription(
        key="water_pressure",
        translation_key="water_pressure",
        name="Water Pressure",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("water_pressure"),
    ),
)


# Power and energy sensors - HA compliant for InfluxDB/Grafana
POWER_ENERGY_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    DimplexSensorEntityDescription(
        key="current_power_consumption",
        translation_key="current_power_consumption",
        name="Current Power Consumption",
        icon="mdi:flash",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("current_power_consumption"),
    ),
    DimplexSensorEntityDescription(
        key="current_heating_power",
        translation_key="current_heating_power",
        name="Current Heating Power",
        icon="mdi:fire",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("current_heating_power"),
    ),
    DimplexSensorEntityDescription(
        key="pv_surplus",
        translation_key="pv_surplus",
        name="PV Surplus",
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("pv_surplus"),
    ),
    DimplexSensorEntityDescription(
        key="total_energy_consumed",
        translation_key="total_energy_consumed",
        name="Total Energy Consumed",
        icon="mdi:lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("total_energy_consumed"),
    ),
    DimplexSensorEntityDescription(
        key="total_heat_generated",
        translation_key="total_heat_generated",
        name="Total Heat Generated",
        icon="mdi:fire-circle",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("total_heat_generated"),
    ),
    DimplexSensorEntityDescription(
        key="heating_energy",
        translation_key="heating_energy",
        name="Heating Energy",
        icon="mdi:radiator",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("heating_energy"),
    ),
    DimplexSensorEntityDescription(
        key="hot_water_energy",
        translation_key="hot_water_energy",
        name="Hot Water Energy",
        icon="mdi:water-boiler",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("hot_water_energy"),
    ),
    DimplexSensorEntityDescription(
        key="cooling_energy",
        translation_key="cooling_energy",
        name="Cooling Energy",
        icon="mdi:snowflake",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("cooling_energy"),
    ),
    DimplexSensorEntityDescription(
        key="pool_energy",
        translation_key="pool_energy",
        name="Pool Energy",
        icon="mdi:pool",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("pool_energy"),
    ),
    DimplexSensorEntityDescription(
        key="environmental_energy",
        translation_key="environmental_energy",
        name="Environmental Energy",
        icon="mdi:leaf",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("environmental_energy"),
    ),
    DimplexSensorEntityDescription(
        key="cop",
        translation_key="cop",
        name="Coefficient of Performance",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("cop"),
    ),
)


# Runtime and counter sensors - HA compliant for InfluxDB/Grafana
RUNTIME_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    DimplexSensorEntityDescription(
        key="compressor_runtime_total",
        translation_key="compressor_runtime_total",
        name="Compressor Runtime Total",
        icon="mdi:timer",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("compressor_runtime_total"),
    ),
    DimplexSensorEntityDescription(
        key="compressor_starts",
        translation_key="compressor_starts",
        name="Compressor Starts",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("compressor_starts"),
    ),
    DimplexSensorEntityDescription(
        key="heating_runtime",
        translation_key="heating_runtime",
        name="Heating Runtime",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("heating_runtime"),
    ),
    DimplexSensorEntityDescription(
        key="hot_water_runtime",
        translation_key="hot_water_runtime",
        name="Hot Water Runtime",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("hot_water_runtime"),
    ),
    DimplexSensorEntityDescription(
        key="cooling_runtime",
        translation_key="cooling_runtime",
        name="Cooling Runtime",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("cooling_runtime"),
    ),
    DimplexSensorEntityDescription(
        key="auxiliary_heater_runtime",
        translation_key="auxiliary_heater_runtime",
        name="Auxiliary Heater Runtime",
        icon="mdi:timer-alert-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("auxiliary_heater_runtime"),
    ),
    DimplexSensorEntityDescription(
        key="defrost_cycles",
        translation_key="defrost_cycles",
        name="Defrost Cycles",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("defrost_cycles"),
    ),
)


# Combine all sensor types
ALL_SENSOR_TYPES: tuple[DimplexSensorEntityDescription, ...] = (
    STATUS_SENSOR_TYPES
    + TEMPERATURE_SENSOR_TYPES
    + PRESSURE_SENSOR_TYPES
    + POWER_ENERGY_SENSOR_TYPES
    + RUNTIME_SENSOR_TYPES
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex sensor platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for description in ALL_SENSOR_TYPES:
        # Skip sensors that have no data available
        if description.key == "sensor_error_code" and "sensor_error_code" not in coordinator.data:
            continue

        # Skip sensors that are not supported by the current software version
        # (prevents always-unavailable entities for version-specific registers).
        sw_version = getattr(coordinator, "software_version", None)
        register_dict = _VERSION_DEPENDENT_SENSOR_REGISTERS.get(description.key)
        if (
            register_dict is not None
            and isinstance(sw_version, SoftwareVersion)
            and get_register_definition(register_dict, sw_version) is None
        ):
            continue

        # Skip cooling-related sensors if cooling is not enabled
        if description.key in ("cooling_energy", "cooling_runtime") and not coordinator.cooling_enabled:
            continue

        # Skip pool-related sensors if pool is not enabled
        if description.key == "pool_energy" and not coordinator.pool_enabled:
            continue

        # Skip brine pressure if not a brine system
        if description.key == "brine_pressure" and coordinator.heat_source != "brine":
            continue

        # Skip defrost cycles if no defrost capability
        if description.key == "defrost_cycles" and not coordinator.has_defrost:
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
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get("name", "Dimplex Heat Pump"),
            "manufacturer": "Dimplex",
            "model": coordinator.model_name,
        }
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
        if desc.device_class == SensorDeviceClass.ENUM:
            self._attr_available = True
        elif desc.key in (
            "status_code",
            "lock_code",
            "error_code",
            "sensor_error_code",
        ):
            self._attr_available = True
        else:
            self._attr_available = value is not None

        # Add raw code for enum sensors
        if desc.key in ("status", "lock"):
            code_key = f"{desc.key}_code"
            if code_key in data:
                self._attr_extra_state_attributes["code"] = data[code_key]

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._sync_from_coordinator()
        super()._handle_coordinator_update()
