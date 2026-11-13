"""Number platform for Dimplex integration (writable WPM settings)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

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

from .const import DOMAIN
from .coordinator import DimplexDataUpdateCoordinator
from .entity import build_device_info
from .modbus_registers import SoftwareVersion
from .modbus_registers_extended import (
    HC2_SELECTOR_VALUE,
    HC2SettingsRegisters,
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
    requires_cooling: bool = False
    requires_second_hc: bool = False
    select_circuit: int | None = None
    """Heating circuit that must be selected in register 5082 before the
    register is valid (HC2/HC3 share one settings block)."""


NUMBER_DESCRIPTIONS: tuple[DimplexNumberDescription, ...] = (
    # --- Hot water (wiki "Einstellungen Warmwasser") -----------------------
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
    # --- Heating circuit 1 (wiki "Einstellungen 1. Heiz-/Kuehlkreis") -----
    DimplexNumberDescription(
        key="hc1_parallel_shift",
        translation_key="hc1_parallel_shift",
        data_key="hc1_parallel_shift",
        register=SettingsRegisters.HC1_PARALLEL_SHIFT,
        icon="mdi:chart-bell-curve-cumulative",
        native_unit_of_measurement="K",
        native_min_value=-19,
        native_max_value=19,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hc1_heating_curve_endpoint",
        translation_key="hc1_heating_curve_endpoint",
        data_key="hc1_heating_curve_endpoint",
        register=SettingsRegisters.HC1_HEATING_CURVE_ENDPOINT,
        icon="mdi:chart-line",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=20,
        native_max_value=70,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hc1_fixed_setpoint",
        translation_key="hc1_fixed_setpoint",
        data_key="hc1_fixed_setpoint",
        register=SettingsRegisters.HC1_FIXED_SETPOINT,
        icon="mdi:thermometer-lines",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=18,
        native_max_value=60,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    DimplexNumberDescription(
        key="hc1_hysteresis",
        translation_key="hc1_hysteresis",
        data_key="hc1_hysteresis",
        register=SettingsRegisters.HC1_HYSTERESIS,
        icon="mdi:delta",
        native_unit_of_measurement="K",
        native_min_value=0.5,
        native_max_value=5.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hc1_cooling_setpoint",
        translation_key="hc1_cooling_setpoint",
        data_key="hc1_cooling_setpoint",
        register=SettingsRegisters.HC1_COOLING_SETPOINT,
        requires_cooling=True,
        icon="mdi:snowflake-thermometer",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=35,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hc1_cooling_setpoint_30",
        translation_key="hc1_cooling_setpoint_30",
        data_key="hc1_cooling_setpoint_30",
        register=SettingsRegisters.HC1_COOLING_SETPOINT_30,
        requires_cooling=True,
        icon="mdi:snowflake-thermometer",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=35,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    # --- Heating circuit 2 (wiki "Einstellungen 2./3. Heiz-/Kuehlkreis") ---
    # Shared block behind selector register 5082 (see modbus_registers_extended).
    DimplexNumberDescription(
        key="hc2_parallel_shift",
        translation_key="hc2_parallel_shift",
        data_key="hc2_parallel_shift",
        register=HC2SettingsRegisters.PARALLEL_SHIFT,
        requires_second_hc=True,
        select_circuit=HC2_SELECTOR_VALUE,
        icon="mdi:chart-bell-curve-cumulative",
        native_unit_of_measurement="K",
        native_min_value=-19,
        native_max_value=19,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hc2_heating_curve_endpoint",
        translation_key="hc2_heating_curve_endpoint",
        data_key="hc2_heating_curve_endpoint",
        register=HC2SettingsRegisters.HEATING_CURVE_ENDPOINT,
        requires_second_hc=True,
        select_circuit=HC2_SELECTOR_VALUE,
        icon="mdi:chart-line",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=20,
        native_max_value=70,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hc2_max_temperature",
        translation_key="hc2_max_temperature",
        data_key="hc2_max_temperature",
        register=HC2SettingsRegisters.MAX_TEMPERATURE,
        requires_second_hc=True,
        select_circuit=HC2_SELECTOR_VALUE,
        icon="mdi:thermometer-high",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=70,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexNumberDescription(
        key="hc2_fixed_setpoint",
        translation_key="hc2_fixed_setpoint",
        data_key="hc2_fixed_setpoint",
        register=HC2SettingsRegisters.FIXED_SETPOINT,
        requires_second_hc=True,
        select_circuit=HC2_SELECTOR_VALUE,
        icon="mdi:thermometer-lines",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=20,
        native_max_value=60,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    DimplexNumberDescription(
        key="hc2_mixer_runtime",
        translation_key="hc2_mixer_runtime",
        data_key="hc2_mixer_runtime",
        register=HC2SettingsRegisters.MIXER_RUNTIME,
        requires_second_hc=True,
        select_circuit=HC2_SELECTOR_VALUE,
        icon="mdi:valve",
        native_unit_of_measurement="min",
        native_min_value=1,
        native_max_value=6,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    DimplexNumberDescription(
        key="hc2_mixer_hysteresis",
        translation_key="hc2_mixer_hysteresis",
        data_key="hc2_mixer_hysteresis",
        register=HC2SettingsRegisters.MIXER_HYSTERESIS,
        requires_second_hc=True,
        select_circuit=HC2_SELECTOR_VALUE,
        icon="mdi:delta",
        native_unit_of_measurement="K",
        native_min_value=0.5,
        native_max_value=2.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    DimplexNumberDescription(
        key="hc2_cooling_room_setpoint",
        translation_key="hc2_cooling_room_setpoint",
        data_key="hc2_cooling_room_setpoint",
        register=HC2SettingsRegisters.COOLING_ROOM_SETPOINT,
        requires_second_hc=True,
        requires_cooling=True,
        select_circuit=HC2_SELECTOR_VALUE,
        icon="mdi:snowflake-thermometer",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=15,
        native_max_value=30,
        native_step=0.5,
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
        if description.requires_cooling and not coordinator.cooling_enabled:
            continue
        if description.requires_second_hc and not coordinator.second_hc_enabled:
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
        self._attr_device_info = build_device_info(coordinator, entry)

    @property
    def available(self) -> bool:
        """Selector-based settings are unavailable until their block was read."""
        if not super().available:
            return False
        if self.entity_description.select_circuit is None:
            return True
        data = self.coordinator.data or {}
        return self.entity_description.data_key in data

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

        circuit = self.entity_description.select_circuit
        if (
            circuit is not None
            and not await self.coordinator.client.select_heating_circuit(
                self.coordinator.software_version, circuit
            )
        ):
            _LOGGER.error(
                "Cannot write %s: heating circuit %s could not be selected (5082)",
                self.entity_description.key,
                circuit,
            )
            return

        raw_value = self._reg_def.to_raw(value)
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
