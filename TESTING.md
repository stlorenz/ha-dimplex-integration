

# Testing Guide - Dimplex Heat Pump Integration

This document describes how to run and maintain tests for the Dimplex integration.

## Test Suite Overview

163 unit tests (88 % coverage) across:

- **Register map** (`test_modbus_registers.py`, `test_modbus_registers_extended.py`,
  `test_hot_water_settings.py`, `test_bcd_decoder.py`) - addresses against the Dimplex wiki,
  scaling/offset encoding, 12-digit counters, coil blocks
- **Modbus client** (`test_modbus_client.py`) - connection, registers, coils, writes,
  `read_operating_data` incl. derived values
- **Coordinator** (`test_coordinator.py`) - updates, failures, timeouts, backoff
- **Config / options flow** (`test_config_flow.py`)
- **Platforms** (`test_sensor.py`, `test_binary_sensor.py`, `test_climate.py`,
  `test_number.py`, `test_select.py`, `test_switch.py`)
- **Services** (`test_services.py`) - raw register access, diagnose, time programme
- **Integration init** (`test_init.py`)

Requirements: Python 3.13 or newer (Home Assistant 2026.x). The CI runs the same
suite plus `black --check`, `isort --check-only` and `ruff check` (configured in
`pyproject.toml`).

---

## Running Tests

### Quick Start

#### Using the Test Script (Recommended)

```bash
chmod +x run_tests.sh
./run_tests.sh
```

This script will:
1. Create a virtual environment (if needed)
2. Install all dependencies
3. Run all tests with coverage
4. Generate HTML coverage report

#### Manual Test Run

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements_test.txt

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_modbus_client.py

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=custom_components.dimplex --cov-report=html
```

### Test Options

#### Run Specific Tests

```bash
# Run single test file
pytest tests/test_modbus_client.py

# Run specific test function
pytest tests/test_modbus_client.py::test_client_connect_success

# Run tests matching pattern
pytest tests/ -k "sensor"
```

#### Coverage Reports

```bash
# Generate HTML coverage report
pytest tests/ --cov=custom_components.dimplex --cov-report=html
# Open htmlcov/index.html in browser

# Terminal coverage report
pytest tests/ --cov=custom_components.dimplex --cov-report=term-missing

# XML coverage report (for CI)
pytest tests/ --cov=custom_components.dimplex --cov-report=xml
```

#### Verbose Output

```bash
# Show test names
pytest tests/ -v

# Show print statements
pytest tests/ -s

# Show local variables on failure
pytest tests/ -l
```

---

## Test Structure

### Fixtures (`tests/conftest.py`)

Common test fixtures available to all tests:

- `mock_modbus_client` - Mocked Modbus TCP client
- `mock_setup_entry` - Mocked setup entry
- `mock_config_entry` - Sample configuration data
- `mock_dimplex_coordinator` - Mocked coordinator with data

### Test Patterns

#### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_example(hass: HomeAssistant):
    """Test async function."""
    result = await some_async_function()
    assert result is True
```

#### Mocking Modbus Responses

```python
with patch("custom_components.dimplex.modbus_client.AsyncModbusTcpClient") as mock:
    mock_instance = Mock()
    mock_response = Mock()
    mock_response.isError.return_value = False
    mock_response.registers = [100]
    mock_instance.read_holding_registers = AsyncMock(return_value=mock_response)
    mock.return_value = mock_instance
    
    # Your test code here
```

---

## Continuous Integration

### GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/tests.yml`) that:

1. **Runs tests** on Python 3.11 and 3.12
2. **Checks code quality** with black, isort, ruff, mypy
3. **Uploads coverage** to Codecov
4. **Runs on** push to main/develop and all pull requests

### CI Status

After pushing to GitHub, you can add badges to your README:

```markdown
![Tests](https://github.com/stlorenz/ha-dimplex-integration/actions/workflows/tests.yml/badge.svg)
![Coverage](https://codecov.io/gh/stlorenz/ha-dimplex-integration/branch/main/graph/badge.svg)
```

---

## Code Coverage

### Current Coverage Target

**Target: 80%+ code coverage**

### Viewing Coverage

After running tests with coverage:

```bash
# HTML report (most detailed)
open htmlcov/index.html

# Terminal summary
pytest tests/ --cov=custom_components.dimplex --cov-report=term

# Missing lines
pytest tests/ --cov=custom_components.dimplex --cov-report=term-missing
```

### Coverage Configuration

Coverage settings in `.coveragerc`:
- Excludes test files
- Excludes common patterns (if __name__, TYPE_CHECKING, etc.)
- Measures only `custom_components/dimplex/`

---

## Adding New Tests

### When to Add Tests

Add tests when:
- Adding new features
- Adding new entity types
- Adding new Modbus registers
- Fixing bugs (add test that would have caught it)

### Test Template

```python
"""Tests for new feature."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch
import pytest
from homeassistant.core import HomeAssistant

from custom_components.dimplex.your_module import YourClass


@pytest.mark.asyncio
async def test_your_feature(hass: HomeAssistant, mock_dimplex_coordinator):
    """Test your new feature."""
    # Arrange
    your_object = YourClass(mock_dimplex_coordinator)
    
    # Act
    result = await your_object.do_something()
    
    # Assert
    assert result == expected_value
```

### Best Practices

1. **One assertion per test** (when possible)
2. **Clear test names** - describe what's being tested
3. **Arrange-Act-Assert** pattern
4. **Mock external dependencies**
5. **Test both success and failure cases**
6. **Test edge cases**

---

## Testing with Real Hardware

### Integration Testing

To test with actual Dimplex hardware:

1. **Copy integration** to Home Assistant `custom_components/`
2. **Enable debug logging** in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.dimplex: debug
```

3. **Add integration** via UI
4. **Monitor logs** for errors:

```bash
tail -f /config/home-assistant.log | grep dimplex
```

### Manual Test Checklist

- [ ] Connection establishes successfully
- [ ] Status sensor shows correct state
- [ ] Lock sensor updates correctly
- [ ] Error sensor responds to faults
- [ ] Binary sensors change state appropriately
- [ ] Connection recovery after network interruption
- [ ] Connection recovery after device restart
- [ ] No errors in Home Assistant logs
- [ ] Entities have correct device info
- [ ] Polling continues without memory leaks

---

## Troubleshooting Tests

### Common Issues

#### Import Errors

```
ModuleNotFoundError: No module named 'custom_components'
```

**Solution:** Install test requirements
```bash
pip install -r requirements_test.txt
```

#### Async Test Failures

```
RuntimeError: Event loop is closed
```

**Solution:** Ensure test is marked with `@pytest.mark.asyncio`

#### Mock Not Working

```
AssertionError: Expected call not made
```

**Solution:** Check mock is patched at correct import path

#### Coverage Not Generated

```
Coverage.py warning: No data was collected
```

**Solution:** Ensure pytest-cov is installed and paths are correct

### Debug Mode

Run tests with debugging:

```bash
# Drop into debugger on failure
pytest tests/ --pdb

# Run last failed tests
pytest tests/ --lf

# Show all output
pytest tests/ -vvs
```

---

## Test Maintenance

### Regular Tasks

- **Run tests before commits**
- **Keep coverage above 80%**
- **Update tests when modifying code**
- **Add tests for bug fixes**
- **Review test failures in CI**

### Test Dependencies

Update test dependencies:

```bash
# Check for outdated packages
pip list --outdated

# Update requirements
pip install --upgrade pytest pytest-asyncio pytest-cov

# Regenerate requirements
pip freeze > requirements_test.txt
```

---

## Performance Testing

### Test Execution Time

```bash
# Show slowest tests
pytest tests/ --durations=10

# Timeout slow tests
pytest tests/ --timeout=5
```

### Memory Testing

For memory leak detection:

```bash
# Install memory profiler
pip install pytest-memprof

# Run with memory profiling
pytest tests/ --memprof
```

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Home Assistant Testing](https://developers.home-assistant.io/docs/development_testing)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

## Test Statistics

**Last Updated:** November 20, 2025

| Metric | Value |
|--------|-------|
| Total Tests | 53+ |
| Test Files | 7 |
| Code Coverage | Target: 80%+ |
| Test Execution Time | ~5-10 seconds |
| Python Versions | 3.11, 3.12 |

---

## Support

For test-related issues:
- Check this guide first
- Review existing test files for examples
- Check GitHub Actions logs for CI failures
- Open an issue if stuck

Happy testing! 🧪

