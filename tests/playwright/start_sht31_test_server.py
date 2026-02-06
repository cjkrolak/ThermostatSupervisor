#!/usr/bin/env python3
"""
Start SHT31 Flask server in unit test mode for Playwright tests.

This script starts the SHT31 Flask server with mocked hardware for CI testing.
It spawns the server in unit test mode which generates fabricated sensor data.
"""

import sys
import os
import time
import traceback

# Add repository root to Python path
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

# Set environment for unit test - this bypasses Raspberry Pi checks
os.environ['SHT31_REMOTE_IP_ADDRESS_99'] = 'mock_test_server'
os.environ['PLAYWRIGHT_TEST_MODE'] = '1'  # Signal test mode
os.environ['SKIP_RASPBERRY_PI_CHECK'] = '1'  # Skip all Raspberry Pi checks

try:
    print('DEBUG: Starting Flask server initialization...', flush=True)

    # Import utilities first and set unit test mode
    from src import utilities as util
    util.unit_test_mode = True
    print('DEBUG: Set util.unit_test_mode = True', flush=True)

    # Patch the environment check to bypass Raspberry Pi detection in test mode
    # We need to patch it in sys.modules so it persists through importlib.reload()
    from src import environment as env

    def mock_is_raspberrypi_environment(verbose=False):
        """Mock version that always returns True for unit testing."""
        if verbose:
            msg = "Mock: raspberry pi environment check bypassed for unit testing"
            print(msg, flush=True)
        msg2 = 'DEBUG: mock_is_raspberrypi_environment called, returning True'
        print(msg2, flush=True)
        # Print call stack to see where it's being called from
        print('DEBUG: Call stack:', flush=True)
        for line in traceback.format_stack()[:-1]:
            print(line.strip(), flush=True)
        return True

    # Patch in the environment module
    env.is_raspberrypi_environment = mock_is_raspberrypi_environment

    # Also patch in sys.modules to ensure it persists through reloads
    env_mod = sys.modules['src.environment']
    env_mod.is_raspberrypi_environment = mock_is_raspberrypi_environment
    msg = 'DEBUG: Patched env.is_raspberrypi_environment in module and sys.modules'
    print(msg, flush=True)

    # Verify the patch is in place
    test_result = env.is_raspberrypi_environment(verbose=True)
    msg = f'DEBUG: Test call to is_raspberrypi_environment returned: {test_result}'
    print(msg, flush=True)

    # Import sht31 to spawn Flask server in unit test mode
    print('DEBUG: About to import sht31 module...', flush=True)
    from src import sht31
    from src import sht31_config
    print('DEBUG: Successfully imported sht31 modules', flush=True)

    print('Spawning SHT31 Flask server in unit test mode...', flush=True)

    # Verify patch is still in place before creating ThermostatClass
    print('DEBUG: Verifying patch before ThermostatClass creation...', flush=True)
    test_result_2 = env.is_raspberrypi_environment(verbose=True)
    print(f'DEBUG: Second test call returned: {test_result_2}', flush=True)

    # Also verify it's still in sys.modules
    from src import environment as env2
    test_result_3 = env2.is_raspberrypi_environment(verbose=True)
    print(f'DEBUG: Test via reimport returned: {test_result_3}', flush=True)

    # Create thermostat instance with unit test zone
    # This automatically spawns Flask server
    print('DEBUG: About to create ThermostatClass...', flush=True)
    try:
        thermostat = sht31.ThermostatClass(sht31_config.UNIT_TEST_ZONE)
        print('DEBUG: ThermostatClass created successfully!', flush=True)
    except Exception as init_error:
        print(f'DEBUG: Exception during ThermostatClass init: {init_error}', flush=True)
        print(f'DEBUG: Exception type: {type(init_error).__name__}', flush=True)
        print(f'DEBUG: Exception args: {init_error.args}', flush=True)
        print('DEBUG: Full traceback:', flush=True)
        traceback.print_exc()
        # Re-raise to let outer handler catch it
        raise

    alive = thermostat.flask_server.is_alive()
    print(f'Flask server thread alive: {alive}', flush=True)

    # Wait for server to be ready
    import requests
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get('http://127.0.0.1:5000/unit', timeout=2)
            if response.status_code == 200:
                print(f'✅ Server is ready! (attempt {i+1})', flush=True)
                break
        except Exception as e:
            if i < max_attempts - 1:
                time.sleep(1)
            else:
                msg = f'❌ Server failed to start after {max_attempts} attempts'
                print(msg, flush=True)
                print(f'Last error: {e}', flush=True)
                sys.exit(1)

    # Keep the server running by sleeping indefinitely
    print('Server is running. Keeping alive...', flush=True)
    while True:
        time.sleep(10)

except Exception as e:
    print(f'❌ ERROR starting server: {e}', flush=True)
    traceback.print_exc()
    sys.exit(1)
