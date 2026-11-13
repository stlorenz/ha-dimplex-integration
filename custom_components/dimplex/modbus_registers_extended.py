"""Extended Modbus register definitions for the Dimplex heat pump integration.

All addresses below are taken from the official Dimplex wiki
"Modbus TCP - Datenpunktliste" (WPM Touch / NWPM Touch, software J/L/M)
unless a definition says otherwise. Pages used (fetched 2026-11-08):

- Betriebsdaten:         https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303571917
- Betriebsmodus:         https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303572150
- Laufzeiten:            https://dimplex.atlassian.net/wiki/spaces/DW/pages/3341451265
- Waerme-/Energiemengen: https://dimplex.atlassian.net/wiki/spaces/DW/pages/3341124281
- Eingaenge (Coils):     https://dimplex.atlassian.net/wiki/spaces/DW/pages/3342204929
- Ausgaenge (Coils):     https://dimplex.atlassian.net/wiki/spaces/DW/pages/3342205162
- Einstellungen 1. HK:   https://dimplex.atlassian.net/wiki/spaces/DW/pages/3341090817
- Einstellungen WW:      https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303833834
- Systemstatus:          https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303833601

Conventions
-----------
* Analogue datapoints are holding registers (FC03 read, FC06/FC16 write).
* Digital inputs/outputs are coils (FC01 read only).
* Temperatures in the operating data block are int16 in 0.1 degC steps.
* Settings registers in the 5000 range are mostly whole degC / K (uint16).
* Software version H exposes only the system status registers; every
  extended datapoint is ``None`` for H.

Datapoints marked ``EMPIRICAL`` are not in the wiki but were observed on a
real device; they are read but should be re-checked with
``scripts/validate_registers.py`` on new installations.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

from .modbus_registers import SoftwareVersion


@dataclass
class RegisterDefinition:
    """Definition of a Modbus holding register datapoint."""

    address: int | None
    """Register address (None if not available for this software version)"""

    scale: float = 1.0
    """Scale factor applied to the raw value (value = raw * scale + offset)"""

    signed: bool = True
    """Whether the register value is two's complement"""

    size: int = 1
    """Number of consecutive registers (1 = 16-bit, 2 = 32-bit, 3 = 12-digit)"""

    unit: str = ""
    """Unit of the scaled value"""

    decoder: Callable[[list[int]], int | float | None] | None = None
    """Optional decoder for multi-register values (overrides default decoding)."""

    offset: float = 0.0
    """Offset added after scaling (used for e.g. parallel shift 0..38 -> -19..19)."""

    min_value: float | None = None
    """Documented minimum of the scaled value (None = not documented)."""

    max_value: float | None = None
    """Documented maximum of the scaled value (None = not documented)."""

    writable: bool = False
    """Whether the wiki documents the register as R/W."""

    def to_raw(self, value: float) -> int:
        """Convert a scaled value back to the raw register value."""
        return int(round((value - self.offset) / self.scale))


def _reg(
    j_lm_address: int | None,
    *,
    scale: float = 1.0,
    signed: bool = True,
    size: int = 1,
    unit: str = "",
    decoder: Callable[[list[int]], int | float | None] | None = None,
    offset: float = 0.0,
    min_value: float | None = None,
    max_value: float | None = None,
    writable: bool = False,
    lm_only: bool = False,
) -> dict[SoftwareVersion, RegisterDefinition]:
    """Build a J/L_M register map (H is never available for extended data)."""

    def make(address: int | None) -> RegisterDefinition:
        return RegisterDefinition(
            address=address,
            scale=scale,
            signed=signed,
            size=size,
            unit=unit,
            decoder=decoder,
            offset=offset,
            min_value=min_value,
            max_value=max_value,
            writable=writable,
        )

    return {
        SoftwareVersion.H: make(None),
        SoftwareVersion.J: make(None if lm_only else j_lm_address),
        SoftwareVersion.L_M: make(j_lm_address),
    }


def _temp(address: int | None) -> dict[SoftwareVersion, RegisterDefinition]:
    """Operating data temperature: int16, 0.1 degC."""
    return _reg(address, scale=0.1, unit="°C", min_value=-50.0, max_value=150.0)


def _coil(
    j_lm_address: int | None, *, lm_only: bool = False
) -> dict[SoftwareVersion, int | None]:
    return {
        SoftwareVersion.H: None,
        SoftwareVersion.J: None if lm_only else j_lm_address,
        SoftwareVersion.L_M: j_lm_address,
    }


class OperatingMode(IntEnum):
    """Operating mode values for register 5015 (Betriebsmodus), WPM J/L/M."""

    SUMMER = 0
    WINTER = 1
    VACATION = 2
    PARTY = 3
    SECOND_HEAT_GENERATOR = 4
    COOLING = 5


OPERATING_MODE_KEYS: dict[int, str] = {
    OperatingMode.SUMMER: "summer",
    OperatingMode.WINTER: "winter",
    OperatingMode.VACATION: "vacation",
    OperatingMode.PARTY: "party",
    OperatingMode.SECOND_HEAT_GENERATOR: "second_heat_generator",
    OperatingMode.COOLING: "cooling",
}


# ---------------------------------------------------------------------------
# Operating Mode (Betriebsmodus) - R/W
# ---------------------------------------------------------------------------
class OperatingModeRegisters:
    """Operating mode registers (wiki "Modbus TCP - Betriebsmodus")."""

    # Plain address maps, kept for climate.py / services.py.
    CURRENT_MODE: dict[SoftwareVersion, int | None] = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: 5015,
        SoftwareVersion.L_M: 5015,
    }
    PARTY_HOURS: dict[SoftwareVersion, int | None] = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: 5016,
        SoftwareVersion.L_M: 5016,
    }
    VACATION_DAYS: dict[SoftwareVersion, int | None] = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: 5017,
        SoftwareVersion.L_M: 5017,
    }
    VENTILATION_STAGE: dict[SoftwareVersion, int | None] = {
        SoftwareVersion.H: None,
        SoftwareVersion.J: 5034,
        SoftwareVersion.L_M: 5034,
    }
    BOOST_VENTILATION_TIME: dict[SoftwareVersion, int | None] = {
        # Documented at 127 ("Zeitwert Stosslueften", 15..90) although all
        # other ventilation registers live in the 5000 range.
        SoftwareVersion.H: None,
        SoftwareVersion.J: 127,
        SoftwareVersion.L_M: 127,
    }

    # Full definitions (with documented ranges) for the datapoint reader.
    OPERATING_MODE = _reg(5015, signed=False, min_value=0, max_value=5, writable=True)
    PARTY_HOURS_DEF = _reg(
        5016, signed=False, unit="h", min_value=0, max_value=72, writable=True
    )
    VACATION_DAYS_DEF = _reg(
        5017, signed=False, unit="d", min_value=0, max_value=150, writable=True
    )


# ---------------------------------------------------------------------------
# Operating Data (Betriebsdaten) - read only, int16, 0.1 degC
# ---------------------------------------------------------------------------
class OperatingDataRegisters:
    """Operating data (wiki "Modbus TCP - Betriebsdaten").

    Wiki mapping (register: name):
      1 Aussentemperatur (R1)         2 Temperatur Ruecklauf (R2)
      3 Temperatur Warmwasser (R3)    5 Temperatur Vorlauf (R9)
      6 WQ-Eintritt (R24)             7 WQ-Austritt (R6)
      9 Temperatur 2. Heizkreis (R5)  10 Temperatur 3. Heizkreis (R13)
      11 Raumtemperatur 1             12 Raumtemperatur 2
      13 Raumfeuchte 1                14 Raumfeuchte 2
      19 Vorlauf passiv Kuehlen (R11) 20 Ruecklauf passiv Kuehlen (R4)
      21 Ruecklauf Primaerkreis (R24) 23 Solarspeicher (R22)
      53 Ruecklaufsoll                54 Soll 2. HK   55 Soll 3. HK
      58 Warmwassersoll

    NOTE on 5 vs 9: commit 0de5697 had swapped these to 9 = flow / 5 = HC2
    after a reading taken while the compressor was off. Verified on
    2026-11-09 on an LA 1422C with the compressor running: reg 5 = 37.7 degC
    (3.8 K above the return of 33.9 degC) and reg 9 = 25.2 degC (mixed
    floor-heating circuit 2, below the return). The wiki mapping is correct:
    5 = Vorlauf, 9 = 2. Heizkreis.

    Unfitted probes read exactly 0 (heat source in/out on an air unit, HC3,
    room sensors, humidity, passive cooling, solar); the sensor platform
    skips those entities.
    """

    OUTSIDE_TEMPERATURE = _temp(1)
    RETURN_TEMPERATURE = _temp(2)
    HOT_WATER_TEMPERATURE = _temp(3)
    FLOW_TEMPERATURE = _temp(5)  # Temperatur Vorlauf (R9)
    HEAT_SOURCE_INLET_TEMP = _temp(6)
    HEAT_SOURCE_OUTLET_TEMP = _temp(7)
    HC2_TEMPERATURE = _temp(9)  # Temperatur 2. Heizkreis (R5)
    HC3_TEMPERATURE = _temp(10)
    ROOM_TEMPERATURE = _temp(11)
    ROOM_TEMPERATURE_2 = _temp(12)
    ROOM_HUMIDITY = _reg(13, scale=0.1, unit="%", min_value=0, max_value=100)
    ROOM_HUMIDITY_2 = _reg(14, scale=0.1, unit="%", min_value=0, max_value=100)
    PASSIVE_COOLING_FLOW_TEMP = _temp(19)
    PASSIVE_COOLING_RETURN_TEMP = _temp(20)
    PRIMARY_CIRCUIT_RETURN_TEMP = _temp(21)
    SOLAR_STORAGE_TEMPERATURE = _temp(23)

    RETURN_SETPOINT = _temp(53)
    HC2_SETPOINT = _temp(54)
    HC3_SETPOINT = _temp(55)
    HOT_WATER_SETPOINT = _temp(58)
    # Not documented in the wiki; kept for API compatibility (never read).
    FLOW_SETPOINT = _temp(None)

    # Pressures are NOT part of the wiki datapoint list. EMPIRICAL on an
    # LA 1422C / WPM Touch: reg 8 = 226 while the display showed 22.6 bar
    # (high pressure), reg 101 = 55 while the display showed 5.5 bar (low
    # pressure). Treated as 0.1 bar, unsigned.
    HIGH_PRESSURE = _reg(
        8, scale=0.1, unit="bar", signed=False, min_value=0, max_value=60
    )
    LOW_PRESSURE = _reg(
        101, scale=0.1, unit="bar", signed=False, min_value=0, max_value=60
    )


# ---------------------------------------------------------------------------
# Runtime counters (Laufzeiten) - uint16 hours, read only
# ---------------------------------------------------------------------------
class RuntimeRegisters:
    """Runtime counters (wiki "Modbus TCP - Laufzeiten")."""

    COMPRESSOR_1_RUNTIME = _reg(72, signed=False, unit="h", min_value=0)
    COMPRESSOR_2_RUNTIME = _reg(73, signed=False, unit="h", min_value=0)
    PRIMARY_PUMP_FAN_RUNTIME = _reg(74, signed=False, unit="h", min_value=0)  # M11
    SECOND_HEAT_GENERATOR_RUNTIME = _reg(75, signed=False, unit="h", min_value=0)  # E10
    HEATING_PUMP_RUNTIME = _reg(76, signed=False, unit="h", min_value=0)  # M13
    HOT_WATER_PUMP_RUNTIME = _reg(77, signed=False, unit="h", min_value=0)  # M18
    IMMERSION_HEATER_RUNTIME = _reg(78, signed=False, unit="h", min_value=0)  # E9
    POOL_PUMP_RUNTIME = _reg(79, signed=False, unit="h", min_value=0)  # M19
    # Zusatzumwaelzpumpe (M16), documented "ab L12" -> L/M only.
    AUX_CIRC_PUMP_RUNTIME = _reg(71, signed=False, unit="h", min_value=0, lm_only=True)


def decode_digits_12(registers: list[int]) -> int | None:
    """Decode a 12-digit counter split across 3 uint16 registers.

    The wiki labels the words "1-4", "5-8" and "9-12" and gives the formula

        value = (reg_9_12 * 100000000) + (reg_5_8 * 10000) + reg_1_4

    i.e. each word holds a 4-digit decimal chunk (0..9999), not BCD nibbles.
    """
    if len(registers) < 3:
        return None

    low, mid, high = registers[0], registers[1], registers[2]
    if any(r < 0 or r > 9999 for r in (low, mid, high)):
        return None

    return (high * 100_000_000) + (mid * 10_000) + low


def _energy_12(address: int) -> dict[SoftwareVersion, RegisterDefinition]:
    return _reg(
        address,
        unit="kWh",
        signed=False,
        size=3,
        decoder=decode_digits_12,
        min_value=0,
    )


# ---------------------------------------------------------------------------
# Heat and energy quantities (Waerme- und Energiemengen, Leistungen)
# ---------------------------------------------------------------------------
class EnergyRegisters:
    """Power and energy datapoints.

    Heat quantities are only available on heat pumps with an integrated heat
    meter or the external WMZ 25/32 meter and are not suitable for billing.
    """

    # "Leistungen und Ueberschuss" (WPM J/L/M): raw value in 10 W steps.
    CURRENT_POWER_CONSUMPTION = _reg(
        5170, scale=10.0, unit="W", min_value=0, max_value=100_000
    )
    CURRENT_HEATING_POWER = _reg(
        5168, scale=10.0, unit="W", min_value=0, max_value=200_000
    )
    PV_SURPLUS = _reg(5182, scale=10.0, unit="W", writable=True)

    HEATING_ENERGY = _energy_12(5096)
    HOT_WATER_ENERGY = _energy_12(5099)
    POOL_ENERGY = _energy_12(5102)
    ENVIRONMENTAL_ENERGY = _energy_12(5127)


# ---------------------------------------------------------------------------
# Digital inputs / outputs - COILS (FC01), read only
# ---------------------------------------------------------------------------
class InputCoils:
    """Digital inputs (wiki "Modbus TCP - Eingaenge"), J/L/M."""

    SMART_GRID_1 = _coil(3)
    SMART_GRID_2 = _coil(4)
    EVU_LOCK = _coil(5)
    EXTERNAL_LOCK = _coil(6)


class OutputCoils:
    """Digital outputs (wiki "Modbus TCP - Ausgaenge"), J/L (and M)."""

    COMPRESSOR_1 = _coil(41)
    COMPRESSOR_2 = _coil(42)
    PRIMARY_PUMP_FAN = _coil(43)  # M11 / Ventilator M2
    SECOND_HEAT_GENERATOR = _coil(44)  # E10
    HEATING_PUMP_M13 = _coil(45)
    HOT_WATER_PUMP = _coil(46)  # M18
    MIXER_M21_OPEN = _coil(47)
    MIXER_M21_CLOSE = _coil(48)
    AUX_CIRC_PUMP = _coil(49)  # M16
    FLANGE_HEATER = _coil(50)  # E9
    HEATING_PUMP_M15 = _coil(51)
    MIXER_M22_OPEN = _coil(52)
    MIXER_M22_CLOSE = _coil(53)
    POOL_PUMP = _coil(56)  # M19
    COLLECTIVE_FAULT = _coil(57)  # H5
    HEATING_PUMP_M14 = _coil(59)
    COOLING_PUMP = _coil(60)  # M17
    HEATING_PUMP_M20 = _coil(61)
    ROOM_THERMOSTAT_COOLING = _coil(66)  # N9 Umschaltung Heizen/Kuehlen
    PRIMARY_PUMP_COOLING = _coil(68)  # M12
    SOLAR_PUMP = _coil(71)  # M23


# Coil blocks read in one request each: (first address, count)
INPUT_COIL_BLOCK: tuple[int, int] = (3, 4)
OUTPUT_COIL_BLOCK: tuple[int, int] = (41, 31)


# ---------------------------------------------------------------------------
# Settings (Einstellungen) - R/W holding registers
# ---------------------------------------------------------------------------
class SettingsRegisters:
    """Writable settings.

    Hot water block verified against the wiki and on an LA 1422C (WPM L/M):
    reading 5046..5048 returned [-25, 45, 60] with WW-Soll 45 / WW-Max 60,
    writing 48 to 5047 was accepted. Whole degC / K, uint16.
    """

    # --- Heating circuit 1 (wiki "Einstellungen 1. Heiz-/Kuehlkreis") ---
    # Raumtemperatur (room setpoint), 150..300 in 0.1 degC -> 15.0..30.0 degC
    HC1_ROOM_SETPOINT = _reg(
        46,
        scale=0.1,
        unit="°C",
        signed=False,
        min_value=15.0,
        max_value=30.0,
        writable=True,
    )
    # Parallelverschiebung: raw 0..38 -> -19..+19 K (raw 19 = 0 K)
    HC1_PARALLEL_SHIFT = _reg(
        5036,
        unit="K",
        signed=False,
        offset=-19.0,
        min_value=-19,
        max_value=19,
        writable=True,
    )
    # Festwertsolltemperatur 18..60 degC
    HC1_FIXED_SETPOINT = _reg(
        5037, unit="°C", signed=False, min_value=18, max_value=60, writable=True
    )
    # Heizkurvenendpunkt 20..70 degC
    HC1_HEATING_CURVE_ENDPOINT = _reg(
        5038, unit="°C", signed=False, min_value=20, max_value=70, writable=True
    )
    # Hysterese 5..50 in 0.1 K -> 0.5..5.0 K
    HC1_HYSTERESIS = _reg(
        47,
        scale=0.1,
        unit="K",
        signed=False,
        min_value=0.5,
        max_value=5.0,
        writable=True,
    )
    # Solltemperatur dynamische Kuehlung (bis L22.9) / bei 15 degC AT (ab L22.9)
    HC1_COOLING_SETPOINT = _reg(
        5043, unit="°C", signed=False, min_value=10, max_value=35, writable=True
    )
    # Solltemperatur dyn. Kuehlung bei 30 degC AT (ab L22.9) -> L/M only
    HC1_COOLING_SETPOINT_30 = _reg(
        5134,
        unit="°C",
        signed=False,
        min_value=10,
        max_value=35,
        writable=True,
        lm_only=True,
    )

    # --- Hot water (wiki "Einstellungen Warmwasser") ---
    HOT_WATER_COMFORT_SETPOINT = _reg(
        5047, unit="°C", signed=False, min_value=10, max_value=85, writable=True
    )
    HOT_WATER_MAX_SETPOINT = _reg(
        5048, unit="°C", signed=False, min_value=10, max_value=85, writable=True
    )
    HOT_WATER_MIN_SETPOINT = _reg(
        5145, unit="°C", signed=False, min_value=10, max_value=85, writable=True
    )
    HOT_WATER_HYSTERESIS = _reg(
        5045, unit="K", signed=False, min_value=2, max_value=15, writable=True
    )
    # The WPM has no separate "reduced" hot water setpoint register; the
    # reduction is realised via the time programme. Kept for API compatibility.
    HOT_WATER_REDUCED_SETPOINT = _reg(None)


# ---------------------------------------------------------------------------
# Datapoint registry: data key -> register map. The Modbus client reads every
# entry that has an address for the active software version, the sensor
# platform uses it to skip entities that can never have data, and the
# validation script uses it to check real devices.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Heating circuit 2 / 3 settings (wiki "Einstellungen 2./3. Heiz-/Kuehlkreis",
# https://dimplex.atlassian.net/wiki/spaces/DW/pages/3341123585)
#
# Both circuits share ONE register block. Register 5082 selects which circuit
# the block refers to (2 = 2. Heizkreis, 3 = 3. Heizkreis), the same pattern
# as the time programme selector 5065. The wiki page's intro mentions address
# 209 for the selector while its table says 5082; the table is used here
# (consistent with the other 5000-range settings). The validation script
# prints both so the choice can be checked on a device.
#
# Only HC2 is exposed as entities. HC3 would require toggling the selector on
# every poll, which doubles the writes; it is left for a later version.
# ---------------------------------------------------------------------------
HC_SETTINGS_SELECTOR = _reg(5082, signed=False, min_value=2, max_value=3, writable=True)
HC2_SELECTOR_VALUE = 2
HC3_SELECTOR_VALUE = 3


class HC2SettingsRegisters:
    """Settings of heating circuit 2 (valid while register 5082 == 2)."""

    # Heizkurvenendpunkt 20..70 degC
    HEATING_CURVE_ENDPOINT = _reg(
        5084, unit="°C", signed=False, min_value=20, max_value=70, writable=True
    )
    # Festwertemperatur 20..60 degC
    FIXED_SETPOINT = _reg(
        5085, unit="°C", signed=False, min_value=20, max_value=60, writable=True
    )
    # Parallelverschiebung: raw 0..38 -> -19..+19 K (raw 19 = 0 K)
    PARALLEL_SHIFT = _reg(
        5086,
        unit="K",
        signed=False,
        offset=-19.0,
        min_value=-19,
        max_value=19,
        writable=True,
    )
    # Mischerlaufzeit 1..6 min
    MIXER_RUNTIME = _reg(
        5087, unit="min", signed=False, min_value=1, max_value=6, writable=True
    )
    # Mischerhysterese 5..20 in 0.1 K -> 0.5..2.0 K
    MIXER_HYSTERESIS = _reg(
        93,
        scale=0.1,
        unit="K",
        signed=False,
        min_value=0.5,
        max_value=2.0,
        writable=True,
    )
    # Maximale Temperatur 30..70 degC
    MAX_TEMPERATURE = _reg(
        5088, unit="°C", signed=False, min_value=30, max_value=70, writable=True
    )
    # Kuehlung Raumsolltemperatur: raw 0..30 -> 15.0..30.0 degC in 0.5 K steps
    COOLING_ROOM_SETPOINT = _reg(
        5089,
        scale=0.5,
        offset=15.0,
        unit="°C",
        signed=False,
        min_value=15.0,
        max_value=30.0,
        writable=True,
    )


HC2_SETTINGS_DATAPOINTS: dict[str, dict[SoftwareVersion, RegisterDefinition]] = {
    "hc2_heating_curve_endpoint": HC2SettingsRegisters.HEATING_CURVE_ENDPOINT,
    "hc2_fixed_setpoint": HC2SettingsRegisters.FIXED_SETPOINT,
    "hc2_parallel_shift": HC2SettingsRegisters.PARALLEL_SHIFT,
    "hc2_mixer_runtime": HC2SettingsRegisters.MIXER_RUNTIME,
    "hc2_mixer_hysteresis": HC2SettingsRegisters.MIXER_HYSTERESIS,
    "hc2_max_temperature": HC2SettingsRegisters.MAX_TEMPERATURE,
    "hc2_cooling_room_setpoint": HC2SettingsRegisters.COOLING_ROOM_SETPOINT,
}
"""HC2 settings; NOT part of REGISTER_DATAPOINTS because they are only valid
after the selector (5082) has been set to 2 (DimplexModbusClient.read_hc_settings)."""


REGISTER_DATAPOINTS: dict[str, dict[SoftwareVersion, RegisterDefinition]] = {
    # Operating data
    "outside_temperature": OperatingDataRegisters.OUTSIDE_TEMPERATURE,
    "return_temperature": OperatingDataRegisters.RETURN_TEMPERATURE,
    "hot_water_temperature": OperatingDataRegisters.HOT_WATER_TEMPERATURE,
    "flow_temperature": OperatingDataRegisters.FLOW_TEMPERATURE,
    "heat_source_inlet_temperature": OperatingDataRegisters.HEAT_SOURCE_INLET_TEMP,
    "heat_source_outlet_temperature": OperatingDataRegisters.HEAT_SOURCE_OUTLET_TEMP,
    "hc2_temperature": OperatingDataRegisters.HC2_TEMPERATURE,
    "hc3_temperature": OperatingDataRegisters.HC3_TEMPERATURE,
    "room_temperature": OperatingDataRegisters.ROOM_TEMPERATURE,
    "room_temperature_2": OperatingDataRegisters.ROOM_TEMPERATURE_2,
    "room_humidity": OperatingDataRegisters.ROOM_HUMIDITY,
    "room_humidity_2": OperatingDataRegisters.ROOM_HUMIDITY_2,
    "passive_cooling_flow_temperature": OperatingDataRegisters.PASSIVE_COOLING_FLOW_TEMP,
    "passive_cooling_return_temperature": OperatingDataRegisters.PASSIVE_COOLING_RETURN_TEMP,
    "primary_circuit_return_temperature": OperatingDataRegisters.PRIMARY_CIRCUIT_RETURN_TEMP,
    "solar_storage_temperature": OperatingDataRegisters.SOLAR_STORAGE_TEMPERATURE,
    "return_setpoint": OperatingDataRegisters.RETURN_SETPOINT,
    "hc2_setpoint": OperatingDataRegisters.HC2_SETPOINT,
    "hc3_setpoint": OperatingDataRegisters.HC3_SETPOINT,
    "hot_water_setpoint": OperatingDataRegisters.HOT_WATER_SETPOINT,
    "flow_setpoint": OperatingDataRegisters.FLOW_SETPOINT,
    "high_pressure": OperatingDataRegisters.HIGH_PRESSURE,
    "low_pressure": OperatingDataRegisters.LOW_PRESSURE,
    # Operating mode
    "operating_mode_code": OperatingModeRegisters.OPERATING_MODE,
    "party_hours": OperatingModeRegisters.PARTY_HOURS_DEF,
    "vacation_days": OperatingModeRegisters.VACATION_DAYS_DEF,
    # Power / energy
    "current_power_consumption": EnergyRegisters.CURRENT_POWER_CONSUMPTION,
    "current_heating_power": EnergyRegisters.CURRENT_HEATING_POWER,
    "pv_surplus": EnergyRegisters.PV_SURPLUS,
    "heating_energy": EnergyRegisters.HEATING_ENERGY,
    "hot_water_energy": EnergyRegisters.HOT_WATER_ENERGY,
    "pool_energy": EnergyRegisters.POOL_ENERGY,
    "environmental_energy": EnergyRegisters.ENVIRONMENTAL_ENERGY,
    # Runtimes
    "compressor_1_runtime": RuntimeRegisters.COMPRESSOR_1_RUNTIME,
    "compressor_2_runtime": RuntimeRegisters.COMPRESSOR_2_RUNTIME,
    "primary_pump_fan_runtime": RuntimeRegisters.PRIMARY_PUMP_FAN_RUNTIME,
    "second_heat_generator_runtime": RuntimeRegisters.SECOND_HEAT_GENERATOR_RUNTIME,
    "heating_pump_runtime": RuntimeRegisters.HEATING_PUMP_RUNTIME,
    "hot_water_pump_runtime": RuntimeRegisters.HOT_WATER_PUMP_RUNTIME,
    "immersion_heater_runtime": RuntimeRegisters.IMMERSION_HEATER_RUNTIME,
    "pool_pump_runtime": RuntimeRegisters.POOL_PUMP_RUNTIME,
    "aux_circ_pump_runtime": RuntimeRegisters.AUX_CIRC_PUMP_RUNTIME,
    # Settings (read back so number entities show the device value)
    "hc1_room_setpoint": SettingsRegisters.HC1_ROOM_SETPOINT,
    "hc1_parallel_shift": SettingsRegisters.HC1_PARALLEL_SHIFT,
    "hc1_fixed_setpoint": SettingsRegisters.HC1_FIXED_SETPOINT,
    "hc1_heating_curve_endpoint": SettingsRegisters.HC1_HEATING_CURVE_ENDPOINT,
    "hc1_hysteresis": SettingsRegisters.HC1_HYSTERESIS,
    "hc1_cooling_setpoint": SettingsRegisters.HC1_COOLING_SETPOINT,
    "hc1_cooling_setpoint_30": SettingsRegisters.HC1_COOLING_SETPOINT_30,
    "hot_water_setpoint_setting": SettingsRegisters.HOT_WATER_COMFORT_SETPOINT,
    "hot_water_max_setpoint": SettingsRegisters.HOT_WATER_MAX_SETPOINT,
    "hot_water_min_setpoint": SettingsRegisters.HOT_WATER_MIN_SETPOINT,
    "hot_water_hysteresis": SettingsRegisters.HOT_WATER_HYSTERESIS,
}

COIL_DATAPOINTS: dict[str, dict[SoftwareVersion, int | None]] = {
    # Inputs
    "smart_grid_1": InputCoils.SMART_GRID_1,
    "smart_grid_2": InputCoils.SMART_GRID_2,
    "evu_lock": InputCoils.EVU_LOCK,
    "external_lock": InputCoils.EXTERNAL_LOCK,
    # Outputs
    "compressor_1": OutputCoils.COMPRESSOR_1,
    "compressor_2": OutputCoils.COMPRESSOR_2,
    "primary_pump_fan": OutputCoils.PRIMARY_PUMP_FAN,
    "second_heat_generator": OutputCoils.SECOND_HEAT_GENERATOR,
    "heating_pump_m13": OutputCoils.HEATING_PUMP_M13,
    "hot_water_pump": OutputCoils.HOT_WATER_PUMP,
    "mixer_m21_open": OutputCoils.MIXER_M21_OPEN,
    "mixer_m21_close": OutputCoils.MIXER_M21_CLOSE,
    "aux_circ_pump": OutputCoils.AUX_CIRC_PUMP,
    "flange_heater": OutputCoils.FLANGE_HEATER,
    "heating_pump_m15": OutputCoils.HEATING_PUMP_M15,
    "mixer_m22_open": OutputCoils.MIXER_M22_OPEN,
    "mixer_m22_close": OutputCoils.MIXER_M22_CLOSE,
    "pool_pump": OutputCoils.POOL_PUMP,
    "collective_fault": OutputCoils.COLLECTIVE_FAULT,
    "heating_pump_m14": OutputCoils.HEATING_PUMP_M14,
    "cooling_pump": OutputCoils.COOLING_PUMP,
    "heating_pump_m20": OutputCoils.HEATING_PUMP_M20,
    "room_thermostat_cooling": OutputCoils.ROOM_THERMOSTAT_COOLING,
    "primary_pump_cooling": OutputCoils.PRIMARY_PUMP_COOLING,
    "solar_pump": OutputCoils.SOLAR_PUMP,
}

# Datapoints that are derived from other datapoints in the client rather
# than read from a register. Listed so the sensor platform can keep them.
COMPUTED_DATAPOINTS: tuple[str, ...] = (
    "cop",
    "compressor_runtime_total",
    "total_heat_generated",
    "operating_mode",
)


def get_register_definition(
    register_dict: dict[SoftwareVersion, RegisterDefinition],
    software_version: SoftwareVersion,
) -> RegisterDefinition | None:
    """Return the register definition for a software version, or None.

    None is returned when the version is unknown or the address is None.
    """
    reg_def = register_dict.get(software_version)
    if reg_def is None or reg_def.address is None:
        return None
    return reg_def


def get_coil_address(
    coil_dict: dict[SoftwareVersion, int | None], software_version: SoftwareVersion
) -> int | None:
    """Return the coil address for a software version, or None."""
    return coil_dict.get(software_version)


def scale_value(raw_value: int, register_def: RegisterDefinition) -> float:
    """Scale a raw register value using its definition.

    Two's-complement decoding is applied when ``signed=True``, sized by the
    register's width (16 bit for size=1, 32 bit for size=2).
    """
    if register_def.signed:
        bits = register_def.size * 16
        sign_bit = 1 << (bits - 1)
        if raw_value >= sign_bit:
            raw_value -= 1 << bits

    return raw_value * register_def.scale + register_def.offset


def read_32bit_value(registers: list[int]) -> int:
    """Combine two 16-bit registers [high, low] into a 32-bit value."""
    if len(registers) < 2:
        return 0
    return (registers[0] << 16) | registers[1]
