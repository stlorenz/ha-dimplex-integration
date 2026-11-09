"""Tests for the Dimplex diagnostics download."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dimplex.const import CONF_HOST, CONF_PORT, DOMAIN
from custom_components.dimplex.diagnostics import async_get_config_entry_diagnostics
from custom_components.dimplex.modbus_registers import SoftwareVersion


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Keller",
        unique_id="192.168.1.73:502",
        data={CONF_HOST: "192.168.1.73", CONF_PORT: 502, "name": "Keller"},
        options={"cooling_enabled": False},
    )


@pytest.mark.asyncio
async def test_diagnostics_redacts_connection_details(hass: HomeAssistant):
    """Host and port must never leave the installation; everything else does."""
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = SimpleNamespace(
        software_version=SoftwareVersion.L_M,
        model="la1422c",
        slave_id=1,
        write_enabled=False,
        update_interval=timedelta(seconds=30),
        last_update_success=True,
        last_exception=None,
        data={"status": "heating", "flow_temperature": 37.7, "connected": True},
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["entry"]["title"] == "Keller"
    assert diag["entry"]["data"][CONF_HOST] == "**REDACTED**"
    assert diag["entry"]["data"][CONF_PORT] == "**REDACTED**"
    assert diag["entry"]["data"]["name"] == "Keller"
    assert diag["entry"]["options"] == {"cooling_enabled": False}

    coord = diag["coordinator"]
    assert coord["software_version"] == str(SoftwareVersion.L_M)
    assert coord["model"] == "la1422c"
    assert coord["slave_id"] == 1
    assert coord["write_enabled"] is False
    assert coord["update_interval"] == 30
    assert coord["last_update_success"] is True
    assert coord["last_exception"] is None
    assert coord["data"]["flow_temperature"] == 37.7


@pytest.mark.asyncio
async def test_diagnostics_reports_last_exception(hass: HomeAssistant):
    entry = _entry()
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = SimpleNamespace(
        software_version=SoftwareVersion.J,
        model="generic",
        slave_id=3,
        write_enabled=True,
        update_interval=None,
        last_update_success=False,
        last_exception=TimeoutError("no answer"),
        data=None,
    )

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["coordinator"]["update_interval"] is None
    assert diag["coordinator"]["last_update_success"] is False
    assert "no answer" in diag["coordinator"]["last_exception"]
    assert diag["coordinator"]["data"] is None


@pytest.mark.asyncio
async def test_diagnostics_without_loaded_coordinator(hass: HomeAssistant):
    """An entry that failed to set up still yields its (redacted) config."""
    entry = _entry()
    entry.add_to_hass(hass)

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert "coordinator" not in diag
    assert diag["entry"]["data"][CONF_HOST] == "**REDACTED**"
