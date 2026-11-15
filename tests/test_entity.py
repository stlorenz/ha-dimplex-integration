"""Tests for the shared device info."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.dimplex.entity import build_device_info
from custom_components.dimplex.modbus_registers import SoftwareVersion


def _entry():
    return SimpleNamespace(entry_id="entry1", data={"name": "Test Dimplex"})


def test_device_info_prefers_version_read_from_the_wpm():
    coordinator = SimpleNamespace(
        software_version=SoftwareVersion.L_M,
        model_name="LA 1422C (Air/Water)",
        controller_software="M3.16",
    )
    info = build_device_info(coordinator, _entry())
    assert info["sw_version"] == "WPM M3.16"
    assert info["model"] == "LA 1422C (Air/Water)"
    assert info["manufacturer"] == "Dimplex"


def test_device_info_falls_back_to_configured_family():
    coordinator = SimpleNamespace(
        software_version=SoftwareVersion.J, model_name="x", controller_software=None
    )
    assert build_device_info(coordinator, _entry())["sw_version"] == "WPM J"
    coordinator = SimpleNamespace(software_version=SoftwareVersion.L_M, model_name="x")
    assert build_device_info(coordinator, _entry())["sw_version"] == "WPM L/M"
