# Implementation Status

This document tracks the implementation status of the Dimplex Heat Pump Home
Assistant integration against the [Product Requirements Document](PRD.md).

**Last Updated:** November 13, 2026
**Version:** 0.2.0 (main, unreleased changes towards 1.0 listed in CHANGELOG.md)
**Reference hardware:** LA 1422C with NWPM Touch, WPM software L/M

All register addresses are taken from the official Dimplex wiki
("Modbus TCP - Datenpunktliste", see `custom_components/dimplex/modbus_registers_extended.py`
for the page links). Two values (high/low pressure, registers 8 / 101) are not
in the wiki and were determined empirically.

---

## Completed ✅

### Communication

- ✅ Modbus TCP client (pymodbus 3.x) with connect/retry, holding/input registers, coils (FC01), single register write with one retry
- ✅ Data coordinator with configurable polling interval (10–300 s, options flow)
- ✅ Exponential backoff on consecutive failures (up to 5 min), reset on success
- ✅ Per-entry Modbus unit/slave ID and WPM software version (H / J / L+M)
- ✅ Reconfigure flow: host / port / unit ID can be changed without losing the entry (entity IDs, history)
- ✅ Diagnostics download (config + coordinator state, host/port redacted)
- ✅ Partial data on failures: system status is always delivered, operating data is best effort

### System status (all software versions)

- ✅ Status messages (31 states), lock messages (43), error messages, sensor errors (L/M)
- ✅ Binary sensors: error active, lock active, heat pump running, defrost active
- ✅ Error description sensor (enum, translated)

### Operating data (J / L / M)

- ✅ Temperatures: outside, flow, return, hot water, heat source in/out, room 1/2, HC2/HC3, setpoints (return, hot water, HC2, HC3), passive cooling flow/return, primary circuit return, solar storage
- ✅ Room humidity 1/2
- ✅ High / low pressure (empirical registers 8 / 101, 0.1 bar)
- ✅ Power: electrical input, thermal output, PV surplus; smoothed COP
- ✅ Heat quantities: heating, hot water, pool, environmental energy (12-digit counters, wiki formula); total heat generated (derived)
- ✅ Runtimes: compressor 1/2 (+ derived total), primary pump/fan, 2nd heat generator, heating pump, hot water pump, flange heater, pool pump, auxiliary circulation pump
- ✅ Digital inputs as binary sensors: EVU lock, external lock, Smart Grid 1/2
- ✅ Digital outputs as binary sensors: compressors, pumps, mixers, flange heater, 2nd heat generator, collective fault, …

### Control (J / L / M, behind the Write Enable switch)

- ✅ Climate entity for heating circuit 1: room setpoint (register 46, 15–30 °C), HVAC mode via Betriebsmodus (OFF = Sommer, HEAT = Winter, COOL = Kühlen)
- ✅ Select: operating mode (Sommer / Winter / Urlaub / Party / 2. WE / Kühlen)
- ✅ Numbers: hot water setpoint / max / min / hysteresis; HC1 parallel shift, heating curve endpoint, fixed setpoint, hysteresis, cooling setpoints
- ✅ Services: read/write raw registers, diagnose registers, set/read time programme

### Quality

- ✅ 163 unit tests, 88 % coverage, CI on Python 3.13 / 3.14 with black, isort, ruff, hassfest and the HACS validator
- ✅ `scripts/validate_registers.py`: reads every mapped datapoint from a real WPM and checks documented ranges
- ✅ English and German translations
- ✅ Device info with WPM software version

---

## Pending 📋

### Needs a real device

- ✅ Flow vs. HC2 temperature settled with the compressor running: wiki mapping (5 = Vorlauf, 9 = 2. Heizkreis) restored
- ✅ 12-digit energy counter formula confirmed on an LA 1422C (heating 68 666 kWh for 4 345 h compressor 1 runtime)
- ✅ Output coils 41–51 match the WPM "Ein- und Ausgänge" screen (compressor 1, fan M2, M13, M15, M16, E9, E10, M18); M21 "zu" is permanently on because the HC1 mixer is unconfigured
- ⬜ Coils 59 (M14) and 60 (M17) are on although the WPM lists neither output; entities disabled by default until confirmed
- ✅ Status code 1 = "Aus" on L/M (was reported as unknown_1)
- ✅ Hot water / HC1 settings read back with plausible values (48 / 60 / 10 °C, 6 K; 20.0 °C, 0 K, 50 °C, 3.0 K)
- ⬜ Verify Software H / J register sets (only L/M hardware available so far; marked "unverified" in the setup dialog and README)

### Not implemented

- ⬜ Settings for heating circuits 2/3, swimming pool and 2nd heat generator (wiki pages exist, not yet mapped)
- ⬜ Remaining time programme functions (hot water lock, thermal disinfection, circulation pump)
- ⬜ Ventilation datapoints (registers 120–127, 5034)
- ⬜ Firmware version / serial number in device info (no Modbus datapoint documented)
- ⬜ Automatic software version detection (no documented datapoint; user selects H / J / L-M)
- ⬜ Auto-discovery, multiple heat pumps per host

---

## Removed in 0.2.0

The following entities were based on guessed addresses that are not in the
Dimplex datapoint list and have been removed: evaporator / condenser / suction
gas / discharge gas temperature (20–23), brine and water pressure (32/33),
32-bit runtime counters and totals at 50–62 / 80–88 (compressor starts,
heating/hot water/cooling/auxiliary runtime, defrost cycles, total energy
consumed, cooling energy). `compressor_runtime_total` and `total_heat_generated`
are kept as derived values. Orphaned entities can be deleted from the entity
registry after the update.

---

## Road to 1.0

Code side (done on `main`): hassfest + HACS validation in CI, diagnostics and
climate fully covered by tests, reconfigure flow, CHANGELOG, documentation of
the Write Enable behaviour and of the unexplained coils 59/60.

Hardware side: every write path, the reconnect behaviour and the reconfigure
flow have been confirmed on the LA 1422C (2026-11-13). The only open item is
the multi-day soak run at the default 30 s interval; 1.0.0 is tagged once it
passes.

## Testing checklist (manual, on hardware)

Verified on the LA 1422C (WPM L/M) by Stefan Lorenz; dates are the day of the check.

- [x] `scripts/validate_registers.py --host <ip>` reports no problems (2026-11-09)
- [x] Flow / return temperature match the WPM display (2026-11-09, compressor running)
- [x] Hot water setpoint write (number entity) is accepted and read back (2026-11-13)
- [x] HC1 room setpoint write via climate entity is accepted (2026-11-13)
- [x] Operating mode select: Winter ↔ Sommer round trip, change visible on the WPM (2026-11-13)
- [x] Compressor binary sensor follows the compressor (2026-11-13)
- [x] Parallel shift write (number entity) is reflected on the WPM display (2026-11-13)
- [x] Connection recovery after unplugging the NWPM Touch for a minute, backoff visible in the log (2026-11-13)
- [x] Reconfigure to a wrong IP shows "cannot connect", to the right IP keeps all entities (2026-11-13)
- [x] Climate action shows Idle with the compressor off in Winter, Off in Sommer (2026-11-13, after PR #6)
- [ ] Several days of polling at 30 s without connection drops, memory growth or repeated warnings (started 2026-11-13)
