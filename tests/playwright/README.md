# Playwright Test Suite for SHT31 API

This directory contains Playwright end-to-end tests for the SHT31 Flask API endpoints.

## Overview

The test suite validates the following SHT31 API endpoints:

### Endpoints tested in CI (without hardware):
- `/unit` - Unit test sensor measurements (fabricated data)
- `/i2c_detect/0` - Detect I2C devices on bus 0 (simulated)
- `/i2c_detect/1` - Detect I2C devices on bus 1 (simulated)
- `/i2c_bus_health` - Get I2C bus health status
- `/print_block_list` - Get IP ban block list
- `/clear_block_list` - Clear IP ban block list
- Error handling (404, 405 responses)

### Endpoints requiring hardware (skipped in CI):
- `/data` - Production sensor measurements (requires SHT31 hardware)
- `/diag` - Diagnostic register data (requires SHT31 hardware)
- `/clear_diag` - Clear diagnostic register (requires SHT31 hardware)
- `/enable_heater` - Enable sensor heater (requires SHT31 hardware)
- `/disable_heater` - Disable sensor heater (requires SHT31 hardware)
- `/soft_reset` - Perform soft reset (requires SHT31 hardware)
- `/i2c_detect` - Detect I2C devices (requires hardware without bus number)
- `/i2c_logic_levels` - Get I2C logic levels (requires GPIO hardware)

Tests for hardware-dependent endpoints are marked with `test.skip()` and can be
enabled on systems with actual SHT31 hardware.

## Prerequisites

- Node.js (v18 or later recommended)
- npm (comes with Node.js)
- Python 3.13 (or compatible version)
- Python dependencies installed (`pip install -r requirements.txt requirements_sht31.txt`)

**Note:** The SHT31 Flask server is automatically started and stopped by Playwright's
global setup/teardown hooks. You do not need to manually start the server.

## Installation

```bash
cd tests/playwright
npm install
npx playwright install chromium
```

## Running Tests

### Run all tests
```bash
npm test
```

### Run tests in headed mode (visible browser)
```bash
npm run test:headed
```

### Run tests in debug mode
```bash
npm run test:debug
```

### View test report
```bash
npm run test:report
```

## Configuration

The Playwright configuration is in `playwright.config.js`. You can customize:
- Base URL for the SHT31 server (default: http://127.0.0.1:5000)
- Timeout settings
- Reporter options
- Browser selection

To override the base URL, set the `SHT31_BASE_URL` environment variable:
```bash
SHT31_BASE_URL=http://localhost:8000 npm test
```

## CI/CD Integration

The tests are automatically run by the GitHub Actions workflow 
`.github/workflows/playwright-sht31-tests.yml` when:
- Changes are made to Playwright test files (`tests/playwright/**/*.spec.js`)
- Changes are made to SHT31 Python code (`src/sht31*.py`)

## Test Structure

- `test_sht31_api.spec.js` - Main test file containing all endpoint tests
- `playwright.config.js` - Playwright configuration
- `package.json` - Node.js dependencies and scripts

## How It Works

The test suite uses Playwright's global setup and teardown hooks to automatically:
1. Start the SHT31 Flask server in unit test mode before tests run
2. Wait for the server to be ready and responding
3. Run all test suites
4. Stop the server after tests complete

This works on all platforms including Windows, Linux, and macOS.

## Troubleshooting

### Tests fail with connection error
- Check that Python dependencies are installed: `pip install -r requirements.txt requirements_sht31.txt`
- Verify Python is in your PATH (`python3` or `python` depending on platform)
- Check server logs at `/tmp/sht31_server.log` (Linux/Mac) or `%TEMP%\sht31_server.log` (Windows)
- Verify firewall settings allow connections to port 5000
- Ensure port 5000 is not already in use by another application

### Browser not installed
Run:
```bash
npx playwright install chromium
```

### Tests timeout
- Increase timeout in `playwright.config.js`
- Check server response times
- Ensure the server is not overloaded
