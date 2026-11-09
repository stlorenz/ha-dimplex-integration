"""Shared entity helpers for the Dimplex integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_NAME, DOMAIN
from .modbus_registers import SoftwareVersion

SOFTWARE_VERSION_LABELS: dict[SoftwareVersion, str] = {
    SoftwareVersion.H: "H",
    SoftwareVersion.J: "J",
    SoftwareVersion.L_M: "L/M",
}


def build_device_info(coordinator: Any, entry: Any) -> DeviceInfo:
    """Build the device registry entry shared by all platforms.

    Works with the real coordinator as well as the lightweight stand-ins used
    in tests (only ``model_name`` and ``software_version`` are read).
    """
    sw_version = getattr(coordinator, "software_version", None)
    label = (
        SOFTWARE_VERSION_LABELS.get(sw_version)
        if isinstance(sw_version, SoftwareVersion)
        else None
    )

    info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_NAME, "Dimplex Heat Pump"),
        manufacturer="Dimplex",
        model=getattr(coordinator, "model_name", None),
    )
    if label is not None:
        info["sw_version"] = f"WPM {label}"
    return info
