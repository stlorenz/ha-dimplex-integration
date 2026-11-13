> **Status:** pre-1.0. Reading has been validated on an LA 1422C (WPM L/M);
> writing (setpoints, operating mode) is implemented and tested in software but
> is still being verified on hardware. See [CHANGELOG.md](CHANGELOG.md).

# Dimplex Heat Pump Home Assistant Integration

A custom Home Assistant integration for Dimplex heat pumps with NWPM Touch Extension module, providing comprehensive monitoring and control via Modbus TCP.

## Hardware Requirements

- **Dimplex Heat Pump** with Wärmepumpenmanager (WPM)
- **NWPM Touch Extension** (Article Number: 378800)
- Ethernet network connection
- WPM Software M3.3 or higher
- Gateway Firmware 3.0.5 or higher

## Features

### System Status Monitoring
- **Real-time Status** - Current operational state (Heating, Hot Water, Pool, Cooling, Defrost, etc.)
- **Lock Status** - Active blocking conditions (EVU lock, flow rate, pressure limits, etc.)
- **Error Monitoring** - Error code tracking and alerts
- **Sensor Diagnostics** - Sensor error detection (L/M software only)

### Operating Data (WPM software J/L/M)
All addresses come from the official Dimplex datapoint list
("Modbus TCP - Betriebsdaten / Laufzeiten / Wärme- und Energiemengen"):
- **Temperatures** - outside, flow, return, hot water, heat source inlet/outlet,
  room 1/2 (+ humidity), heating circuit 2/3, setpoints, passive cooling, solar storage
- **Pressures** - high / low pressure (registers 8 / 101, observed on an LA 1422C,
  not part of the official list)
- **Power & energy** - electrical input, heating output, PV surplus, smoothed COP,
  heat quantities for heating / hot water / pool / environmental energy
- **Runtimes** - compressor 1/2, primary pump/fan, 2nd heat generator, pumps, flange heater

### Binary Sensors
- Error, lock, heat pump running and defrost indicators (all software versions)
- **Digital inputs** (coils 3–6): EVU lock, external lock, Smart Grid 1/2
- **Digital outputs** (coils 41–71): compressor 1/2, primary pump / fan,
  2nd heat generator, heating / hot water / pool / cooling pumps, mixers,
  flange heater, collective fault. Coils 59 (M14) and 60 (M17) read "on" on
  the reference system although the WPM lists neither output; those two
  entities are disabled by default until their meaning is confirmed.

### Climate Control (heating circuit 1, WPM software J/L/M)
- Target temperature = room setpoint, register 46 (15–30 °C, 0.5 °C steps)
- HVAC mode = Betriebsmodus, register 5015: **Off** = Sommer (heating off, hot
  water continues), **Heat** = Winter, **Cool** = Kühlen (only if cooling is installed)
- Current temperature = room sensor 1; without a room sensor none is shown and
  flow / return temperature and return setpoint are attributes of the entity
- HVAC action: Off in Sommer, Heating / Cooling / Defrosting only while a
  compressor runs, otherwise Idle (hot water and pool charging count as idle
  for the heating circuit)
- Writes require the **Write Enable** switch

### Operating Mode Select
`select.<name>_operating_mode` switches the Betriebsmodus directly:
Sommer / Winter / Urlaub / Party / 2. Wärmeerzeuger / Kühlen.

### Writable Settings (number entities, WPM software J/L/M)
Hot water ("Modbus TCP - Einstellungen Warmwasser"):

| Entity | Register | Range |
|---|---|---|
| `number.<name>_hot_water_setpoint` | 5047 | min..85 °C |
| `number.<name>_hot_water_max_setpoint` | 5048 | setpoint..85 °C |
| `number.<name>_hot_water_min_setpoint` | 5145 | 10..setpoint °C |
| `number.<name>_hot_water_hysteresis` | 5045 | 2..15 K |

Heating circuit 1 ("Modbus TCP - Einstellungen 1. Heiz-/Kühlkreis"):

| Entity | Register | Range |
|---|---|---|
| `number.<name>_hc1_heating_curve_parallel_shift` | 5036 | −19..+19 K |
| `number.<name>_hc1_heating_curve_endpoint` | 5038 | 20..70 °C |
| `number.<name>_hc1_fixed_setpoint` | 5037 | 18..60 °C (disabled by default) |
| `number.<name>_hc1_hysteresis` | 47 | 0.5..5.0 K |
| `number.<name>_hc1_cooling_setpoint` | 5043 | 10..35 °C (cooling only) |
| `number.<name>_hc1_cooling_setpoint_at_30_c_outside` | 5134 | 10..35 °C (cooling, L/M only) |

Heating circuit 2 ("Modbus TCP - Einstellungen 2./3. Heiz-/Kühlkreis"), only
with **Second Heating Circuit** enabled in the options:

| Entity | Register | Range |
|---|---|---|
| `number.<name>_hc2_heating_curve_parallel_shift` | 5086 | −19..+19 K |
| `number.<name>_hc2_heating_curve_endpoint` | 5084 | 20..70 °C |
| `number.<name>_hc2_maximum_flow_temperature` | 5088 | 30..70 °C |
| `number.<name>_hc2_fixed_setpoint` | 5085 | 20..60 °C (disabled by default) |
| `number.<name>_hc2_mixer_runtime` | 5087 | 1..6 min (disabled by default) |
| `number.<name>_hc2_mixer_hysteresis` | 93 | 0.5..2.0 K (disabled by default) |
| `number.<name>_hc2_cooling_room_setpoint` | 5089 | 15..30 °C in 0.5 K (cooling only) |

Heating circuits 2 and 3 share this register block; register 5082 selects
which circuit it refers to. The integration reads the block only while 5082
is 2. If the WPM has 3 selected, the HC2 entities stay unavailable until
**Write Enable** is turned on once; the integration then writes 2 to 5082 and
keeps reading. Every HC2 write re-checks the selector first. HC3 settings are
not exposed yet (they would need the selector toggled on every poll).

Writes require the **Write Enable** switch. The WPM applies a new value with a
short delay (a few seconds up to one poll interval); the entity shows the new
value optimistically until the next poll confirms it.

### Reliability
- Polling interval configurable (10–300 s, default 30 s) in the integration options
- Exponential backoff after consecutive failures (up to 5 min), automatic reconnect
- Register writes are retried once after a network error
- **Write Enable** is deliberately off after every Home Assistant restart. Turn it
  on in the automation that needs it (and off again afterwards) rather than
  relying on it staying on.
- Host, port and unit ID can be changed later via **Reconfigure** on the
  integration entry; entity IDs and history are kept.

### Time Programme Services
- `dimplex.set_time_program` – write a complete raise/lower (Anhebung/Absenkung)
  programme of heating circuit 1–3 in one call: two time windows, weekday mode
  and the offset in K (registers 5065 selector + 5066..5081). Returns the
  read-back block so automations can verify the write.
- `dimplex.read_time_program` – read the current programme of a time function.

Both require **Write Enable** (reading needs the selector write).

```yaml
action: dimplex.set_time_program
data:
  function: hc2_raise      # floor-heating circuit, raise
  window1_start: "02:00"
  window1_end: "06:00"
  window2_start: "12:00"
  window2_end: "16:00"
  value: 4                 # K
```

### Model-Specific Configuration
- Select your heat pump model (LA1422C, LA Series, SI Series, etc.)
- Configure installed features (Cooling, DHW, Pool, Second Heating Circuit)
- Features automatically adapt to your specific installation

## Installation

### Prerequisites

1. **Enable Modbus TCP on your NWPM Touch module:**
   - Access the local web interface at `https://[IP_ADDRESS]`
   - Navigate to Settings → Gateway Access
   - Enable "Network Services"
   - Restart the device
   - Verify Modbus TCP is active on port 502

2. **Find your device IP address:**
   - Check on the WPM display: Analytics → Network
   - Or check your router's DHCP client list

### HACS Installation (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots menu and select "Custom repositories"
4. Add this repository URL: `https://github.com/stlorenz/ha-dimplex-integration`
5. Select category "Integration"
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/dimplex` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### Adding the Integration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Dimplex"
4. Enter your device details:
   - **Host**: IP address of your NWPM Touch module (e.g., `192.168.1.33`)
   - **Port**: Modbus TCP port (default: `502`)
   - **Name**: Friendly name for the device (e.g., `Dimplex Heat Pump`)
   - **Model**: Select your heat pump model (e.g., `LA 1422C (Air/Water)`)
   - **WPM Software Version**: H, J or L/M (shown on the WPM display under Info).
     Extended data and all controls need J or L/M.
   - **Modbus Unit / Slave ID**: usually `1`

If the NWPM Touch later gets a new IP address, use **Reconfigure** on the
integration entry instead of removing and re-adding it.

### Configuring Features

After setup, you can configure which features are installed in your system:

1. Go to Settings → Devices & Services → Dimplex
2. Click "Configure"
3. Adjust model, software version and the **polling interval** (10–300 s)
4. Enable/disable features based on your installation:
   - **Cooling Installed**: Enable if active cooling is installed (not just heat pump capability)
   - **DHW Tank**: Enable if you have a domestic hot water tank
   - **Pool Circuit**: Enable if pool heating is installed
   - **Second Heating Circuit**: Enable if HC2 is configured
   - **Passive Cooling**: enables the passive cooling temperature sensors

This ensures the UI only shows entities relevant to your specific installation.

### Available Entities

Entity ids use the device name you chose (`dimplex` below). The full list with
registers is in [docs/REGISTER_MAPPING_GUIDE.md](docs/REGISTER_MAPPING_GUIDE.md).

#### Always (all software versions)
- `sensor.dimplex_status`, `sensor.dimplex_lock`, `sensor.dimplex_error` - translated status / lock / error
- `sensor.dimplex_status_code`, `_lock_code`, `_error_code`, `_sensor_error_code` - raw codes (diagnostic)
- `binary_sensor.dimplex_error_active`, `_lock_active`, `_heat_pump_running`, `_defrost_active`
- `switch.dimplex_write_enable` - must be on before anything is written to the WPM
- `climate.dimplex` - display-only on software H

#### WPM software J / L/M
- Temperature, humidity, pressure, power, energy and runtime sensors (see Features)
- Coil based binary sensors for inputs and outputs (compressor, pumps, EVU lock, …).
  Rarely used outputs are disabled by default and can be enabled in the entity settings.
- `climate.dimplex` with room setpoint and Sommer / Winter / Kühlen mode
- `select.dimplex_operating_mode`
- Number entities for hot water, heating circuit 1 and (if enabled) heating circuit 2 settings

#### Services
- `dimplex.read_holding_registers`, `dimplex.read_input_registers`, `dimplex.write_register` - raw access for mapping work
- `dimplex.diagnose_registers` - reads every mapped datapoint and checks it against the documented range
- `dimplex.set_time_program`, `dimplex.read_time_program`

## Usage Examples

### Automation: Notify on Error

```yaml
automation:
  - alias: "Notify on Dimplex Error"
    trigger:
      - platform: state
        entity_id: binary_sensor.dimplex_error_active
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Heat Pump Error"
          message: "Error code: {{ states('sensor.dimplex_error_code') }}"
```

### Automation: Summer Mode When It Stays Warm

```yaml
automation:
  - alias: "Dimplex: switch to summer mode"
    trigger:
      - platform: numeric_state
        entity_id: sensor.dimplex_outside_temperature
        above: 18
        for: "24:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.dimplex_write_enable
      - service: select.select_option
        target:
          entity_id: select.dimplex_operating_mode
        data:
          option: summer
```

### Dashboard Card

```yaml
type: entities
entities:
  - entity: sensor.dimplex_status
  - entity: climate.dimplex
  - entity: binary_sensor.dimplex_compressor_1
  - entity: sensor.dimplex_current_heating_power
  - entity: sensor.dimplex_coefficient_of_performance
  - entity: binary_sensor.dimplex_heat_pump_running
  - entity: binary_sensor.dimplex_error_active
  - entity: sensor.dimplex_lock
title: Heat Pump Status
```

## Home Assistant Compatibility

Requires Home Assistant **2026.1 or newer** (Python 3.13+). Tested against HA
2026.10. CI runs the unit tests on Python 3.13 and 3.14 plus `hassfest` and the
HACS validator.

## Software Version Support

The WPM software version is selected during setup (and can be changed in the
options); there is no Modbus datapoint to detect it automatically.

| WPM software | Scope | Hardware status |
|---|---|---|
| **L/M** (current) | everything described above, including sensor errors | verified on an LA 1422C |
| **J** | everything except the L/M-only registers (auxiliary circulation pump runtime, cooling setpoint at 30 °C) | **unverified**, addresses from the Dimplex wiki |
| **H** | system status only (status, lock, error); no operating data, no controls | **unverified** |

If you run J or H, please open an issue with the output of
`scripts/validate_registers.py` so the mapping can be confirmed.

## Validating the register map on your device

```bash
python3 -m venv venv && venv/bin/pip install -r requirements_test.txt
venv/bin/python scripts/validate_registers.py --host 192.168.1.33
```

The script reads every datapoint the integration knows, prints raw and scaled
values with a verdict against the ranges documented by Dimplex, and prints
registers 5 (flow) and 9 (2nd heating circuit) side by side. Judge those two
only while the compressor runs: with the heat pump idle both drift towards
the return temperature (see
[docs/REGISTER_MAPPING_GUIDE.md](docs/REGISTER_MAPPING_GUIDE.md)).

## Troubleshooting

### Cannot Connect to Device

1. Verify the IP address is correct
2. Ensure Modbus TCP is enabled in the NWPM Touch web interface
3. Check firewall settings on your network
4. Verify port 502 is accessible
5. Try pinging the device from Home Assistant host

### No Data Received

1. Check that the NWPM Touch module is properly connected to the WPM
2. Verify the WPM software version is M3.3 or higher
3. Check Home Assistant logs for detailed error messages
4. Try restarting the NWPM Touch module

### Invalid Status Values

1. Ensure you have the correct software version configured
2. Check for firmware updates for the NWPM Touch module
3. Verify the WPM is powered on and operating normally

## Documentation

- [Dimplex Modbus TCP Documentation](https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303571457/Modbus+TCP+Anbindung)
- [System Status Registers](https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303833601/Modbus+TCP+-+Systemstatus)
- [Register Map & Validation Guide](docs/REGISTER_MAPPING_GUIDE.md)
- [Implementation Status](docs/IMPLEMENTATION_STATUS.md)
- [Product Requirements Document](docs/PRD.md)
- [Testing Guide](TESTING.md)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Clone the repository
2. Python 3.13 or newer: `python3 -m venv venv && venv/bin/pip install -r requirements_test.txt`
3. Run `venv/bin/pytest` (163 tests) and `venv/bin/black --check .`, `venv/bin/isort --check-only .`, `venv/bin/ruff check .`
4. Validate register changes on hardware with `scripts/validate_registers.py`
5. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: https://github.com/stlorenz/ha-dimplex-integration/issues
- Dimplex Support: ferndiagnose@dimplex.de

## License

[MIT](LICENSE) © 2025–2026 Stefan Lorenz

## Acknowledgments

Based on the official Dimplex Modbus TCP specification and Home Assistant integration guidelines.

