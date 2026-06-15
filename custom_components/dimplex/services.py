"""Service helpers for the Dimplex integration."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

SERVICE_READ_HOLDING = "read_holding_registers"
SERVICE_READ_INPUT = "read_input_registers"
SERVICE_WRITE_REGISTER = "write_register"
SERVICE_DIAGNOSE_REGISTERS = "diagnose_registers"

# Registers flagged "# UNVERIFIED" in modbus_registers_extended.py.
# Reported both ways so the user can match whichever interpretation
# corresponds to their WPM display.
_PRESSURE_DIAGNOSTIC_REGISTERS: tuple[tuple[str, int], ...] = (
    ("brine_pressure", 32),
    ("water_pressure", 33),
)

_AUX_TEMP_DIAGNOSTIC_REGISTERS: tuple[tuple[str, int], ...] = (
    ("evaporator_temperature", 20),
    ("condenser_temperature", 21),
    ("suction_gas_temperature", 22),
    ("discharge_gas_temperature", 23),
)

# 32-bit registers where the byte/word order is currently unverified.
# Each entry is (name, base address). Read 2 consecutive registers.
_THIRTYTWO_BIT_DIAGNOSTIC_REGISTERS: tuple[tuple[str, int], ...] = (
    ("compressor_runtime_total", 50),
    ("compressor_starts", 52),
    ("heating_runtime", 54),
    ("hot_water_runtime", 56),
    ("cooling_runtime", 58),
    ("auxiliary_heater_runtime", 60),
    ("defrost_cycles", 62),
    ("total_energy_consumed", 80),
    ("total_heat_generated", 82),
)


def _decode_signed_16(raw: int) -> int:
    return raw - 65536 if raw > 32767 else raw


def _decode_signed_32(raw: int) -> int:
    return raw - (1 << 32) if raw >= (1 << 31) else raw

_HASS_FLAG_SERVICES_REGISTERED = "__services_registered"


def _get_coordinator(hass: HomeAssistant, entry_id: str | None):
    domain_data = hass.data.get(DOMAIN, {})
    if entry_id:
        coordinator = domain_data.get(entry_id)
        if coordinator is None:
            raise HomeAssistantError(f"Unknown config entry_id: {entry_id}")
        return coordinator

    # Default to the only entry, if exactly one exists.
    if len(domain_data) == 1:
        return next(iter(domain_data.values()))

    raise HomeAssistantError(
        "Multiple Dimplex entries found; please pass entry_id"
    )


async def async_register_services(hass: HomeAssistant) -> None:
    """Register domain services (once)."""
    # Services must be registered per Home Assistant instance (tests create multiple hass objects).
    hass.data.setdefault(DOMAIN, {})
    if hass.data[DOMAIN].get(_HASS_FLAG_SERVICES_REGISTERED):
        return

    base_schema = vol.Schema(
        {
            vol.Optional("entry_id"): str,
            vol.Required("address"): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
            vol.Optional("count", default=1): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=125)
            ),
            vol.Optional("unit_id", default=1): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=247)
            ),
        }
    )

    async def _ensure_connected(coordinator) -> None:
        if not coordinator.client.is_connected:
            ok = await coordinator.client.connect()
            if not ok:
                raise HomeAssistantError("Unable to connect to Modbus device")

    async def handle_read_holding(call: ServiceCall) -> dict[str, Any]:
        coordinator = _get_coordinator(hass, call.data.get("entry_id"))
        address = call.data["address"]
        count = call.data["count"]
        unit_id = call.data["unit_id"]

        async with asyncio.timeout(10):
            await _ensure_connected(coordinator)
            values = await coordinator.client.read_holding_registers(
                address=address, count=count, slave=unit_id
            )

        if values is None:
            raise HomeAssistantError("Read failed (no data returned)")

        return {"address": address, "count": count, "unit_id": unit_id, "registers": values}

    async def handle_read_input(call: ServiceCall) -> dict[str, Any]:
        coordinator = _get_coordinator(hass, call.data.get("entry_id"))
        address = call.data["address"]
        count = call.data["count"]
        unit_id = call.data["unit_id"]

        async with asyncio.timeout(10):
            await _ensure_connected(coordinator)
            values = await coordinator.client.read_input_registers(
                address=address, count=count, slave=unit_id
            )

        if values is None:
            raise HomeAssistantError("Read failed (no data returned)")

        return {"address": address, "count": count, "unit_id": unit_id, "registers": values}

    write_schema = base_schema.extend(
        {
            vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
        }
    )

    async def handle_write_register(call: ServiceCall) -> dict[str, Any]:
        coordinator = _get_coordinator(hass, call.data.get("entry_id"))
        address = call.data["address"]
        value = call.data["value"]
        unit_id = call.data["unit_id"]

        if not coordinator.write_enabled:
            raise HomeAssistantError(
                "Write mode is disabled. Turn on the 'Write Enable' switch first."
            )

        async with asyncio.timeout(10):
            await _ensure_connected(coordinator)
            ok = await coordinator.client.write_register(
                address=address, value=value, slave=unit_id
            )

        if not ok:
            raise HomeAssistantError("Write failed")

        return {"address": address, "unit_id": unit_id, "value": value, "success": True}

    hass.services.async_register(
        DOMAIN,
        SERVICE_READ_HOLDING,
        handle_read_holding,
        schema=base_schema,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_READ_INPUT,
        handle_read_input,
        schema=base_schema,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_WRITE_REGISTER,
        handle_write_register,
        schema=write_schema,
        supports_response=SupportsResponse.ONLY,
    )

    diagnose_schema = vol.Schema(
        {
            vol.Optional("entry_id"): str,
            vol.Optional("unit_id", default=1): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=247)
            ),
        }
    )

    async def handle_diagnose_registers(call: ServiceCall) -> dict[str, Any]:
        """Dump unverified registers in every plausible interpretation.

        Use this once against a real device to pin down:
          - Brine/Water pressure addresses (32/33) and scale (0.01 vs 0.1).
          - Aux refrigerant temperatures at 20-23.
          - 32-bit register word order (big-endian hi/lo vs lo/hi) for
            runtime counters (50/52/54/56/58/60/62) and total energy
            (80/82).
        Compare each interpretation against the value shown on the WPM
        display, then update modbus_registers_extended.py accordingly and
        drop the `# UNVERIFIED` markers.
        """
        coordinator = _get_coordinator(hass, call.data.get("entry_id"))
        unit_id = call.data["unit_id"]

        async with asyncio.timeout(30):
            await _ensure_connected(coordinator)

            pressures: dict[str, Any] = {}
            for name, addr in _PRESSURE_DIAGNOSTIC_REGISTERS:
                values = await coordinator.client.read_holding_registers(
                    address=addr, count=1, slave=unit_id
                )
                if values is None:
                    pressures[name] = {"address": addr, "raw": None}
                    continue
                raw = values[0]
                pressures[name] = {
                    "address": addr,
                    "raw": raw,
                    "scale_0_01_bar": round(raw * 0.01, 3),
                    "scale_0_1_bar": round(raw * 0.1, 2),
                }

            aux_temps: dict[str, Any] = {}
            for name, addr in _AUX_TEMP_DIAGNOSTIC_REGISTERS:
                values = await coordinator.client.read_holding_registers(
                    address=addr, count=1, slave=unit_id
                )
                if values is None:
                    aux_temps[name] = {"address": addr, "raw": None}
                    continue
                raw = values[0]
                aux_temps[name] = {
                    "address": addr,
                    "raw": raw,
                    "signed_0_1_celsius": round(_decode_signed_16(raw) * 0.1, 1),
                    "unsigned_0_1_celsius": round(raw * 0.1, 1),
                }

            counters: dict[str, Any] = {}
            for name, addr in _THIRTYTWO_BIT_DIAGNOSTIC_REGISTERS:
                values = await coordinator.client.read_holding_registers(
                    address=addr, count=2, slave=unit_id
                )
                if values is None or len(values) < 2:
                    counters[name] = {
                        "address": addr,
                        "raw_words": values,
                    }
                    continue
                hi_lo = (values[0] << 16) | values[1]
                lo_hi = (values[1] << 16) | values[0]
                counters[name] = {
                    "address": addr,
                    "raw_words": values,
                    "big_endian_unsigned": hi_lo,
                    "little_endian_unsigned": lo_hi,
                    "big_endian_signed": _decode_signed_32(hi_lo),
                    "little_endian_signed": _decode_signed_32(lo_hi),
                    # Energy values use scale 0.1 kWh; show both for convenience.
                    "big_endian_x0_1": round(hi_lo * 0.1, 1),
                    "little_endian_x0_1": round(lo_hi * 0.1, 1),
                }

        return {
            "software_version": int(coordinator.software_version),
            "slave_id": unit_id,
            "pressure_registers": pressures,
            "aux_temperature_registers": aux_temps,
            "thirtytwo_bit_registers": counters,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_DIAGNOSE_REGISTERS,
        handle_diagnose_registers,
        schema=diagnose_schema,
        supports_response=SupportsResponse.ONLY,
    )

    hass.data[DOMAIN][_HASS_FLAG_SERVICES_REGISTERED] = True

