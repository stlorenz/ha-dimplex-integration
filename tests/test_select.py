"""Tests for the operating mode select entity (register 5015)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.dimplex.modbus_registers import SoftwareVersion
from custom_components.dimplex.select import (
    DimplexOperatingModeSelect,
    async_setup_entry,
)


def _coordinator(
    *,
    software_version=SoftwareVersion.L_M,
    write_enabled=True,
    cooling_enabled=False,
    mode="winter",
):
    return SimpleNamespace(
        software_version=software_version,
        write_enabled=write_enabled,
        cooling_enabled=cooling_enabled,
        model_name="LA 1422C (Air/Water)",
        data={"connected": True, "operating_mode": mode, "operating_mode_code": 1},
        client=SimpleNamespace(write_register=AsyncMock(return_value=True)),
        async_request_refresh=AsyncMock(),
        last_update_success=True,
    )


def _entry():
    return SimpleNamespace(entry_id="entry1", data={"name": "Test Dimplex"})


def _entity(coordinator) -> DimplexOperatingModeSelect:
    ent = DimplexOperatingModeSelect(coordinator, _entry(), 5015)  # type: ignore[arg-type]
    ent.async_write_ha_state = Mock()
    return ent


@pytest.mark.asyncio
async def test_setup_creates_select_for_lm_only():
    added: list = []
    hass = SimpleNamespace(data={"dimplex": {"entry1": _coordinator()}})
    await async_setup_entry(hass, _entry(), lambda ents: added.extend(ents))  # type: ignore[arg-type]
    assert len(added) == 1
    assert added[0].unique_id == "entry1_operating_mode"

    added.clear()
    hass = SimpleNamespace(
        data={"dimplex": {"entry1": _coordinator(software_version=SoftwareVersion.H)}}
    )
    await async_setup_entry(hass, _entry(), lambda ents: added.extend(ents))  # type: ignore[arg-type]
    assert added == []


def test_options_and_current_option():
    ent = _entity(_coordinator(mode="party"))
    assert ent.current_option == "party"
    assert "cooling" not in ent.options
    assert ent.options[:2] == ["summer", "winter"]

    ent = _entity(_coordinator(cooling_enabled=True))
    assert "cooling" in ent.options


@pytest.mark.asyncio
async def test_select_option_writes_register_5015():
    coordinator = _coordinator()
    ent = _entity(coordinator)

    await ent.async_select_option("vacation")

    coordinator.client.write_register.assert_awaited_once_with(address=5015, value=2)
    assert coordinator.data["operating_mode"] == "vacation"
    assert coordinator.data["operating_mode_code"] == 2
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_option_refused_when_write_disabled():
    coordinator = _coordinator(write_enabled=False)
    ent = _entity(coordinator)

    await ent.async_select_option("summer")

    coordinator.client.write_register.assert_not_awaited()
    assert coordinator.data["operating_mode"] == "winter"
