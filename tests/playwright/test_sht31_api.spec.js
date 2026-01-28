// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Playwright test suite for SHT31 Flask API endpoints.
 * 
 * This test suite validates the SHT31 temperature/humidity sensor
 * Flask API endpoints by making API requests and verifying responses.
 * 
 * Note: Some endpoints require actual SHT31 hardware and are marked with
 * test.skip() for CI environments. These include:
 * - /data (production sensor readings)
 * - /diag, /clear_diag (diagnostic register access)
 * - /enable_heater, /disable_heater (heater control)
 * - /soft_reset, /reset (hardware reset commands)
 * - /i2c_detect (without bus number)
 * - /i2c_logic_levels (GPIO pin levels)
 * - /i2c_recovery (I2C bus recovery)
 * 
 * Endpoints that work in CI (without hardware):
 * - /unit (unit test mock data)
 * - /i2c_detect/0, /i2c_detect/1 (simulated I2C bus scans)
 * - /i2c_bus_health (bus health check)
 * - /print_block_list, /clear_block_list (IP ban management)
 */

// Helper function to validate common response structure
function validateSensorData(data) {
  expect(data).toHaveProperty('measurements');
  expect(data).toHaveProperty('Temp(C) mean');
  expect(data).toHaveProperty('Temp(C) std');
  expect(data).toHaveProperty('Temp(F) mean');
  expect(data).toHaveProperty('Temp(F) std');
  expect(data).toHaveProperty('Humidity(%RH) mean');
  expect(data).toHaveProperty('Humidity(%RH) std');
  expect(data).toHaveProperty('rssi(dBm) mean');
  expect(data).toHaveProperty('rssi(dBm) std');
  
  // Validate data types and reasonable ranges
  expect(typeof data.measurements).toBe('number');
  expect(data.measurements).toBeGreaterThanOrEqual(0);
  
  expect(typeof data['Temp(F) mean']).toBe('number');
  expect(data['Temp(F) mean']).toBeGreaterThan(-50);
  expect(data['Temp(F) mean']).toBeLessThan(150);
  
  expect(typeof data['Humidity(%RH) mean']).toBe('number');
  expect(data['Humidity(%RH) mean']).toBeGreaterThanOrEqual(0);
  expect(data['Humidity(%RH) mean']).toBeLessThanOrEqual(100);
}

test.describe('SHT31 API Production Endpoints', () => {
  test.skip('GET /data returns production sensor measurements', async ({ request }) => {
    // This test requires actual SHT31 hardware
    const response = await request.get('/data');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    validateSensorData(data);
  });

  test('GET /unit returns unit test sensor measurements', async ({ request }) => {
    const response = await request.get('/unit');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    validateSensorData(data);
  });
});

test.describe('SHT31 API Diagnostic Endpoints', () => {
  test.skip('GET /diag returns diagnostic register data', async ({ request }) => {
    // This test requires actual SHT31 hardware
    const response = await request.get('/diag');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('raw_binary');
    expect(typeof data.raw_binary).toBe('string');
  });

  test.skip('GET /clear_diag clears diagnostic register', async ({ request }) => {
    // This test requires actual SHT31 hardware
    const response = await request.get('/clear_diag');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('raw_binary');
  });
});

test.describe('SHT31 API Heater Control Endpoints', () => {
  test.skip('GET /enable_heater enables sensor heater', async ({ request }) => {
    // This test requires actual SHT31 hardware
    const response = await request.get('/enable_heater');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('raw_binary');
  });

  test.skip('GET /disable_heater disables sensor heater', async ({ request }) => {
    // This test requires actual SHT31 hardware
    const response = await request.get('/disable_heater');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('raw_binary');
  });
});

test.describe('SHT31 API Reset Endpoints', () => {
  test.skip('GET /soft_reset performs soft reset', async ({ request }) => {
    // This test requires actual SHT31 hardware
    const response = await request.get('/soft_reset');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('raw_binary');
  });

  // Note: /reset endpoint is not tested as it performs a hard reset
  // which could interrupt ongoing tests
});

test.describe('SHT31 API I2C Diagnostic Endpoints', () => {
  test.skip('GET /i2c_detect detects I2C devices', async ({ request }) => {
    // This test requires actual I2C hardware
    const response = await request.get('/i2c_detect');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('i2c_detect');
    expect(typeof data.i2c_detect).toBe('string');
  });

  test('GET /i2c_detect/0 detects I2C devices on bus 0', async ({ request }) => {
    const response = await request.get('/i2c_detect/0');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('i2c_detect');
  });

  test('GET /i2c_detect/1 detects I2C devices on bus 1', async ({ request }) => {
    const response = await request.get('/i2c_detect/1');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('i2c_detect');
  });

  test.skip('GET /i2c_logic_levels returns I2C logic levels', async ({ request }) => {
    // This test requires actual GPIO hardware
    const response = await request.get('/i2c_logic_levels');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('i2c_logic_levels');
    expect(typeof data.i2c_logic_levels).toBe('string');
  });

  test('GET /i2c_bus_health returns I2C bus health status', async ({ request }) => {
    const response = await request.get('/i2c_bus_health');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('i2c_bus_health');
  });

  // Note: /i2c_recovery endpoint is not tested as it performs
  // recovery operations that could disrupt ongoing tests
});

test.describe('SHT31 API IP Ban Endpoints', () => {
  test('GET /print_block_list returns IP ban block list', async ({ request }) => {
    const response = await request.get('/print_block_list');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    // Response may be empty or contain blocked IPs
    const data = await response.json();
    expect(data).toBeDefined();
  });

  test('GET /clear_block_list clears IP ban block list', async ({ request }) => {
    const response = await request.get('/clear_block_list');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toBeDefined();
  });
});

test.describe('SHT31 API Error Handling', () => {
  test('GET /nonexistent returns 404', async ({ request }) => {
    const response = await request.get('/nonexistent');
    expect(response.status()).toBe(404);
  });

  test('POST /data is not allowed (GET only)', async ({ request }) => {
    const response = await request.post('/data', {
      data: { test: 'data' }
    });
    // Flask typically returns 405 for method not allowed
    expect(response.status()).toBe(405);
  });
});

test.describe('SHT31 API Response Time', () => {
  test.skip('/data endpoint responds within acceptable time', async ({ request }) => {
    // This test requires actual SHT31 hardware
    const startTime = Date.now();
    const response = await request.get('/data');
    const endTime = Date.now();
    const responseTime = endTime - startTime;
    
    expect(response.ok()).toBeTruthy();
    expect(responseTime).toBeLessThan(2000); // 2 seconds
  });

  test('/unit endpoint responds within acceptable time', async ({ request }) => {
    const startTime = Date.now();
    const response = await request.get('/unit');
    const endTime = Date.now();
    const responseTime = endTime - startTime;
    
    expect(response.ok()).toBeTruthy();
    expect(responseTime).toBeLessThan(2000); // 2 seconds
  });
});
