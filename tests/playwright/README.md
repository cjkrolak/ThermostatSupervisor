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

- Node.js (v16 or later)
- npm (comes with Node.js)
- Running SHT31 Flask server (on http://127.0.0.1:5000 by default)

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

## Troubleshooting

### Tests fail with connection error
- Ensure the SHT31 Flask server is running
- Check that the server is accessible at the configured base URL
- Verify firewall settings allow connections to port 5000

### Browser not installed
Run:
```bash
npx playwright install chromium
```

### Tests timeout
- Increase timeout in `playwright.config.js`
- Check server response times
- Ensure the server is not overloaded
