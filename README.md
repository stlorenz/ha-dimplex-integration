THIS IS A WORK IN PROGRESS. DO NOT USE YET. 

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

### Binary Sensors
- Error Active indicator
- Lock Active indicator
- Heat Pump Running state
- Defrost Active state

### Climate Control
- Temperature display (read-only currently)
- HVAC mode display
- **Note:** Temperature and mode control require Modbus register addresses to be configured. Currently the integration is read-only for monitoring purposes.

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

### Configuring Features

After setup, you can configure which features are installed in your system:

1. Go to Settings → Devices & Services → Dimplex
2. Click "Configure"
3. Enable/disable features based on your installation:
   - **Cooling Installed**: Enable if active cooling is installed (not just heat pump capability)
   - **DHW Tank**: Enable if you have a domestic hot water tank
   - **Pool Circuit**: Enable if pool heating is installed
   - **Second Heating Circuit**: Enable if HC2 is configured

This ensures the UI only shows controls relevant to your specific installation.

### Available Entities

After setup, the following entities will be created:

#### Sensors
- `sensor.dimplex_status` - Current operational status
- `sensor.dimplex_status_code` - Raw status code (diagnostic)
- `sensor.dimplex_lock` - Current lock/blocking condition
- `sensor.dimplex_lock_code` - Raw lock code (diagnostic)
- `sensor.dimplex_error_code` - Current error code
- `sensor.dimplex_sensor_error_code` - Sensor error code (L/M software only)

#### Binary Sensors
- `binary_sensor.dimplex_error_active` - Error present indicator
- `binary_sensor.dimplex_lock_active` - Lock condition indicator
- `binary_sensor.dimplex_heat_pump_running` - Running state
- `binary_sensor.dimplex_defrost_active` - Defrost cycle indicator

#### Climate
- `climate.dimplex_climate` - Temperature control entity

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

### Automation: External Lock Management

```yaml
automation:
  - alias: "Lock Heat Pump During Peak Hours"
    trigger:
      - platform: time
        at: "17:00:00"
    action:
      - service: switch.turn_on
        entity_id: switch.dimplex_external_lock
```

### Dashboard Card

```yaml
type: entities
entities:
  - entity: sensor.dimplex_status
  - entity: climate.dimplex_climate
  - entity: binary_sensor.dimplex_heat_pump_running
  - entity: binary_sensor.dimplex_error_active
  - entity: sensor.dimplex_lock
title: Heat Pump Status
```

## Software Version Support

The integration automatically detects and supports different WPM software versions:

- **L/M Software** (Latest) - Full feature support including sensor errors
- **J Software** - Full feature support
- **H Software** - Basic feature support

Different software versions use different Modbus register addresses, which are handled automatically.

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
- [Product Requirements Document](PRD.md)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Clone the repository
2. Create a development environment
3. Install dependencies: `pip install pymodbus>=3.5.0`
4. Make your changes
5. Test with a real device or Modbus simulator
6. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: https://github.com/stlorenz/ha-dimplex-integration/issues
- Dimplex Support: ferndiagnose@dimplex.de

## License

[Add your license here]

## Acknowledgments

Based on the official Dimplex Modbus TCP specification and Home Assistant integration guidelines.

