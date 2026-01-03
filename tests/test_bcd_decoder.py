"""Tests for 12-digit counter decoding."""

from __future__ import annotations

from custom_components.dimplex.modbus_registers_extended import decode_digits_12


def test_decode_digits_12_ok():
    # base-10,000 chunks: [1-4, 5-8, 9-12]
    assert decode_digits_12([2690, 5, 0]) == 52690
    assert decode_digits_12([1234, 5678, 9012]) == 901256781234


def test_decode_digits_12_invalid_chunk():
    assert decode_digits_12([10000, 0, 0]) is None

