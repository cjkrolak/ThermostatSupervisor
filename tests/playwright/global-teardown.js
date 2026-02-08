// @ts-check
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * Playwright global teardown to stop the SHT31 Flask server.
 *
 * This script automatically stops the SHT31 Flask server after tests complete,
 * ensuring proper cleanup on all platforms including Windows.
 */
async function globalTeardown() {
  console.log('🛑 Stopping SHT31 Flask server...');

  // Platform-specific PID file path
  const pidFile = process.platform === 'win32'
    ? path.join(process.env.TEMP || 'C:\\Temp', 'sht31_server.pid')
    : '/tmp/sht31_server.pid';

  // Read PID from file
  if (!fs.existsSync(pidFile)) {
    console.log('No PID file found, server may not be running');
    return;
  }

  const pid = fs.readFileSync(pidFile, 'utf-8').trim();
  console.log(`Found server PID: ${pid}`);

  try {
    if (process.platform === 'win32') {
      // Windows: Use taskkill to stop the process
      console.log(`Killing process ${pid} on Windows...`);
      try {
        execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
        console.log('✅ Server process terminated');
      } catch (error) {
        // Process may already be dead
        console.log('Process may already be terminated');
      }

      // Also try to kill any Python processes running the server
      try {
        execSync(
          'taskkill /F /IM python.exe /FI "WINDOWTITLE eq *sht31*"',
          { stdio: 'ignore' }
        );
      } catch (error) {
        // Ignore errors - processes may not exist
      }
    } else {
      // Unix-like: Use kill to stop the process group
      console.log(`Killing process group ${pid} on Unix...`);
      try {
        process.kill(-parseInt(pid), 'SIGTERM');
        await new Promise((resolve) => setTimeout(resolve, 2000));

        // Force kill if still running
        process.kill(-parseInt(pid), 'SIGKILL');
        console.log('✅ Server process terminated');
      } catch (error) {
        // Process may already be dead
        console.log('Process may already be terminated');
      }
    }
  } catch (error) {
    console.error(`Error stopping server: ${error.message}`);
  }

  // Clean up PID file
  try {
    fs.unlinkSync(pidFile);
    console.log('Cleaned up PID file');
  } catch (error) {
    console.error(`Error removing PID file: ${error.message}`);
  }

  console.log('Server shutdown complete');
}

module.exports = globalTeardown;
