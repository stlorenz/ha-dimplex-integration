# Modbus Register Map & Validation Guide

The register map lives in `custom_components/dimplex/modbus_registers_extended.py`
(operating data, settings, coils) and `custom_components/dimplex/modbus_registers.py`
(system status). Every address comes from the Dimplex wiki
"Modbus TCP - Datenpunktliste" unless marked `EMPIRICAL`.

## Sources

| Topic | Wiki page |
|---|---|
| Overview / supported function codes | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303571457/Modbus+TCP+Anbindung> |
| Betriebsdaten (temperatures) | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303571917> |
| Betriebsmodus | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303572150> |
| Laufzeiten | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3341451265> |
| Wärme- und Energiemengen | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3341124281> |
| Eingänge (coils) | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3342204929> |
| Ausgänge (coils) | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3342205162> |
| Einstellungen 1. Heiz-/Kühlkreis | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3341090817> |
| Einstellungen Warmwasser | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303833834> |
| Systemstatus | <https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303833601> |

## Conventions

* Analogue values are **holding registers** (FC03 read, FC06/16 write).
* Digital inputs/outputs are **coils** (FC01, read only). Inputs 3–6, outputs 41–71.
* Operating data temperatures are `int16` in 0.1 °C. Settings in the 5000 range are whole °C / K.
* Heat quantities are 12-digit counters in three words: `value = w3·10⁸ + w2·10⁴ + w1`.
* Parallel shift (5036) is stored as 0..38 and means −19..+19 K.
* Software **H** has no extended datapoints; **J** lacks a few L/M-only registers (71, 5134).

## Registers 5 and 9 (flow vs. 2nd heating circuit)

An earlier version read the flow temperature from register 9 after a reading
taken while the compressor was off. Verified on 2026-11-09 on an LA 1422C with
the compressor running: register 5 was 3.8 K above the return and register 9
(mixed floor-heating circuit) below it, so the wiki is right: **5 = Vorlauf,
9 = 2. Heizkreis**. The validation script still prints both side by side.

## Output coils on an LA 1422C (verified 2026-11-09)

Coils 41 (Verdichter 1), 42, 43 (Ventilator M2), 44 (E10), 45 (M13), 46 (M18),
49 (M16, shown as "Erzeugerkreispumpe" in the WPM app), 50 (E9) and 51 (M15)
matched the WPM "Ein- und Ausgänge" screen. Coil 48 (Mischer M21 "zu") is
permanently on because the HC1 mixer is not configured on that system. Coils
59 (M14) and 60 (M17) were on although the WPM lists neither output; both
entities stay disabled by default until someone can confirm them.

## Validating against a real device

No Home Assistant needed, only the test venv:

```bash
venv/bin/python scripts/validate_registers.py --host 192.168.1.33            # full check
venv/bin/python scripts/validate_registers.py --host 192.168.1.33 --json r.json
venv/bin/python scripts/validate_registers.py --host 192.168.1.33 --watch 10 # follow temperatures
venv/bin/python scripts/validate_registers.py --host 192.168.1.33 --dump 1 60 # raw block
```

The full check reads every mapped register and coil, prints raw words, the
scaled value and a verdict against the documented range, and exits non-zero
when something is off. `--watch` prints the Betriebsdaten block every few
seconds, which is the quickest way to tell flow from return (flow rises
first when the compressor starts). `--dump` prints a raw block for registers
the wiki does not list.

Inside Home Assistant the service `dimplex.diagnose_registers` returns the
same information as a service response.

## Adding a datapoint

1. Add a `RegisterDefinition` map (or coil map) to the matching class with the
   wiki address, scale, documented min/max and `writable` flag.
2. Register it in `REGISTER_DATAPOINTS` / `COIL_DATAPOINTS` under its data key.
   The Modbus client reads every registry entry automatically.
3. Add an entity description (sensor / binary_sensor / number) using the same key.
4. Add the `name` to `strings.json`, `translations/en.json` and `translations/de.json`.
5. Add the address to `tests/test_modbus_registers_extended.py` and run
   `scripts/validate_registers.py` against hardware.
