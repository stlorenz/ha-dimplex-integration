"""Tests for the Dimplex climate platform."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.components.climate import ClimateEntityFeature, HVACMode

from custom_components.dimplex.climate import DimplexClimate
from custom_components.dimplex.modbus_registers import SoftwareVersion


def _make_entry(
    entry_id: str = "entry1", name: str = "Test Dimplex"
) -> SimpleNamespace:
    return SimpleNamespace(entry_id=entry_id, data={"name": name})


def _make_coordinator(
    *,
    software_version: SoftwareVersion,
    status: str = "off",
    cooling_enabled: bool = False,
    write_enabled: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        data={
            "status": status,
            "connected": True,
            "room_temperature": 21.5,
            "hc1_room_setpoint": 21.0,
        },
        software_version=software_version,
        cooling_enabled=cooling_enabled,
        write_enabled=write_enabled,
        model_name="Test Model",
        client=SimpleNamespace(write_register=AsyncMock(return_value=True)),
        async_request_refresh=AsyncMock(),
        last_update_success=True,
    )


def _make_entity(coordinator: SimpleNamespace) -> DimplexClimate:
    ent = DimplexClimate(coordinator, _make_entry())  # type: ignore[arg-type]
    ent.async_write_ha_state = Mock()  # not added to hass in unit tests
    return ent


def test_supported_features_disabled_when_registers_not_available():
    """For older software versions (H/J), control registers are not available."""
    coordinator = _make_coordinator(
        software_version=SoftwareVersion.H, status="heating"
    )
    entry = _make_entry()

    ent = DimplexClimate(coordinator, entry)  # type: ignore[arg-type]

    assert ent.supported_features == ClimateEntityFeature(0)
    # Even without control, we should still expose the observed mode
    assert ent.hvac_mode == HVACMode.HEAT
    assert ent.hvac_modes == [HVACMode.HEAT]


def test_supported_features_enabled_when_registers_available():
    """For L/M, registers exist and controls should be enabled."""
    coordinator = _make_coordinator(
        software_version=SoftwareVersion.L_M, status="off", cooling_enabled=True
    )
    entry = _make_entry()

    ent = DimplexClimate(coordinator, entry)  # type: ignore[arg-type]

    assert ent.supported_features & ClimateEntityFeature.TARGET_TEMPERATURE
    # Betriebsmodus (5015): OFF = Sommer, HEAT = Winter, COOL = Kuehlen
    assert ent.supported_features & ClimateEntityFeature.TURN_ON
    assert ent.supported_features & ClimateEntityFeature.TURN_OFF
    assert ent.hvac_modes == [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    assert ent.target_temperature == 21.0
    assert ent.current_temperature == 21.5


def test_hvac_mode_prefers_operating_mode_register():
    """The Betriebsmodus wins over the status message when both are known."""
    coordinator = _make_coordinator(
        software_version=SoftwareVersion.L_M, status="heating"
    )
    coordinator.data["operating_mode"] = "summer"
    ent = _make_entity(coordinator)
    assert ent.hvac_mode == HVACMode.OFF

    coordinator.data["operating_mode"] = "cooling"
    assert ent.hvac_mode == HVACMode.COOL

    del coordinator.data["operating_mode"]
    assert ent.hvac_mode == HVACMode.HEAT  # falls back to the status


@pytest.mark.asyncio
async def test_set_temperature_writes_register_when_enabled():
    """Room setpoint goes to register 46 (wiki: Raumtemperatur, 0.1 degC)."""
    coordinator = _make_coordinator(
        software_version=SoftwareVersion.L_M, status="off", write_enabled=True
    )
    ent = _make_entity(coordinator)
    await ent.async_set_temperature(temperature=22.5)

    coordinator.client.write_register.assert_awaited_once()
    _, kwargs = coordinator.client.write_register.await_args
    assert kwargs["address"] == 46
    assert kwargs["value"] == 225
    assert coordinator.data["hc1_room_setpoint"] == 22.5
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_temperature_is_clamped_to_documented_range():
    """The WPM accepts 15.0..30.0 degC only."""
    coordinator = _make_coordinator(
        software_version=SoftwareVersion.L_M, status="off", write_enabled=True
    )
    ent = _make_entity(coordinator)
    await ent.async_set_temperature(temperature=40)

    _, kwargs = coordinator.client.write_register.await_args
    assert kwargs["value"] == 300


@pytest.mark.asyncio
async def test_set_hvac_mode_writes_betriebsmodus():
    """OFF -> Sommer (0), HEAT -> Winter (1), COOL -> Kuehlen (5)."""
    coordinator = _make_coordinator(
        software_version=SoftwareVersion.L_M,
        status="off",
        write_enabled=True,
        cooling_enabled=True,
    )
    ent = _make_entity(coordinator)

    for mode, expected in ((HVACMode.OFF, 0), (HVACMode.HEAT, 1), (HVACMode.COOL, 5)):
        coordinator.client.write_register.reset_mock()
        await ent.async_set_hvac_mode(mode)
        _, kwargs = coordinator.client.write_register.await_args
        assert kwargs["address"] == 5015
        assert kwargs["value"] == expected


@pytest.mark.asyncio
async def test_set_hvac_mode_cool_refused_without_cooling():
    coordinator = _make_coordinator(
        software_version=SoftwareVersion.L_M,
        status="off",
        write_enabled=True,
        cooling_enabled=False,
    )
    ent = _make_entity(coordinator)
    await ent.async_set_hvac_mode(HVACMode.COOL)
    coordinator.client.write_register.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_temperature_no_write_when_disabled():
    """If write mode is disabled, we should not write."""
    coordinator = _make_coordinator(
        software_version=SoftwareVersion.L_M, status="off", write_enabled=False
    )
    entry = _make_entry()

    ent = DimplexClimate(coordinator, entry)  # type: ignore[arg-type]
    await ent.async_set_temperature(temperature=22.5)

    coordinator.client.write_register.assert_not_awaited()
