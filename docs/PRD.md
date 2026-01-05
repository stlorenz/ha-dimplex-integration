# Product Requirements Document (PRD)
## Dimplex Heat Pump Home Assistant Integration

**Version:** 1.0  
**Date:** November 19, 2025  
**Author:** @stlorenz  
**Status:** Draft

---

## 1. Executive Summary

This document outlines the requirements for a Home Assistant custom integration for Dimplex heat pumps. The integration will communicate with Dimplex heat pump systems via Modbus TCP protocol through the NWPM Touch Extension module, providing comprehensive monitoring and control capabilities.

### 1.1 Project Goals

- Enable Home Assistant users to monitor and control Dimplex heat pumps locally
- Provide real-time access to all available sensors and data points via Modbus TCP
- Implement reliable communication with automatic error handling and reconnection
- Support climate control for heating system management
- Expose all operational data as Home Assistant sensors

---

## 2. Background & Context

### 2.1 Hardware Requirements

- **Device**: Dimplex Heat Pump with Wärmepumpenmanager (WPM)
- **Extension Module**: NWPM Touch-Erweiterung (Article Number: 378800)
- **Connectivity**: Ethernet network (RJ45, 10/100BaseT, Cat5, max 100m)
- **Protocol**: Modbus TCP (Port 502)

### 2.2 Software Requirements

- **WPM Software**: M3.3 or higher
- **Gateway Firmware**: 3.0.5 or higher
- **Operating System**: Linux 4.11.11 (on NWPM Touch module)

### 2.3 Reference Documentation

- [Dimplex Modbus TCP Documentation](https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303571457/Modbus+TCP+Anbindung#8-Datenpunktliste)

---

## 3. Target Users

### Primary Users
- Home Assistant users with Dimplex heat pump systems
- Smart home enthusiasts seeking local control of heating systems
- Energy efficiency-focused homeowners

### User Expertise Levels
- **Beginner**: Users who want plug-and-play setup via UI
- **Intermediate**: Users who want to create automations
- **Advanced**: Users who want to monitor detailed technical parameters

---

## 4. Functional Requirements

### 4.1 Connection & Configuration

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| FR-1.1 | Support config flow for UI-based setup | Must Have | User enters IP address and port |
| FR-1.2 | Auto-discovery of Dimplex devices on local network | Nice to Have | Future enhancement |
| FR-1.3 | Support both DHCP and static IP configurations | Must Have | - |
| FR-1.4 | Validate connection during setup | Must Have | Test Modbus TCP connectivity |
| FR-1.5 | Support multiple heat pump instances | Should Have | Multiple config entries |
| FR-1.6 | Display connection status in UI | Must Have | Connected/Disconnected state |

### 4.2 Data Collection & Updates

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| FR-2.1 | Poll device data at configurable intervals | Must Have | Default: 30 seconds |
| FR-2.2 | Implement exponential backoff on connection failures | Must Have | Prevent network flooding |
| FR-2.3 | Automatic reconnection on connection loss | Must Have | - |
| FR-2.4 | Log communication errors appropriately | Must Have | Debug level for normal operations |
| FR-2.5 | Support coordinator-based data updates | Must Have | Efficient batch reading |

### 4.3 Climate Control

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| FR-3.1 | Expose heat pump as Climate entity | Must Have | - |
| FR-3.2 | Support temperature setpoint control | Must Have | Heating target temperature |
| FR-3.3 | Display current temperature | Must Have | From heat pump sensor |
| FR-3.4 | Support HVAC modes (Heat, Off, Auto) | Must Have | Based on available modes |
| FR-3.5 | Display current operation mode | Must Have | Heating, Idle, etc. |
| FR-3.6 | Support preset modes | Should Have | Comfort, Eco, Away, etc. |
| FR-3.7 | Implement temperature step of 0.5°C | Must Have | Per typical heat pump specs |

### 4.4 Sensor Entities

All data points from the Modbus TCP data point list shall be exposed as appropriate Home Assistant entities.

#### 4.4.1 Temperature Sensors

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| FR-4.1 | Flow temperature (Vorlauftemperatur) | Must Have | Heating circuit supply |
| FR-4.2 | Return temperature (Rücklauftemperatur) | Must Have | Heating circuit return |
| FR-4.3 | Outside temperature (Außentemperatur) | Must Have | Outdoor sensor |
| FR-4.4 | Hot water temperature (Warmwassertemperatur) | Must Have | DHW tank |
| FR-4.5 | Heat source inlet temperature | Should Have | Source side |
| FR-4.6 | Heat source outlet temperature | Should Have | Source side |
| FR-4.7 | Room temperature | Should Have | If available |
| FR-4.8 | Buffer tank temperature(s) | Should Have | If configured |

#### 4.4.2 Performance & Energy Sensors

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| FR-4.9 | Current power consumption | Must Have | Electrical power input |
| FR-4.10 | Heating power output | Must Have | Thermal power output |
| FR-4.11 | COP (Coefficient of Performance) | Must Have | Calculated or direct |
| FR-4.12 | Total energy consumed | Must Have | Energy meter |
| FR-4.13 | Total heat generated | Should Have | Energy meter |
| FR-4.14 | Compressor operating hours | Must Have | Maintenance tracking |
| FR-4.15 | Circulation pump status | Should Have | On/Off state |

#### 4.4.3 Status & Operational Sensors

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| FR-4.16 | Operating mode | Must Have | Heating, DHW, Standby, etc. |
| FR-4.17 | Operating state | Must Have | Running, Idle, Defrost, etc. |
| FR-4.18 | Error/Alarm status | Must Have | Binary sensor |
| FR-4.19 | Error code | Must Have | Sensor with error number |
| FR-4.20 | Error description | Should Have | Translated error text |
| FR-4.21 | Defrost status | Should Have | Binary sensor |
| FR-4.22 | DHW heating status | Should Have | Binary sensor |
| FR-4.23 | Additional heater status | Should Have | If configured |

#### 4.4.4 Binary Sensors

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| FR-4.24 | Compressor running | Must Have | - |
| FR-4.25 | Circulation pump running | Should Have | - |
| FR-4.26 | Error active | Must Have | - |
| FR-4.27 | Warning active | Should Have | - |
| FR-4.28 | DHW demand | Should Have | - |
| FR-4.29 | Heating demand | Should Have | - |

#### 4.4.5 Control Entities

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| FR-4.30 | DHW heating switch | Should Have | Enable/Disable DHW |
| FR-4.31 | Operating mode select | Should Have | Select dropdown |
| FR-4.32 | Heating curve adjustment | Nice to Have | Number entity |
| FR-4.33 | Comfort temperature setpoint | Should Have | Number entity |
| FR-4.34 | Reduced temperature setpoint | Should Have | Number entity |

### 4.5 Device Information

| ID | Requirement | Priority | Notes |
|----|------------|----------|-------|
| FR-5.1 | Display device model | Must Have | Device registry |
| FR-5.2 | Display firmware version | Must Have | Device registry |
| FR-5.3 | Display serial number | Should Have | Device registry |
| FR-5.4 | Display software version | Should Have | Device registry |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement | Priority |
|----|------------|----------|
| NFR-1.1 | Poll interval configurable from 10-300 seconds | Must Have |
| NFR-1.2 | Respond to user commands within 5 seconds | Must Have |
| NFR-1.3 | Initial setup time under 30 seconds | Should Have |

### 5.2 Reliability

| ID | Requirement | Priority |
|----|------------|----------|
| NFR-2.1 | Handle network interruptions gracefully | Must Have |
| NFR-2.2 | Recover automatically from device restarts | Must Have |
| NFR-2.3 | Prevent data corruption on communication errors | Must Have |
| NFR-2.4 | Validate all Modbus responses | Must Have |

### 5.3 Usability

| ID | Requirement | Priority |
|----|------------|----------|
| NFR-3.1 | Provide clear error messages in UI | Must Have |
| NFR-3.2 | Use device class icons for all sensors | Must Have |
| NFR-3.3 | Provide meaningful entity names | Must Have |
| NFR-3.4 | Support English and German translations | Should Have |

### 5.4 Maintainability

| ID | Requirement | Priority |
|----|------------|----------|
| NFR-4.1 | Follow Home Assistant development guidelines | Must Have |
| NFR-4.2 | Include type hints throughout codebase | Must Have |
| NFR-4.3 | Maintain comprehensive logging | Must Have |
| NFR-4.4 | Provide unit test coverage >80% | Should Have |

---

## 6. Technical Architecture

### 6.1 Component Structure

```
custom_components/dimplex/
├── __init__.py                 # Integration setup
├── manifest.json               # Integration metadata
├── config_flow.py              # UI configuration
├── const.py                    # Constants
├── coordinator.py              # Data coordinator
├── modbus_client.py            # Modbus TCP client wrapper
├── models.py                   # Data models
├── climate.py                  # Climate entity
├── sensor.py                   # Sensor entities
├── binary_sensor.py            # Binary sensor entities
├── number.py                   # Number entities (setpoints)
├── select.py                   # Select entities (modes)
├── switch.py                   # Switch entities (controls)
└── translations/
    ├── en.json                 # English translations
    └── de.json                 # German translations
```

### 6.2 Communication Flow

1. **Initialization**: Config flow validates connection
2. **Setup**: Coordinator initializes Modbus client
3. **Polling**: Coordinator reads Modbus registers on schedule
4. **Update**: Entities receive data via coordinator callbacks
5. **Control**: User actions write to Modbus registers
6. **Error Handling**: Failed communications trigger retry logic

### 6.3 Modbus Register Mapping

The integration shall implement a register map based on the official Dimplex Modbus TCP data point list. Each register will be mapped to appropriate Home Assistant entity types:

- **Holding Registers**: Read/write parameters (temperatures, modes)
- **Input Registers**: Read-only measurements (sensors, status)
- **Coils**: Binary controls (on/off switches)
- **Discrete Inputs**: Binary status (running states)

### 6.4 Dependencies

```python
requirements = [
    "pymodbus>=3.5.0",  # Modbus TCP client library
]
```

---

## 7. User Stories

### 7.1 Setup & Configuration

**US-1**: As a user, I want to add my Dimplex heat pump through the Home Assistant UI so that I don't need to edit configuration files.

**Acceptance Criteria:**
- Configuration flow accessible via UI
- Only IP address and optional port required
- Connection validation before completion
- Clear error messages on failure

### 7.2 Monitoring

**US-2**: As a user, I want to see the current operating status of my heat pump so that I know if it's working properly.

**Acceptance Criteria:**
- Operating mode visible in UI
- Current temperatures displayed
- Error status clearly indicated
- Data updates automatically

**US-3**: As a user, I want to monitor energy consumption and efficiency so that I can optimize my heating costs.

**Acceptance Criteria:**
- Current power consumption visible
- COP (efficiency) calculated and displayed
- Energy statistics available
- Historical data tracked

### 7.3 Control

**US-4**: As a user, I want to adjust the heating temperature setpoint so that I can control my home comfort.

**Acceptance Criteria:**
- Temperature adjustable via Climate entity
- Changes applied immediately
- Current setpoint always visible
- Temperature in 0.5°C steps

**US-5**: As a user, I want to switch between heating modes (comfort/reduced) so that I can save energy when away.

**Acceptance Criteria:**
- Mode selection available
- Mode changes confirmed
- Current mode always visible

### 7.4 Automation

**US-6**: As a user, I want to create automations based on heat pump data so that I can optimize operations.

**Acceptance Criteria:**
- All sensors available as automation triggers
- State changes fire events
- Conditions can use sensor values
- Actions can control setpoints

### 7.5 Maintenance

**US-7**: As a user, I want to be notified of errors and warnings so that I can address issues promptly.

**Acceptance Criteria:**
- Error status exposed as binary sensor
- Error codes readable
- Error descriptions in plain language
- Integration with HA notifications

---

## 8. Success Criteria

### 8.1 Launch Criteria

- [ ] All Must Have features implemented
- [ ] Successful connection to real Dimplex device
- [ ] All sensors reading correct values
- [ ] Climate control functional
- [ ] Error handling tested
- [ ] Documentation complete

### 8.2 Quality Metrics

- **Reliability**: <1% communication failure rate under normal conditions
- **Response Time**: <5 seconds for control commands
- **Uptime**: Integration stable for >7 days continuous operation
- **User Satisfaction**: Positive feedback from beta testers

---

## 9. Development Phases

### Phase 1: Core Communication (Week 1)
- Modbus TCP client implementation
- Register mapping from data point list
- Basic coordinator setup
- Connection testing

### Phase 2: Sensors & Monitoring (Week 2)
- Temperature sensor entities
- Status sensor entities
- Binary sensor entities
- Device information

### Phase 3: Climate Control (Week 3)
- Climate entity implementation
- Temperature setpoint control
- HVAC mode control
- Testing and refinement

### Phase 4: Advanced Features (Week 4)
- Number entities (additional setpoints)
- Select entities (operating modes)
- Switch entities (controls)
- Error handling improvements

### Phase 5: Polish & Documentation (Week 5)
- Translations (English, German)
- User documentation
- Code cleanup and optimization
- Beta testing

---

## 10. Open Questions & Risks

### 10.1 Open Questions

1. **Q**: What is the complete Modbus register map?  
   **A**: Need to access full data point list from section 8 of documentation

2. **Q**: Are there device model variations requiring different register maps?  
   **A**: TBD - may need device detection

3. **Q**: What authentication is required for Modbus TCP?  
   **A**: Documentation suggests none for local access

4. **Q**: Are there rate limits on Modbus requests?  
   **A**: TBD - need to test with actual device

### 10.2 Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Incomplete register documentation | High | Medium | Request detailed docs from Dimplex support |
| Device communication instability | High | Low | Implement robust retry logic and error handling |
| Register map changes between firmware versions | Medium | Medium | Add firmware version detection and adaptation |
| Performance issues with many entities | Medium | Low | Optimize polling and batch register reads |

---

## 11. Out of Scope

The following items are explicitly out of scope for v1.0:

- Cloud connectivity to Dimplex servers
- Support for other Dimplex connection methods (KNX, BACnet, MQTT)
- Modbus RTU support (only Modbus TCP)
- Advanced diagnostic features
- Historical data analysis (use HA recorder)
- Mobile app integration (use HA app)
- Multi-language support beyond English and German

---

## 12. Future Enhancements

Potential features for future versions:

- Auto-discovery via mDNS/SSDP
- Enhanced energy dashboard integration
- Predictive heating curves
- Integration with dynamic electricity tariffs
- Advanced error diagnostics
- Firmware update notifications
- Configuration backup/restore

---

## 13. Appendices

### Appendix A: Modbus TCP Specifications

- **Protocol**: Modbus TCP (RFC standard)
- **Port**: 502
- **Function Codes**: 
  - 0x03: Read Holding Registers
  - 0x04: Read Input Registers  
  - 0x06: Write Single Register
  - 0x10: Write Multiple Registers

### Appendix B: References

1. [Dimplex Modbus TCP Documentation](https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303571457/Modbus+TCP+Anbindung#8-Datenpunktliste)
2. [Home Assistant Developer Documentation](https://developers.home-assistant.io/)
3. [Modbus TCP Protocol Specification](https://www.modbus.org/)
4. [PyModbus Documentation](https://pymodbus.readthedocs.io/)

### Appendix C: Glossary

- **WPM**: Wärmepumpenmanager (Heat Pump Manager)
- **NWPM Touch**: Network extension module for Dimplex heat pumps
- **COP**: Coefficient of Performance (efficiency metric)
- **DHW**: Domestic Hot Water
- **Modbus TCP**: Industrial communication protocol over Ethernet
- **Register**: Modbus data storage location

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-19 | @stlorenz | Initial draft |

---

**Next Steps:**
1. Review and approve PRD
2. Request complete Modbus register map from Dimplex
3. Set up development environment
4. Begin Phase 1 implementation


