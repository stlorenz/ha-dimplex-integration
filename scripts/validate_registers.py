#!/usr/bin/env python3
"""Validate the integration's Modbus register map against a real WPM.

Reads every datapoint the integration knows (holding registers and coils)
directly over Modbus TCP, prints raw and scaled values and checks them
against the ranges documented in the Dimplex wiki. No Home Assistant needed.

Usage (from the repository root, inside the test venv):

    venv/bin/python scripts/validate_registers.py --host 192.168.1.33
    venv/bin/python scripts/validate_registers.py --host 192.168.1.33 --version J
    venv/bin/python scripts/validate_registers.py --host 192.168.1.33 --json out.json
    venv/bin/python scripts/validate_registers.py --host 192.168.1.33 --dump 1 60
    venv/bin/python scripts/validate_registers.py --host 192.168.1.33 --watch 10

Exit code 0 = every read succeeded and every documented range held,
1 = at least one problem, 2 = connection failure.

``--dump START COUNT`` prints a raw holding-register block (int16 and
uint16 interpretation) for mapping registers the wiki does not list.
``--watch SECONDS`` re-reads the operating data block repeatedly, which
helps to tell flow from return temperature (flow changes first when the
compressor starts) and to settle the register 5 / 9 question.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Make the custom component importable without installing it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.dimplex.modbus_registers import (
    ERROR_MESSAGES,
    SoftwareVersion,
    get_error_register,
    get_lock_message,
    get_lock_register,
    get_sensor_error_register,
    get_status_message,
    get_status_register,
)
from custom_components.dimplex.modbus_registers_extended import (
    COIL_DATAPOINTS,
    HC2_SETTINGS_DATAPOINTS,
    HC_SETTINGS_SELECTOR,
    REGISTER_DATAPOINTS,
    RegisterDefinition,
    get_coil_address,
    get_register_definition,
    read_32bit_value,
    scale_value,
)

try:
    from pymodbus.client import AsyncModbusTcpClient
except ImportError:  # pragma: no cover - friendly hint for a bare interpreter
    print("pymodbus is required: pip install pymodbus>=3.8", file=sys.stderr)
    sys.exit(2)

VERSIONS = {
    "H": SoftwareVersion.H,
    "J": SoftwareVersion.J,
    "L_M": SoftwareVersion.L_M,
    "L": SoftwareVersion.L_M,
    "M": SoftwareVersion.L_M,
}

# Wiki "Betriebsdaten" labels for the raw dump / watch mode.
WIKI_OPERATING_DATA: dict[int, str] = {
    1: "Aussentemperatur (R1)",
    2: "Temperatur Ruecklauf (R2)",
    3: "Temperatur Warmwasser (R3)",
    5: "Temperatur Vorlauf (R9)  [integration: flow_temperature]",
    6: "WQ-Eintritt (R24)",
    7: "WQ-Austritt (R6)",
    8: "EMPIRICAL Hochdruck 0.1 bar",
    9: "Temperatur 2. Heizkreis (R5)  [integration: hc2_temperature]",
    10: "Temperatur 3. Heizkreis (R13)",
    11: "Raumtemperatur 1",
    12: "Raumtemperatur 2",
    13: "Raumfeuchte 1",
    14: "Raumfeuchte 2",
    19: "Vorlauf passiv Kuehlen (R11)",
    20: "Ruecklauf passiv Kuehlen (R4)",
    21: "Ruecklauf Primaerkreis (R24)",
    23: "Solarspeicher (R22)",
    46: "Einstellung HK1 Raumtemperatur (0.1 degC)",
    47: "Einstellung HK1 Hysterese (0.1 K)",
    53: "Ruecklaufsoll",
    54: "Soll 2. Heizkreis",
    55: "Soll 3. Heizkreis",
    58: "Warmwassersoll",
    71: "Laufzeit Zusatzumwaelzpumpe M16 (h)",
    72: "Laufzeit Verdichter 1 (h)",
    73: "Laufzeit Verdichter 2 (h)",
    74: "Laufzeit Primaerpumpe/Ventilator M11 (h)",
    75: "Laufzeit 2. Waermeerzeuger E10 (h)",
    76: "Laufzeit Heizungspumpe M13 (h)",
    77: "Laufzeit Warmwasserpumpe M18 (h)",
    78: "Laufzeit Flanschheizung E9 (h)",
    79: "Laufzeit Schwimmbadpumpe M19 (h)",
    101: "EMPIRICAL Niederdruck 0.1 bar",
    103: "Statusmeldung (L/M)",
    104: "Sperrmeldung (L/M)",
    105: "Stoermeldung (L/M)",
    106: "Sensorfehler (L/M)",
}


def _int16(raw: int) -> int:
    return raw - 65536 if raw > 32767 else raw


class Reader:
    """Thin async wrapper around pymodbus with the unit-id keyword detection."""

    def __init__(self, host: str, port: int, unit: int, timeout: float) -> None:
        self.client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)
        self.unit = unit
        self._kw: str | None = None

    async def connect(self) -> bool:
        await self.client.connect()
        return self.client.connected

    def close(self) -> None:
        self.client.close()

    async def _call(self, method: Any, **kwargs: Any) -> Any:
        if self._kw:
            return await method(**kwargs, **{self._kw: self.unit})
        for candidate in ("device_id", "slave", "unit"):
            try:
                result = await method(**kwargs, **{candidate: self.unit})
            except TypeError as err:
                if f"unexpected keyword argument '{candidate}'" in str(err):
                    continue
                raise
            self._kw = candidate
            return result
        raise TypeError("cannot determine pymodbus unit keyword")

    async def holding(self, address: int, count: int = 1) -> list[int] | None:
        try:
            result = await self._call(
                self.client.read_holding_registers, address=address, count=count
            )
        except Exception as err:  # noqa: BLE001 - report and continue
            print(f"  ! exception reading {address}: {err}", file=sys.stderr)
            return None
        if result.isError():
            return None
        return list(result.registers)

    async def coils(self, address: int, count: int = 1) -> list[bool] | None:
        try:
            result = await self._call(
                self.client.read_coils, address=address, count=count
            )
        except Exception as err:  # noqa: BLE001
            print(f"  ! exception reading coil {address}: {err}", file=sys.stderr)
            return None
        if result.isError():
            return None
        return [bool(b) for b in result.bits[:count]]


def _verdict(value: float, reg: RegisterDefinition) -> str:
    if reg.min_value is None and reg.max_value is None:
        return "no-range"
    if reg.min_value is not None and value < reg.min_value:
        return "BELOW"
    if reg.max_value is not None and value > reg.max_value:
        return "ABOVE"
    return "ok"


async def validate(reader: Reader, version: SoftwareVersion) -> dict[str, Any]:
    """Read everything once and return a structured report."""
    report: dict[str, Any] = {
        "software_version": version.name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": {},
        "registers": {},
        "coils": {},
        "problems": [],
    }

    # --- system status ---------------------------------------------------
    print("\n== System status ==")
    for name, addr in (
        ("status", get_status_register(version)),
        ("lock", get_lock_register(version)),
        ("error", get_error_register(version)),
        ("sensor_error", get_sensor_error_register(version)),
    ):
        if addr is None:
            continue
        words = await reader.holding(addr)
        raw = words[0] if words else None
        text = None
        if raw is not None:
            if name == "status":
                text = get_status_message(raw, version)
            elif name == "lock":
                text = get_lock_message(raw, version)
            elif name == "error":
                text = ERROR_MESSAGES.get(raw, f"unknown_{raw}")
        report["status"][name] = {"address": addr, "raw": raw, "text": text}
        flag = "" if raw is not None else "  <-- READ FAILED"
        print(f"  {name:13s} reg {addr:5d}  raw={raw!s:>6}  {text or ''}{flag}")
        if raw is None:
            report["problems"].append(f"{name}: read failed")

    # --- holding register datapoints --------------------------------------
    print("\n== Holding registers ==")
    print(
        f"  {'datapoint':36s} {'addr':>5s} {'raw':>14s} {'value':>12s} {'unit':5s} {'range':16s} verdict"
    )
    for key, reg_map in REGISTER_DATAPOINTS.items():
        reg = get_register_definition(reg_map, version)
        if reg is None:
            continue
        words = await reader.holding(reg.address, reg.size)
        entry: dict[str, Any] = {
            "address": reg.address,
            "size": reg.size,
            "unit": reg.unit,
            "raw": words,
        }
        if words is None:
            entry["verdict"] = "READ-FAILED"
            value_str = "-"
        elif reg.decoder is not None:
            decoded = reg.decoder(words)
            entry["value"] = decoded
            entry["verdict"] = (
                "DECODE-FAILED" if decoded is None else _verdict(decoded, reg)
            )
            value_str = str(decoded)
        else:
            raw = read_32bit_value(words) if reg.size == 2 else words[0]
            value = scale_value(raw, reg)
            entry["value"] = round(value, 3)
            entry["verdict"] = _verdict(value, reg)
            if reg.size == 1 and not reg.signed and words[0] > 32767:
                entry["alt_signed"] = round(
                    _int16(words[0]) * reg.scale + reg.offset, 3
                )
            value_str = f"{value:.1f}".rstrip("0").rstrip(".")
        rng = ""
        if reg.min_value is not None or reg.max_value is not None:
            rng = f"{reg.min_value if reg.min_value is not None else ''}..{reg.max_value if reg.max_value is not None else ''}"
        mark = "" if entry["verdict"] in ("ok", "no-range") else "  <--"
        print(
            f"  {key:36s} {reg.address:5d} {words!s:>14s} {value_str:>12s} {reg.unit:5s} {rng:16s} {entry['verdict']}{mark}"
        )
        if entry["verdict"] not in ("ok", "no-range"):
            report["problems"].append(
                f"{key} (reg {reg.address}): {entry['verdict']} value={entry.get('value')}"
            )
        report["registers"][key] = entry

    # --- coils --------------------------------------------------------------
    print("\n== Coils (inputs 3..6, outputs 41..71) ==")
    for key, coil_map in COIL_DATAPOINTS.items():
        addr = get_coil_address(coil_map, version)
        if addr is None:
            continue
        bits = await reader.coils(addr)
        state = bits[0] if bits else None
        report["coils"][key] = {"address": addr, "state": state}
        flag = "" if state is not None else "  <-- READ FAILED"
        print(
            f"  {key:28s} coil {addr:3d}  {'ON ' if state else ('off' if state is not None else '-')}{flag}"
        )
        if state is None:
            report["problems"].append(f"coil {key} ({addr}): read failed")

    # --- HC2 / HC3 shared settings block ---------------------------------
    # The wiki page lists 5082 as selector in its table but mentions 209 in
    # the intro; both are printed. Nothing is written here.
    sel = get_register_definition(HC_SETTINGS_SELECTOR, version)
    if sel is not None and sel.address is not None:
        print("\n== Heating circuit 2/3 settings (shared block, selector 5082) ==")
        words = await reader.holding(sel.address)
        selector = words[0] if words else None
        words209 = await reader.holding(209)
        print(
            f"  selector reg 5082 = {selector!s:>4}   (2 = 2. Heizkreis, 3 = 3. Heizkreis)"
        )
        print(
            f"  reg 209           = {words209[0] if words209 else '-'!s:>4}   (wiki intro names this as selector)"
        )
        report["hc_settings"] = {
            "selector_5082": selector,
            "reg_209": words209[0] if words209 else None,
        }
        if selector not in (2, 3):
            report["problems"].append(
                f"hc settings selector (5082) = {selector}, expected 2 or 3"
            )
        circuit = f"HC{selector}" if selector in (2, 3) else "HC?"
        print(f"  block currently shows {circuit}:")
        for key, reg_map in HC2_SETTINGS_DATAPOINTS.items():
            reg = get_register_definition(reg_map, version)
            if reg is None:
                continue
            words = await reader.holding(reg.address, reg.size)
            if words is None:
                verdict, value_str, value = "READ-FAILED", "-", None
            else:
                value = scale_value(words[0], reg)
                verdict = _verdict(value, reg)
                value_str = f"{value:.1f}".rstrip("0").rstrip(".")
            rng = f"{reg.min_value}..{reg.max_value}"
            mark = "" if verdict in ("ok", "no-range") else "  <--"
            print(
                f"  {key:36s} {reg.address:5d} {words!s:>14s} {value_str:>12s} {reg.unit:5s} {rng:16s} {verdict}{mark}"
            )
            report["hc_settings"][key] = {
                "address": reg.address,
                "raw": words,
                "value": value,
                "verdict": verdict,
            }
            if verdict not in ("ok", "no-range"):
                report["problems"].append(
                    f"{key} (reg {reg.address}): {verdict} value={value}"
                )

    # --- wiki cross check 5 vs 9 -----------------------------------------
    print("\n== Register 5 vs 9 (wiki: 5 = Vorlauf R9, 9 = 2. Heizkreis R5) ==")
    for addr in (5, 9, 2, 53):
        words = await reader.holding(addr)
        val = f"{_int16(words[0]) / 10:.1f} °C" if words else "-"
        print(f"  reg {addr:3d}: {val:>10s}   {WIKI_OPERATING_DATA.get(addr, '')}")
    print("  -> Verified on an LA 1422C: reg 5 = Vorlauf, reg 9 = 2. Heizkreis.")
    print("     Flow is normally a few K above return (reg 2) while heating.")

    return report


async def dump(reader: Reader, start: int, count: int) -> None:
    """Print a raw holding-register block."""
    print(f"\n== Raw holding registers {start}..{start + count - 1} ==")
    print(f"  {'addr':>5s} {'uint16':>7s} {'int16':>7s} {'/10':>8s}  label")
    step = 100
    for base in range(start, start + count, step):
        n = min(step, start + count - base)
        words = await reader.holding(base, n)
        if words is None:
            print(f"  {base}..{base + n - 1}: read failed (try a smaller block)")
            continue
        for i, w in enumerate(words):
            addr = base + i
            print(
                f"  {addr:5d} {w:7d} {_int16(w):7d} {_int16(w) / 10:8.1f}  {WIKI_OPERATING_DATA.get(addr, '')}"
            )


async def watch(reader: Reader, seconds: float) -> None:
    """Re-read the Betriebsdaten block until interrupted."""
    addrs = sorted(a for a in WIKI_OPERATING_DATA if a <= 58)
    print(f"\n== Watching Betriebsdaten every {seconds:g}s (Ctrl+C to stop) ==")
    print("  " + " ".join(f"r{a:>4d}" for a in addrs))
    try:
        while True:
            words = await reader.holding(1, 58)
            if words is None:
                print("  read failed")
            else:
                row = []
                for a in addrs:
                    w = words[a - 1]
                    row.append(f"{_int16(w) / 10:5.1f}")
                print("  " + " ".join(row) + f"   {time.strftime('%H:%M:%S')}")
            await asyncio.sleep(seconds)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n  stopped")


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--host", required=True, help="IP / hostname of the NWPM Touch module"
    )
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument(
        "--unit", type=int, default=1, help="Modbus unit / slave id (default 1)"
    )
    parser.add_argument(
        "--version",
        default="L_M",
        choices=sorted(VERSIONS),
        help="WPM software version (default L_M)",
    )
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--json", metavar="FILE", help="write the full report as JSON")
    parser.add_argument(
        "--dump",
        nargs=2,
        type=int,
        metavar=("START", "COUNT"),
        help="raw dump of a holding register block",
    )
    parser.add_argument(
        "--watch",
        type=float,
        metavar="SECONDS",
        help="re-read the operating data block periodically",
    )
    args = parser.parse_args()

    version = VERSIONS[args.version]
    reader = Reader(args.host, args.port, args.unit, args.timeout)
    print(
        f"Connecting to {args.host}:{args.port} (unit {args.unit}, WPM software {version.name}) ..."
    )
    if not await reader.connect():
        print("Connection failed", file=sys.stderr)
        return 2

    try:
        if args.dump:
            await dump(reader, args.dump[0], args.dump[1])
            return 0
        if args.watch:
            await watch(reader, args.watch)
            return 0

        report = await validate(reader, version)
        print("\n== Summary ==")
        if report["problems"]:
            print(f"  {len(report['problems'])} problem(s):")
            for p in report["problems"]:
                print(f"   - {p}")
        else:
            print("  all reads succeeded and all documented ranges hold")
        if args.json:
            Path(args.json).write_text(
                json.dumps(report, indent=2, default=str), encoding="utf-8"
            )
            print(f"  report written to {args.json}")
        return 1 if report["problems"] else 0
    finally:
        reader.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
