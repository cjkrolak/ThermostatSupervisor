// @ts-check
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * Playwright global setup to start the SHT31 Flask server.
 *
 * This script automatically starts the SHT31 Flask server before tests run,
 * eliminating the need for manual server startup on Windows and other platforms.
 *
 * The server is started in unit test mode with mocked hardware for CI testing.
 */
async function globalSetup() {
  console.log('🚀 Starting SHT31 Flask server for Playwright tests...');

  // Determine Python command (python3 on Linux/Mac, python on Windows)
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  // Path to the server startup script
  const repoRoot = path.resolve(__dirname, '../..');
  const serverScript = path.join(
    __dirname,
    'start_sht31_test_server.py'
  );

  // Set up environment variables
  const env = {
    ...process.env,
    SHT31_REMOTE_IP_ADDRESS_99: 'mock_test_server',
    PLAYWRIGHT_TEST_MODE: '1',
    SKIP_RASPBERRY_PI_CHECK: '1',
    FLASK_ENV: 'testing',
    PYTHONPATH: repoRoot,
  };

  // Platform-specific server log and PID file paths
  const logFile = process.platform === 'win32'
    ? path.join(process.env.TEMP || 'C:\\Temp', 'sht31_server.log')
    : '/tmp/sht31_server.log';

  const pidFile = process.platform === 'win32'
    ? path.join(process.env.TEMP || 'C:\\Temp', 'sht31_server.pid')
    : '/tmp/sht31_server.pid';

  // Clean up old log and PID files
  [logFile, pidFile].forEach(file => {
    if (fs.existsSync(file)) {
      fs.unlinkSync(file);
    }
  });

  console.log(`Starting server with ${pythonCmd}...`);
  console.log(`Server script: ${serverScript}`);
  console.log(`Log file: ${logFile}`);

  // Start the server process
  const serverProcess = spawn(pythonCmd, [serverScript], {
    env,
    detached: process.platform !== 'win32', // Unix: detach for proper cleanup
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
  });

  // Write PID to file for teardown
  fs.writeFileSync(pidFile, serverProcess.pid.toString());

  // Capture server output to log file
  const logStream = fs.createWriteStream(logFile, { flags: 'w' });
  serverProcess.stdout.pipe(logStream);
  serverProcess.stderr.pipe(logStream);

  // Also log output to console for debugging
  serverProcess.stdout.on('data', (data) => {
    console.log(`[Server] ${data.toString().trim()}`);
  });

  serverProcess.stderr.on('data', (data) => {
    console.error(`[Server Error] ${data.toString().trim()}`);
  });

  // Handle server process exit
  serverProcess.on('exit', (code, signal) => {
    if (code !== null) {
      console.log(`Server process exited with code ${code}`);
    } else if (signal !== null) {
      console.log(`Server process killed with signal ${signal}`);
    }
  });

  // Wait for server to be ready by polling the /unit endpoint
  console.log('Waiting for server to be ready...');
  const maxAttempts = 30;
  const delayMs = 1000;

  for (let i = 0; i < maxAttempts; i++) {
    try {
      // Use fetch (Node 18+) or node-fetch for older versions
      const response = await fetch('http://127.0.0.1:5000/unit', {
        signal: AbortSignal.timeout(2000),
      });

      if (response.ok) {
        console.log(
          `✅ Server is ready and responding! (attempt ${i + 1})`
        );
        return;
      }
    } catch (error) {
      // Server not ready yet, continue waiting
      if (i === maxAttempts - 1) {
        console.error(
          `❌ Server failed to start after ${maxAttempts} attempts`
        );
        console.error(`Last error: ${error.message}`);

        // Print server logs
        if (fs.existsSync(logFile)) {
          console.error('Server logs:');
          const logs = fs.readFileSync(logFile, 'utf-8');
          console.error(logs);
        }

        // Kill the server process
        try {
          if (process.platform === 'win32') {
            execSync(`taskkill /F /PID ${serverProcess.pid}`, {
              stdio: 'ignore',
            });
          } else {
            process.kill(-serverProcess.pid, 'SIGKILL');
          }
        } catch (killError) {
          // Ignore kill errors
        }

        throw new Error('Failed to start SHT31 Flask server');
      }

      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
}

module.exports = globalSetup;
