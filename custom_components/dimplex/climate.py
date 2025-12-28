"""Climate platform for Dimplex integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DOMAIN
from .coordinator import DimplexDataUpdateCoordinator
from .modbus_registers_extended import (
    OperatingModeRegisters,
    SettingsRegisters,
    get_register_definition,
)

_LOGGER = logging.getLogger(__name__)

# Log once at module load if registers are not configured
_REGISTERS_WARNING_LOGGED = False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dimplex climate platform."""
    coordinator: DimplexDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DimplexClimate(coordinator, entry)])


class DimplexClimate(CoordinatorEntity[DimplexDataUpdateCoordinator], ClimateEntity):
    """Representation of a Dimplex climate device.
    
    Note: This climate entity is currently READ-ONLY for monitoring purposes.
    Temperature and HVAC mode control require Modbus register addresses to be
    configured in modbus_registers_extended.py. Until then, only status display
    is functional.
    """

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 10.0
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
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get(CONF_NAME, "Dimplex Heat Pump"),
            "manufacturer": "Dimplex",
            "model": coordinator.model_name,
        }
        
        # Log warning about unconfigured registers (once per setup)
        global _REGISTERS_WARNING_LOGGED
        if not _REGISTERS_WARNING_LOGGED:
            if not self._has_temperature_register():
                _LOGGER.warning(
                    "Temperature setpoint register not configured for software version %s. "
                    "Temperature control will be disabled. See modbus_registers_extended.py",
                    coordinator.software_version,
                )
            if not self._has_mode_register():
                _LOGGER.warning(
                    "Operating mode register not configured for software version %s. "
                    "HVAC mode control will be disabled. See modbus_registers_extended.py",
                    coordinator.software_version,
                )
            _REGISTERS_WARNING_LOGGED = True

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return supported features based on configured registers.
        
        Only enable control features if the corresponding Modbus registers
        are actually configured. This prevents the UI from showing controls
        that don't work.
        """
        features = ClimateEntityFeature(0)
        
        # Only enable temperature control if register is configured
        if self._has_temperature_register():
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        
        # Only enable on/off control if mode register is configured
        if self._has_mode_register():
            features |= ClimateEntityFeature.TURN_OFF
            features |= ClimateEntityFeature.TURN_ON
        
        return features

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available HVAC modes based on device capabilities.
        
        Only shows controllable modes if the mode register is configured.
        """
        # If mode register isn't configured, we can only show what we observe
        # but can't actually control it
        if not self._has_mode_register():
            # Return current mode only - no control available
            current = self.hvac_mode
            return [current] if current else [HVACMode.OFF]
        
        modes = [HVACMode.OFF, HVACMode.HEAT]
        
        # Only add cooling mode if it's enabled in this installation
        if self.coordinator.cooling_enabled:
            modes.append(HVACMode.COOL)
        
        return modes
    
    def _has_temperature_register(self) -> bool:
        """Check if temperature setpoint register is configured."""
        reg_def = get_register_definition(
            SettingsRegisters.HC1_COMFORT_SETPOINT,
            self.coordinator.software_version
        )
        return reg_def is not None and reg_def.address is not None
    
    def _has_mode_register(self) -> bool:
        """Check if operating mode register is configured."""
        mode_addr = OperatingModeRegisters.CURRENT_MODE.get(
            self.coordinator.software_version
        )
        return mode_addr is not None

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if not self.coordinator.data:
            return None
        # Use room temperature if available, fallback to flow temperature
        temp = self.coordinator.data.get("room_temperature")
        if temp is None:
            temp = self.coordinator.data.get("flow_temperature")
        return temp

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("target_temperature")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode based on device status."""
        if not self.coordinator.data:
            return HVACMode.OFF

        status = self.coordinator.data.get("status", "off")

        # Map device status to HVAC mode
        if status in ("cooling", "passive_cooling", "cooling_mode"):
            return HVACMode.COOL
        if status in (
            "heating",
            "heat_pump_on_heating",
            "heat_pump_on_heating_auxiliary",
            "hot_water",
            "heat_pump_on_hot_water",
            "heat_pump_on_hot_water_auxiliary",
            "pool",
            "heat_pump_on_pool",
            "heat_pump_on_pool_auxiliary",
            "defrost",
            "heat_pump_on_defrost",
        ):
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> str | None:
        """Return the current running HVAC action."""
        if not self.coordinator.data:
            return None

        status = self.coordinator.data.get("status", "off")

        if status == "off":
            return "off"
        if status in ("cooling", "passive_cooling", "cooling_mode"):
            return "cooling"
        if status in (
            "heating",
            "heat_pump_on_heating",
            "heat_pump_on_heating_auxiliary",
            "defrost",
            "heat_pump_on_defrost",
        ):
            return "heating"
        if status in ("hot_water", "heat_pump_on_hot_water", "heat_pump_on_hot_water_auxiliary"):
            return "heating"  # DHW heating
        return "idle"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.get("connected", False)
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        # Check if register is configured
        if not self._has_temperature_register():
            _LOGGER.error(
                "Cannot set temperature: register not configured. "
                "This is a development issue - see modbus_registers_extended.py"
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

        register_address = self._get_temperature_register()
        # Already checked above, but satisfy type checker
        if register_address is None:
            return

        # Write temperature to device via Modbus
        # Temperature values are typically stored in 0.1°C units
        raw_value = int(temperature * 10)
        success = await self.coordinator.client.write_register(
            address=register_address,
            value=raw_value,
        )

        if success:
            _LOGGER.debug("Set temperature to %.1f°C (raw value: %d)", temperature, raw_value)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set temperature to %.1f°C", temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        # Check if register is configured
        if not self._has_mode_register():
            _LOGGER.error(
                "Cannot set HVAC mode: register not configured. "
                "This is a development issue - see modbus_registers_extended.py"
            )
            return
            
        if not self.coordinator.write_enabled:
            _LOGGER.warning(
                "Cannot set HVAC mode: write mode is disabled. "
                "Enable the 'Write Enable' switch to allow changes."
            )
            return

        # Prevent setting cooling mode if cooling is not installed
        if hvac_mode == HVACMode.COOL and not self.coordinator.cooling_enabled:
            _LOGGER.warning(
                "Cannot set cooling mode: cooling is not installed in this system. "
                "Configure cooling in integration options if it has been installed."
            )
            return

        register_address = self._get_mode_register()
        # Already checked above, but satisfy type checker
        if register_address is None:
            return

        # Map HVAC mode to device operating mode
        mode_map = {
            HVACMode.OFF: 0,
            HVACMode.HEAT: 1,
            HVACMode.COOL: 2,
        }

        mode_value = mode_map.get(hvac_mode)
        if mode_value is not None:
            success = await self.coordinator.client.write_register(
                address=register_address,
                value=mode_value,
            )
            if success:
                _LOGGER.debug("Set HVAC mode to %s (value: %d)", hvac_mode, mode_value)
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to set HVAC mode to %s", hvac_mode)

    def _get_temperature_register(self) -> int | None:
        """Get the temperature setpoint register address for the current software version.

        Returns:
            Register address if configured, None if not available.
        """
        # Use heating circuit 1 comfort setpoint as the temperature setpoint
        reg_def = get_register_definition(
            SettingsRegisters.HC1_COMFORT_SETPOINT,
            self.coordinator.software_version
        )
        return reg_def.address if reg_def else None

    def _get_mode_register(self) -> int | None:
        """Get the operating mode register address for the current software version.

        Returns:
            Register address if configured, None if not available.
        """
        return OperatingModeRegisters.CURRENT_MODE.get(
            self.coordinator.software_version
        )