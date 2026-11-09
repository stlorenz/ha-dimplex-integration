"""Service helpers for the Dimplex integration."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .modbus_registers_extended import (
    COIL_DATAPOINTS,
    REGISTER_DATAPOINTS,
    get_coil_address,
    get_register_definition,
    read_32bit_value,
    scale_value,
)

SERVICE_READ_HOLDING = "read_holding_registers"
SERVICE_READ_INPUT = "read_input_registers"
SERVICE_WRITE_REGISTER = "write_register"
SERVICE_DIAGNOSE_REGISTERS = "diagnose_registers"
SERVICE_SET_TIME_PROGRAM = "set_time_program"
SERVICE_READ_TIME_PROGRAM = "read_time_program"

# Time programme registers (Dimplex wiki "Modbus TCP - Zeitprogramm ...
# Absenk-/Anhebung", WPM J/L/M). The block 5066..5081 is shared by all time
# functions; register 5065 selects which one is addressed.
TIME_PROGRAM_SELECT_REGISTER = 5065
TIME_PROGRAM_BLOCK_START = (
    5066  # window1 start h/min, end h/min, window2 ..., 7 weekdays, value
)
TIME_PROGRAM_BLOCK_LEN = 16
TIME_PROGRAM_FUNCTIONS: dict[str, int] = {
    # Verified on WPM Touch (L/M), LA 1422C: 2 = HC1 raise, 3 = HC2 lower,
    # 4 = HC2 raise (programme shows up under "2. Heizkreis" in the Wochenprofil).
    "hc1_lower": 1,
    "hc1_raise": 2,
    "hc2_lower": 3,
    "hc2_raise": 4,
    "hc3_lower": 5,
    "hc3_raise": 6,
}
# Weekday registers 5074..5080 are Sunday..Saturday; encoding 0 = both windows,
# 1 = off, 2 = window 1 only, 3 = window 2 only.
WEEKDAY_ORDER = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")
WEEKDAY_MODES: dict[str, int] = {"both": 0, "off": 1, "window1": 2, "window2": 3}

# Flow / HC2 temperature (registers 5 / 9) were swapped in an earlier
# version; the diagnose service keeps reporting them side by side with the
# wiki labels so users can confirm the mapping on their device.
_WIKI_CROSS_CHECK: tuple[tuple[int, str, str], ...] = (
    (5, "Temperatur Vorlauf (R9)", "flow_temperature"),
    (9, "Temperatur 2. Heizkreis (R5)", "hc2_temperature"),
)


def _decode_signed_16(raw: int) -> int:
    return raw - 65536 if raw > 32767 else raw


def _range_verdict(value: float, reg_def: Any) -> str:
    """Compare a scaled value with the documented range."""
    if reg_def.min_value is None and reg_def.max_value is None:
        return "no_documented_range"
    if reg_def.min_value is not None and value < reg_def.min_value:
        return "below_documented_range"
    if reg_def.max_value is not None and value > reg_def.max_value:
        return "above_documented_range"
    return "ok"


_HASS_FLAG_SERVICES_REGISTERED = "__services_registered"


def cv_time_hhmm(value: Any) -> tuple[int, int]:
    """Validate 'HH:MM' (or 'HH:MM:SS') and return (hour, minute)."""
    text = str(value)
    parts = text.split(":")
    if len(parts) not in (2, 3):
        raise vol.Invalid(f"Expected HH:MM, got {text!r}")
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError as err:
        raise vol.Invalid(f"Expected HH:MM, got {text!r}") from err
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise vol.Invalid(f"Time out of range: {text!r}")
    return hour, minute


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

    raise HomeAssistantError("Multiple Dimplex entries found; please pass entry_id")


async def async_register_services(hass: HomeAssistant) -> None:
    """Register domain services (once)."""
    # Services must be registered per Home Assistant instance (tests create multiple hass objects).
    hass.data.setdefault(DOMAIN, {})
    if hass.data[DOMAIN].get(_HASS_FLAG_SERVICES_REGISTERED):
        return

    base_schema = vol.Schema(
        {
            vol.Optional("entry_id"): str,
            vol.Required("address"): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=65535)
            ),
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

        return {
            "address": address,
            "count": count,
            "unit_id": unit_id,
            "registers": values,
        }

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

        return {
            "address": address,
            "count": count,
            "unit_id": unit_id,
            "registers": values,
        }

    write_schema = base_schema.extend(
        {
            vol.Required("value"): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=65535)
            ),
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

    time_program_schema = vol.Schema(
        {
            vol.Optional("entry_id"): str,
            vol.Optional("unit_id", default=1): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=247)
            ),
            vol.Required("function"): vol.In(list(TIME_PROGRAM_FUNCTIONS)),
            vol.Required("window1_start"): cv_time_hhmm,
            vol.Required("window1_end"): cv_time_hhmm,
            vol.Optional("window2_start"): cv_time_hhmm,
            vol.Optional("window2_end"): cv_time_hhmm,
            vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=0, max=19)),
            vol.Optional("weekdays", default="both"): vol.In(list(WEEKDAY_MODES)),
            vol.Optional("readback_delay", default=5): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=60)
            ),
        }
    )

    def _check_window(start: tuple[int, int], end: tuple[int, int], label: str) -> None:
        """The WPM rejects windows that cross midnight and silently rewrites the
        whole block (observed on WPM Touch L/M: 16:00-02:00 became 06:00-23:59 /
        16:00-23:59 and one weekday was disabled). Refuse them up front."""
        if (end[0], end[1]) <= (start[0], start[1]):
            raise HomeAssistantError(
                f"{label}: end must be later than start on the same day "
                f"(got {start[0]:02d}:{start[1]:02d}-{end[0]:02d}:{end[1]:02d}); "
                "windows crossing midnight are not supported by the WPM - "
                "use 23:59 as end and a second window from 00:00 if needed."
            )

    async def handle_set_time_program(call: ServiceCall) -> dict[str, Any]:
        """Write one complete raise/lower time programme in one go.

        Sequence: select the time function (5065), then write the shared block
        5066..5081 (window 1, window 2, seven weekday flags, value in K).
        """
        coordinator = _get_coordinator(hass, call.data.get("entry_id"))
        unit_id = call.data["unit_id"]
        if not coordinator.write_enabled:
            raise HomeAssistantError(
                "Write mode is disabled. Turn on the 'Write Enable' switch first."
            )

        w1s = call.data["window1_start"]
        w1e = call.data["window1_end"]
        w2s = call.data.get("window2_start", w1e)
        w2e = call.data.get("window2_end", w1e)
        if "window2_start" not in call.data:
            # No second window: collapse it to a zero-length window.
            w2s = w2e = w1e
        _check_window(w1s, w1e, "window 1")
        if w2s != w2e:
            _check_window(w2s, w2e, "window 2")
        weekday_mode = WEEKDAY_MODES[call.data["weekdays"]]

        values = [
            w1s[0],
            w1s[1],
            w1e[0],
            w1e[1],
            w2s[0],
            w2s[1],
            w2e[0],
            w2e[1],
            *([weekday_mode] * 7),
            int(call.data["value"]),
        ]
        function = TIME_PROGRAM_FUNCTIONS[call.data["function"]]

        async with asyncio.timeout(90):
            await _ensure_connected(coordinator)
            ok = await coordinator.client.write_register(
                address=TIME_PROGRAM_SELECT_REGISTER, value=function, slave=unit_id
            )
            if not ok:
                raise HomeAssistantError("Selecting the time function failed")
            # Give the WPM a moment to switch the shared block to the selected function.
            await asyncio.sleep(0.5)
            for offset, value in enumerate(values):
                ok = await coordinator.client.write_register(
                    address=TIME_PROGRAM_BLOCK_START + offset,
                    value=value,
                    slave=unit_id,
                )
                if not ok:
                    raise HomeAssistantError(
                        f"Write failed at register {TIME_PROGRAM_BLOCK_START + offset}"
                    )
            # The WPM validates the block after the write and may rewrite it;
            # read back only after it had time to do so.
            await asyncio.sleep(float(call.data["readback_delay"]))
            readback = await coordinator.client.read_holding_registers(
                TIME_PROGRAM_BLOCK_START, count=TIME_PROGRAM_BLOCK_LEN, slave=unit_id
            )

        return {
            "function": call.data["function"],
            "written": values,
            "readback": list(readback) if readback else None,
            "success": bool(readback) and list(readback) == values,
        }

    read_time_program_schema = vol.Schema(
        {
            vol.Optional("entry_id"): str,
            vol.Optional("unit_id", default=1): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=247)
            ),
            vol.Required("function"): vol.In(list(TIME_PROGRAM_FUNCTIONS)),
        }
    )

    async def handle_read_time_program(call: ServiceCall) -> dict[str, Any]:
        """Select a time function and read its programme block (selector write needed)."""
        coordinator = _get_coordinator(hass, call.data.get("entry_id"))
        unit_id = call.data["unit_id"]
        if not coordinator.write_enabled:
            raise HomeAssistantError(
                "Reading a time programme requires writing the selector register; "
                "turn on the 'Write Enable' switch first."
            )
        function = TIME_PROGRAM_FUNCTIONS[call.data["function"]]
        async with asyncio.timeout(20):
            await _ensure_connected(coordinator)
            ok = await coordinator.client.write_register(
                address=TIME_PROGRAM_SELECT_REGISTER, value=function, slave=unit_id
            )
            if not ok:
                raise HomeAssistantError("Selecting the time function failed")
            await asyncio.sleep(0.5)
            regs = await coordinator.client.read_holding_registers(
                TIME_PROGRAM_BLOCK_START, count=TIME_PROGRAM_BLOCK_LEN, slave=unit_id
            )
        if not regs:
            raise HomeAssistantError("Read failed")
        regs = list(regs)
        return {
            "function": call.data["function"],
            "window1": f"{regs[0]:02d}:{regs[1]:02d}-{regs[2]:02d}:{regs[3]:02d}",
            "window2": f"{regs[4]:02d}:{regs[5]:02d}-{regs[6]:02d}:{regs[7]:02d}",
            "weekdays": dict(zip(WEEKDAY_ORDER, regs[8:15], strict=False)),
            "value_k": regs[15],
            "raw": regs,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TIME_PROGRAM,
        handle_set_time_program,
        schema=time_program_schema,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_READ_TIME_PROGRAM,
        handle_read_time_program,
        schema=read_time_program_schema,
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
        """Read every mapped datapoint once and check it against the wiki.

        For each register in ``REGISTER_DATAPOINTS`` the raw word(s), the
        scaled value and a verdict against the documented range are
        returned; coils are listed with their state. Registers whose wiki
        meaning differs from the mapping used by the integration (5 / 9)
        are reported side by side so they can be matched with the WPM
        display. ``scripts/validate_registers.py`` does the same from the
        command line without Home Assistant.
        """
        coordinator = _get_coordinator(hass, call.data.get("entry_id"))
        unit_id = call.data["unit_id"]
        sw = coordinator.software_version

        registers: dict[str, Any] = {}
        coils: dict[str, Any] = {}
        cross_check: dict[str, Any] = {}
        problems: list[str] = []

        async with asyncio.timeout(120):
            await _ensure_connected(coordinator)

            for key, register_dict in REGISTER_DATAPOINTS.items():
                reg_def = get_register_definition(register_dict, sw)
                if reg_def is None:
                    continue
                words = await coordinator.client.read_holding_registers(
                    address=reg_def.address, count=reg_def.size, slave=unit_id
                )
                entry: dict[str, Any] = {
                    "address": reg_def.address,
                    "size": reg_def.size,
                    "unit": reg_def.unit,
                    "raw": list(words) if words is not None else None,
                }
                if words is None:
                    entry["verdict"] = "read_failed"
                    problems.append(f"{key}: read failed (register {reg_def.address})")
                elif reg_def.decoder is not None:
                    decoded = reg_def.decoder(list(words))
                    entry["value"] = decoded
                    entry["verdict"] = (
                        "decode_failed"
                        if decoded is None
                        else _range_verdict(decoded, reg_def)
                    )
                else:
                    raw = (
                        read_32bit_value(list(words)) if reg_def.size == 2 else words[0]
                    )
                    value = scale_value(raw, reg_def)
                    entry["value"] = round(value, 3)
                    if reg_def.size == 1:
                        entry["alt_signed"] = round(
                            _decode_signed_16(words[0]) * reg_def.scale
                            + reg_def.offset,
                            3,
                        )
                    entry["verdict"] = _range_verdict(value, reg_def)
                if entry["verdict"] not in ("ok", "no_documented_range", "read_failed"):
                    problems.append(f"{key}: {entry['verdict']} ({entry.get('value')})")
                registers[key] = entry

            for key, coil_dict in COIL_DATAPOINTS.items():
                addr = get_coil_address(coil_dict, sw)
                if addr is None:
                    continue
                bits = await coordinator.client.read_coils(
                    address=addr, count=1, slave=unit_id
                )
                coils[key] = {
                    "address": addr,
                    "state": bits[0] if bits else None,
                }

            for addr, wiki_name, mapped_key in _WIKI_CROSS_CHECK:
                words = await coordinator.client.read_holding_registers(
                    address=addr, count=1, slave=unit_id
                )
                cross_check[str(addr)] = {
                    "wiki_name": wiki_name,
                    "integration_uses_it_as": mapped_key,
                    "value_celsius": (
                        round(_decode_signed_16(words[0]) * 0.1, 1) if words else None
                    ),
                }

        return {
            "software_version": int(sw),
            "slave_id": unit_id,
            "problems": problems,
            "registers": registers,
            "coils": coils,
            "wiki_cross_check": cross_check,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_DIAGNOSE_REGISTERS,
        handle_diagnose_registers,
        schema=diagnose_schema,
        supports_response=SupportsResponse.ONLY,
    )

    hass.data[DOMAIN][_HASS_FLAG_SERVICES_REGISTERED] = True
