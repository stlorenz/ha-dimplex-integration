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

    hass.data[DOMAIN][_HASS_FLAG_SERVICES_REGISTERED] = True

