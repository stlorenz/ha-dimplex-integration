"""Tests for the Dimplex climate platform."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.components.climate import ClimateEntityFeature, HVACMode

from custom_components.dimplex.climate import DimplexClimate
from custom_components.dimplex.modbus_registers import SoftwareVersion


def _make_entry(entry_id: str = "entry1", name: str = "Test Dimplex") -> SimpleNamespace:
    return SimpleNamespace(entry_id=entry_id, data={"name": name})


def _make_coordinator(
    *,
    software_version: SoftwareVersion,
    status: str = "off",
    cooling_enabled: bool = False,
    write_enabled: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        data={"status": status, "connected": True, "room_temperature": 21.5},
        software_version=software_version,
        cooling_enabled=cooling_enabled,
        write_enabled=write_enabled,
        model_name="Test Model",
        client=SimpleNamespace(write_register=AsyncMock(return_value=True)),
        async_request_refresh=AsyncMock(),
    )


def test_supported_features_disabled_when_registers_not_available():
    """For older software versions (H/J), control registers are not available."""
    coordinator = _make_coordinator(software_version=SoftwareVersion.H, status="heating")
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
    assert ent.supported_features & ClimateEntityFeature.TURN_ON
    assert ent.supported_features & ClimateEntityFeature.TURN_OFF
    assert ent.hvac_modes == [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]


@pytest.mark.asyncio
async def test_set_temperature_writes_register_when_enabled():
    """When write mode enabled and register exists, we should write scaled value."""
    coordinator = _make_coordinator(
        software_version=SoftwareVersion.L_M, status="off", write_enabled=True
    )
    entry = _make_entry()

    ent = DimplexClimate(coordinator, entry)  # type: ignore[arg-type]
    await ent.async_set_temperature(temperature=22.5)

    coordinator.client.write_register.assert_awaited_once()
    args, kwargs = coordinator.client.write_register.await_args
    assert kwargs["address"] == 200  # HC1_COMFORT_SETPOINT for L/M
    assert kwargs["value"] == 225
    coordinator.async_request_refresh.assert_awaited_once()


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


