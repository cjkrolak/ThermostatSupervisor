#!/usr/bin/env python3
"""
Start SHT31 Flask server in unit test mode for Playwright tests.

This script starts the SHT31 Flask server with mocked hardware for CI testing.
It spawns the server in unit test mode which generates fabricated sensor data.
"""

import sys
import os
import time

# Add repository root to Python path
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

# Set environment for unit test
os.environ['SHT31_REMOTE_IP_ADDRESS_99'] = 'mock_test_server'

try:
    # Import sht31 to spawn Flask server in unit test mode
    from thermostatsupervisor import sht31
    from thermostatsupervisor import sht31_config

    print('Spawning SHT31 Flask server in unit test mode...', flush=True)

    # Create thermostat instance with unit test zone
    # This automatically spawns Flask server
    thermostat = sht31.ThermostatClass(sht31_config.UNIT_TEST_ZONE)

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
    import traceback
    traceback.print_exc()
    sys.exit(1)
