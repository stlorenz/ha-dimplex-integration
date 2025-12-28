"""Tests for the Dimplex switch platform."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.dimplex.switch import DimplexWriteEnableSwitch


@pytest.mark.asyncio
async def test_write_enable_switch_turns_on_off():
    """Test toggling write mode via switch."""
    state = {"write_enabled": False}

    def _set_write_enabled(enabled: bool) -> None:
        state["write_enabled"] = enabled

    coordinator = SimpleNamespace(
        write_enabled=False,
        set_write_enabled=_set_write_enabled,
        model_name="Test Model",
    )

    entry = SimpleNamespace(
        entry_id="entry1",
        data={"name": "Test Dimplex"},
    )

    ent = DimplexWriteEnableSwitch(coordinator, entry)  # type: ignore[arg-type]
    ent.async_write_ha_state = Mock()

    assert ent.is_on is False

    await ent.async_turn_on()
    coordinator.write_enabled = state["write_enabled"]
    assert ent.is_on is True

    await ent.async_turn_off()
    coordinator.write_enabled = state["write_enabled"]
    assert ent.is_on is False


@pytest.mark.asyncio
async def test_write_enable_switch_unique_id_and_device_info():
    """Test stable identifiers."""
    coordinator = SimpleNamespace(
        write_enabled=False,
        set_write_enabled=Mock(),
        model_name="Test Model",
    )
    entry = SimpleNamespace(entry_id="entry1", data={"name": "Test Dimplex"})

    ent = DimplexWriteEnableSwitch(coordinator, entry)  # type: ignore[arg-type]

    assert ent.unique_id == "entry1_write_enable"
    assert ent.device_info is not None


