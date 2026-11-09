"""Climate platform for Dimplex integration (heating circuit 1)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DOMAIN
from .coordinator import DimplexDataUpdateCoordinator
from .entity import build_device_info
from .modbus_registers_extended import (
    OperatingMode,
    OperatingModeRegisters,
    SettingsRegisters,
    get_register_definition,
)

_LOGGER = logging.getLogger(__name__)

# Status messages that mean the compressor is producing heat for the house.
_HEATING_STATES = (
    "heating",
    "heat_pump_on_heating",
    "heat_pump_on_heating_auxiliary",
    "defrost",
    "heat_pump_on_defrost",
)
_DHW_STATES = (
    "hot_water",
    "heat_pump_on_hot_water",
    "heat_pump_on_hot_water_auxiliary",
)
_POOL_STATES = ("pool", "heat_pump_on_pool", "heat_pump_on_pool_auxiliary")
_COOLING_STATES = ("cooling", "passive_cooling", "cooling_mode")

# Betriebsmodus (5015) <-> HA HVAC mode. "Sommer" switches space heating off
# while domestic hot water stays active, which is the closest match to OFF.
_MODE_TO_HVAC: dict[str, HVACMode] = {
    "summer": HVACMode.OFF,
    "winter": HVACMode.HEAT,
    "vacation": HVACMode.HEAT,
    "party": HVACMode.HEAT,
    "second_heat_generator": HVACMode.HEAT,
    "cooling": HVACMode.COOL,
}
_HVAC_TO_MODE_VALUE: dict[HVACMode, int] = {
    HVACMode.OFF: int(OperatingMode.SUMMER),
    HVACMode.HEAT: int(OperatingMode.WINTER),
    HVACMode.COOL: int(OperatingMode.COOLING),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex climate platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DimplexClimate(coordinator, entry)])


class DimplexClimate(CoordinatorEntity[DimplexDataUpdateCoordinator], ClimateEntity):
    """Heating circuit 1 of a Dimplex heat pump.

    * Target temperature: register 46 "Raumtemperatur" (15.0..30.0 degC in
      0.1 degC steps, wiki "Einstellungen 1. Heiz-/Kuehlkreis"). On systems
      without a room sensor the WPM uses it as the room setpoint for the
      heating curve.
    * HVAC mode: register 5015 "Betriebsmodus" (Sommer/Winter/.../Kuehlen).
    * Current temperature: room temperature 1 if a room sensor is present,
      otherwise the return temperature.

    Both control registers are only present on WPM software J/L/M; on H the
    entity is display-only.
    """

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 15.0
    _attr_max_temp = 30.0
    _enable_turn_on_off_backwards_compat = False

    def __init__(
        self,
        coordinator: DimplexDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the climate device."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_name = entry.data.get(CONF_NAME, "Dimplex Climate")
        self._attr_device_info = build_device_info(coordinator, entry)

        if not self._has_temperature_register() or not self._has_mode_register():
            _LOGGER.info(
                "Climate control registers are not available for WPM software %s; "
                "the climate entity is display-only",
                coordinator.software_version,
            )

    # ------------------------------------------------------------------ helpers
    def _has_temperature_register(self) -> bool:
        return self._get_temperature_register() is not None

    def _has_mode_register(self) -> bool:
        return self._get_mode_register() is not None

    def _get_temperature_register(self) -> int | None:
        reg_def = get_register_definition(
            SettingsRegisters.HC1_ROOM_SETPOINT, self.coordinator.software_version
        )
        return reg_def.address if reg_def else None

    def _get_mode_register(self) -> int | None:
        return OperatingModeRegisters.CURRENT_MODE.get(
            self.coordinator.software_version
        )

    # --------------------------------------------------------------- properties
    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Only advertise control features whose registers exist."""
        features = ClimateEntityFeature(0)
        if self._has_temperature_register():
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if self._has_mode_register():
            features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        return features

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the selectable HVAC modes."""
        if not self._has_mode_register():
            # Display-only: show what we observe, nothing selectable.
            return [self.hvac_mode]

        modes = [HVACMode.OFF, HVACMode.HEAT]
        if self.coordinator.cooling_enabled:
            modes.append(HVACMode.COOL)
        return modes

    @property
    def current_temperature(self) -> float | None:
        """Return room temperature 1, falling back to the return temperature."""
        data = self.coordinator.data
        if not data:
            return None
        # The WPM reports exactly 0 when no room sensor is connected.
        temp = data.get("room_temperature")
        if not temp:
            temp = data.get("return_temperature")
        return temp

    @property
    def target_temperature(self) -> float | None:
        """Return the room setpoint of heating circuit 1."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("hc1_room_setpoint")

    @property
    def hvac_mode(self) -> HVACMode:
        """Derive the HVAC mode from the Betriebsmodus, else from the status."""
        data = self.coordinator.data
        if not data:
            return HVACMode.OFF

        mode = data.get("operating_mode")
        if mode in _MODE_TO_HVAC:
            return _MODE_TO_HVAC[mode]

        status = data.get("status", "off")
        if status in _COOLING_STATES:
            return HVACMode.COOL
        if status in _HEATING_STATES + _DHW_STATES + _POOL_STATES:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return what the heat pump is doing right now."""
        data = self.coordinator.data
        if not data:
            return None

        status = data.get("status", "off")
        if status == "off":
            return HVACAction.OFF
        if status in _COOLING_STATES:
            return HVACAction.COOLING
        if status in _HEATING_STATES or status in _DHW_STATES or status in _POOL_STATES:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.get("connected", False)
        )

    # ----------------------------------------------------------------- commands
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Write the room setpoint (register 46, 0.1 degC)."""
        register_address = self._get_temperature_register()
        if register_address is None:
            _LOGGER.warning(
                "Cannot set temperature: no setpoint register for WPM software %s",
                self.coordinator.software_version,
            )
            return

        if not self.coordinator.write_enabled:
            _LOGGER.warning(
                "Cannot set temperature: write mode is disabled. "
                "Enable the 'Write Enable' switch to allow changes."
            )
            return

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        temperature = min(
            max(float(temperature), self._attr_min_temp), self._attr_max_temp
        )

        reg_def = get_register_definition(
            SettingsRegisters.HC1_ROOM_SETPOINT, self.coordinator.software_version
        )
        assert reg_def is not None
        raw_value = reg_def.to_raw(temperature)

        success = await self.coordinator.client.write_register(
            address=register_address,
            value=raw_value,
        )
        if not success:
            _LOGGER.error("Failed to set temperature to %.1f°C", temperature)
            return

        _LOGGER.debug(
            "Set temperature to %.1f°C (raw value: %d)", temperature, raw_value
        )
        if self.coordinator.data is not None:
            self.coordinator.data["hc1_room_setpoint"] = temperature
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Write the Betriebsmodus (register 5015)."""
        register_address = self._get_mode_register()
        if register_address is None:
            _LOGGER.warning(
                "Cannot set HVAC mode: no Betriebsmodus register for WPM software %s",
                self.coordinator.software_version,
            )
            return

        if not self.coordinator.write_enabled:
            _LOGGER.warning(
                "Cannot set HVAC mode: write mode is disabled. "
                "Enable the 'Write Enable' switch to allow changes."
            )
            return

        if hvac_mode == HVACMode.COOL and not self.coordinator.cooling_enabled:
            _LOGGER.warning(
                "Cannot set cooling mode: cooling is not installed in this system. "
                "Configure cooling in integration options if it has been installed."
            )
            return

        mode_value = _HVAC_TO_MODE_VALUE.get(hvac_mode)
        if mode_value is None:
            _LOGGER.warning("Unsupported HVAC mode %s", hvac_mode)
            return

        success = await self.coordinator.client.write_register(
            address=register_address,
            value=mode_value,
        )
        if not success:
            _LOGGER.error("Failed to set HVAC mode to %s", hvac_mode)
            return

        _LOGGER.debug("Set HVAC mode to %s (Betriebsmodus %d)", hvac_mode, mode_value)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Switch heating circuit 1 to Winter."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Switch heating circuit 1 to Sommer (heating off, DHW continues)."""
        await self.async_set_hvac_mode(HVACMode.OFF)
