"""Diagnostics support for the Dimplex integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import CONF_HOST, CONF_PORT, DOMAIN

_REDACT_KEYS: set[str] = {CONF_HOST, CONF_PORT}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diag: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
            "source": entry.source,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "disabled_by": entry.disabled_by,
        }
    }

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is not None:
        diag["coordinator"] = {
            "last_update_success": coordinator.last_update_success,
            "last_exception": repr(coordinator.last_exception)
            if coordinator.last_exception
            else None,
            "data": coordinator.data,
        }

    return async_redact_data(diag, _REDACT_KEYS)

