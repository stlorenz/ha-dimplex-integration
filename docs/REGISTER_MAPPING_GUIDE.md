
# Modbus Register Mapping Guide

This guide explains how to complete the register mappings for the Dimplex heat pump integration.

## Current Status

### ✅ Completed Registers (Phase 1)

The following registers are **fully implemented and working**:

| Register Type | Software L/M | Software J | Software H | Status |
|---------------|--------------|------------|------------|--------|
| Status Messages | 103 | 43 | 14 | ✅ Complete |
| Lock Messages | 104 | 59 | 94 | ✅ Complete |
| Error Messages | 105 | 42 | 13 | ✅ Complete |
| Sensor Errors | 106 | - | - | ✅ Complete (L/M only) |

**Sensors Created:**
- `sensor.dimplex_status` - Real-time operational status
- `sensor.dimplex_lock` - Lock/blocking conditions
- `sensor.dimplex_error_code` - Error codes
- `binary_sensor.dimplex_error_active` - Error indicator
- `binary_sensor.dimplex_lock_active` - Lock indicator
- `binary_sensor.dimplex_heat_pump_running` - Running state
- `binary_sensor.dimplex_defrost_active` - Defrost indicator

---

## 📋 Registers Needing Documentation (Phase 2+)

The following register categories need addresses from the Dimplex documentation:

### 1. Operating Mode (Betriebsmodus)

**Documentation:** Look for "Modbus TCP - Betriebsmodus" page

**Needed Registers:**
- Current operating mode
- Mode selection (heating/cooling/auto)
- Mode switches

**How to Find:**
1. Navigate to the Dimplex wiki
2. Go to: Modbus TCP Anbindung → Modbus TCP - Datenpunktliste → Modbus TCP - Betriebsmodus
3. Copy the register addresses for L/M, J, and H software versions
4. Note the data type (uint16, int16, etc.)

### 2. Operating Data (Betriebsdaten)

**Documentation:** Look for "Modbus TCP - Betriebsdaten" page

**Priority: HIGH** - Contains temperature sensors and critical monitoring data

**Needed Registers:**

#### Temperature Sensors (°C, typically scaled by 0.1)
- [ ] Flow temperature (Vorlauftemperatur)
- [ ] Return temperature (Rücklauftemperatur)  
- [ ] Outside temperature (Außentemperatur)
- [ ] Hot water temperature (Warmwassertemperatur)
- [ ] Heat source inlet temperature
- [ ] Heat source outlet temperature
- [ ] Room temperature (if available)

#### Setpoints (°C, typically scaled by 0.1)
- [ ] Flow setpoint
- [ ] Hot water setpoint

#### Pressures (bar, typically scaled by 0.1)
- [ ] High pressure
- [ ] Low pressure

**How to Find:**
1. Navigate to: Modbus TCP Anbindung → Modbus TCP - Datenpunktliste → Modbus TCP - Betriebsdaten
2. Look for each temperature sensor
3. Note the register address, data type, and scaling factor
4. Document the range (min/max values)

### 3. Runtime Counters (Laufzeiten)

**Documentation:** Look for "Modbus TCP - Laufzeiten" page

**Needed Registers:**

#### Operating Hours
- [ ] Compressor total runtime (hours) - might be 32-bit (2 registers)
- [ ] Compressor start count
- [ ] Heating mode runtime
- [ ] Hot water mode runtime
- [ ] Auxiliary heater runtime

**How to Find:**
1. Navigate to: Modbus TCP Anbindung → Modbus TCP - Datenpunktliste → Modbus TCP - Laufzeiten
2. Check if runtime values are 16-bit or 32-bit
3. For 32-bit values, note both the high and low register addresses

### 4. Heat and Energy Quantities (Wärme- und Energiemengen)

**Documentation:** Look for "Modbus TCP - Wärme- und Energiemengen" page

**Priority: HIGH** - Contains power and energy monitoring

**Needed Registers:**

#### Power Measurements (W or kW)
- [ ] Current electrical power consumption
- [ ] Current heating power output
- [ ] Calculated COP (if available as register)

#### Energy Totals (kWh) - likely 32-bit values
- [ ] Total electrical energy consumed
- [ ] Total heat generated
- [ ] Heating energy
- [ ] Hot water energy

**How to Find:**
1. Navigate to: Modbus TCP Anbindung → Modbus TCP - Datenpunktliste → Modbus TCP - Wärme- und Energiemengen
2. Note units (W vs kW, Wh vs kWh)
3. Check if energy totals are 32-bit (common for large values)

### 5. Inputs and Outputs (Eingänge / Ausgänge)

**Documentation:** Look for "Modbus TCP - Eingänge" and "Modbus TCP - Ausgänge" pages

**Needed Registers:**

#### Binary Inputs
- [ ] External lock input
- [ ] EVU (utility) lock input
- [ ] Other digital inputs

#### Binary Outputs  
- [ ] Compressor relay state
- [ ] Circulation pump state
- [ ] Auxiliary heater state
- [ ] Other relay states

### 6. Settings (Einstellungen)

**Documentation:** Look for various "Modbus TCP - Einstellungen" pages

**Needed Registers (Read/Write):**

#### Heating Circuit 1
- [ ] Comfort temperature setpoint (R/W)
- [ ] Reduced temperature setpoint (R/W)
- [ ] Heating curve adjustment (R/W)

#### Hot Water
- [ ] Comfort temperature setpoint (R/W)
- [ ] Reduced temperature setpoint (R/W)

---

## How to Fill In Register Addresses

Once you have the documentation:

### Step 1: Open the Register File

Edit: `custom_components/dimplex/modbus_registers_extended.py`

### Step 2: Replace `None` with Actual Addresses

Find the register class (e.g., `OperatingDataRegisters`) and replace `None` with the actual register address:

**Before:**
```python
FLOW_TEMPERATURE = {
    SoftwareVersion.H: None,
    SoftwareVersion.J: None,
    SoftwareVersion.L_M: None,  # TODO: Fill in
}
```

**After:**
```python
FLOW_TEMPERATURE = {
    SoftwareVersion.H: 50,  # Example address
    SoftwareVersion.J: 45,  # Example address  
    SoftwareVersion.L_M: 150,  # Example address
}
```

### Step 3: Update Scaling Factors (if needed)

If the documentation shows different scaling factors, update `REGISTER_SCALING`:

```python
REGISTER_SCALING: Final[dict[str, dict]] = {
    "temperature": {
        "factor": 0.1,  # Update if documentation shows different factor
        "unit": "°C",
    },
    # ...
}
```

### Step 4: Document Register Details

Add a comment above each register with:
- Description from documentation
- Data type (uint16, int16, int32, etc.)
- Scaling factor
- Valid range
- Read/Write permission

**Example:**
```python
# Flow Temperature (Vorlauftemperatur)
# Type: int16, Scale: 0.1, Range: -50.0 to 150.0°C, Read-only
FLOW_TEMPERATURE = {
    SoftwareVersion.H: 50,
    SoftwareVersion.J: 45,
    SoftwareVersion.L_M: 150,
}
```

---

## Testing Register Addresses

After filling in register addresses, test them:

### 1. Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.dimplex: debug
```

### 2. Restart Home Assistant

### 3. Check Logs

Look for:
- ✅ Successful register reads
- ❌ Modbus errors (wrong addresses)
- ⚠️ Invalid values (wrong scaling)

### 4. Verify Values

- Temperature values should be reasonable (e.g., 20-50°C for flow temp)
- Energy values should increase over time
- Binary states should be 0 or 1

---

## Common Register Patterns

Based on Modbus conventions and the existing registers:

### Temperature Registers
- Usually `int16` (signed 16-bit)
- Scaled by 0.1 (register value 235 = 23.5°C)
- Range typically -50.0 to 150.0°C

### Energy Counters
- Usually `uint32` (unsigned 32-bit) = **2 consecutive registers**
- First register = high word, second = low word
- No scaling or scaled by 10/100 for decimal places

### Binary States
- Single bit in a register or full register (0/1)
- Often packed (multiple bits in one register)

### Setpoints (Writable)
- Same format as temperature sensors
- Use Modbus function code 0x06 (write single register) or 0x10 (write multiple)

---

## Documentation Templates

### For Recording Register Information

Use this template when reading the Dimplex documentation:

```
Register Name: _______________________
Software L/M Address: _______
Software J Address: _______
Software H Address: _______
Data Type: uint16 / int16 / uint32 / int32
Scaling Factor: _______
Unit: _______
Min Value: _______
Max Value: _______
Read/Write: R / W / R/W
Description: _______________________
```

---

## Next Steps After Filling Registers

1. **Update Implementation Status** (`IMPLEMENTATION_STATUS.md`)
   - Mark completed registers as ✅

2. **Create Sensor Entities**
   - Temperature sensors → `sensor.py`
   - Power/Energy sensors → `sensor.py`
   - Binary I/O → `binary_sensor.py`
   - Writable setpoints → `number.py`

3. **Add Translations**
   - Update `translations/en.json`
   - Add `translations/de.json`

4. **Test with Real Device**
   - Verify all values are correct
   - Check update frequency
   - Test writable registers

5. **Update Documentation**
   - Update `README.md` with new sensors
   - Add usage examples
   - Update automation examples

---

## Questions or Issues?

If you encounter:
- **Missing documentation** → Contact Dimplex support: ferndiagnose@dimplex.de
- **Register reads fail** → Check software version compatibility
- **Values seem wrong** → Verify scaling factor
- **Can't write to register** → Check if register is read-only

## Contact

GitHub Issues: https://github.com/stlorenz/ha-dimplex-integration/issues

