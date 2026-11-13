# Changelog

All notable changes to this integration are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Changelog: merged the duplicated "Added" / "Fixed" headings of 0.3.0.

## [0.3.0] - 2026-11-13

### Added
- Settings of heating circuit 2 as number entities (parallel shift, heating
  curve endpoint, maximum flow temperature, fixed setpoint, mixer runtime,
  mixer hysteresis, cooling room setpoint) from the wiki page "Einstellungen
  2./3. Heiz-/Kühlkreis". HC2 and HC3 share one register block selected via
  register 5082; the integration only switches the selector while Write
  Enable is on and re-checks it before every write. HC3 is not exposed yet.
- Reconfigure flow: change host, port or Modbus unit ID of an existing entry
  without losing entity IDs and history.
- Diagnostics download now includes software version, model, unit ID,
  Write Enable state and the current polling interval.
- `scripts/validate_registers.py` prints the shared HC2/HC3 block together
  with the selector (5082) and register 209 for cross-checking the wiki.
- CI: `hassfest` and HACS validation jobs next to the Python 3.13 / 3.14 tests.
- This changelog and an MIT license file.

### Fixed
- Climate action showed "Off" next to mode "Heat" whenever the compressor was
  idle, because WPM L/M reports status "Aus" in that case. The action is now
  derived from the operating mode and the compressor outputs: Off in Sommer,
  Heating / Cooling / Defrosting while a compressor runs, otherwise Idle.
- Climate no longer shows the return temperature as "current temperature"
  when no room sensor is fitted; flow / return / return setpoint are entity
  attributes instead.
- `manifest.json` carried a `description` key that hassfest rejects; the
  `off` option of `set_time_program` was parsed as a YAML boolean.
- `CONFIG_SCHEMA` declares the integration as UI-only (hassfest warning).

### Changed
- Software versions H and J are labelled "unverified" in the setup dialog and
  README; only L/M has been checked on hardware.
- Documented that the Write Enable switch is off after every restart and that
  coils 59 (M14) / 60 (M17) are disabled by default because their meaning is
  unconfirmed.
- `dimplex.diagnose_registers` description no longer claims the wiki and the
  integration disagree on registers 5 / 9.

### Tests
- Climate entity, diagnostics and the HC2 selector logic covered; 178 tests,
  88 % coverage.

## [0.2.0] - 2026-11-09

### Added
- Register map aligned with the official Dimplex "Modbus TCP - Datenpunktliste":
  temperatures, humidity, pressures (empirical registers 8 / 101), power, COP,
  12-digit energy counters, runtimes.
- Digital inputs (coils 3-6) and outputs (coils 41-71) as binary sensors.
- Operating mode select (Sommer / Winter / Urlaub / Party / 2. WE / Kühlen).
- Number entities for heating circuit 1: parallel shift, heating curve
  endpoint, fixed setpoint, hysteresis, cooling setpoints.
- Climate entity controls the room setpoint (register 46) and the operating
  mode (register 5015).
- Configurable polling interval (10-300 s) with exponential backoff on
  failures; register writes retried once.
- `scripts/validate_registers.py` reads every mapped datapoint from a real WPM
  and checks it against the documented ranges.
- German translation.

### Changed
- Flow temperature is register 5 and 2nd heating circuit temperature register 9,
  as in the wiki (verified with the compressor running).
- Mixer outputs renamed: M21 = heating circuit 1, M22 = heating circuit 2.
- Status code 1 on L/M is reported as "off".
- Requires Home Assistant 2026.1 or newer (Python 3.13+).

### Removed
- Sensors based on guessed register addresses (evaporator / condenser / suction
  and discharge gas temperatures, brine / water pressure, 32-bit runtime and
  energy totals at 50-62 / 80-88).

## [0.1.9 - 0.1.11] - 2026-06-15 to 2026-11-07 (untagged)

### Added
- Writable hot water settings (setpoint, maximum, minimum, hysteresis).
- Services to read and write the raise / lower time programmes of the heating
  circuits, with midnight-crossing validation and delayed read-back.
- Software version (H / J / L-M) and Modbus unit ID per entry, error
  description sensor, `diagnose_registers` service.
- Home Assistant 2026 compatibility (explicit config entry on the coordinator,
  options flow without `config_entry` assignment).

## [0.1.0 - 0.1.8] - 2025-11-22 to 2026-01-05

### Added
- Initial Modbus TCP integration: system status, lock and error messages,
  operating data sensors, Write Enable switch, model-specific feature options.
- Energy and runtime metrics, COP with smoothing, raw register services.
- pymodbus 3.8 support, availability checks for sensors and binary sensors.

[Unreleased]: https://github.com/stlorenz/ha-dimplex-integration/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/stlorenz/ha-dimplex-integration/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/stlorenz/ha-dimplex-integration/compare/v0.1.8...v0.2.0
[0.1.9 - 0.1.11]: https://github.com/stlorenz/ha-dimplex-integration/compare/v0.1.8...d4cc757
[0.1.0 - 0.1.8]: https://github.com/stlorenz/ha-dimplex-integration/compare/v0.1.0...v0.1.8
