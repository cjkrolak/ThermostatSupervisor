# Site Supervise Feature

The Site Supervise feature enables monitoring and controlling multiple thermostats at a single site simultaneously. This provides site-level orchestration capability with support for per-thermostat settings and selective thermostat inclusion/exclusion.

## Overview

The `ThermostatSite` class provides a unified interface to:
- Monitor multiple thermostats concurrently using multi-threading
- Display zone information across all thermostats
- Query current temperatures and conditions from all zones
- Supervise all zones with independent settings per thermostat
- Exclude specific thermostats from site operations

## Quick Start

### Command-Line Usage

The easiest way to use site supervision is through the command-line interface:

```bash
# Use default site configuration
python -m src.site_supervise

# Display zones without running supervision
python -m src.site_supervise --display-zones

# Display current temperatures only
python -m src.site_supervise --display-temps

# Use custom configuration file
python -m src.site_supervise -c mysite.json

# Override measurement count for all thermostats
python -m src.site_supervise -n 10

# Disable multi-threading (for debugging)
python -m src.site_supervise --no-threading

# Run with quiet mode (less verbose)
python -m src.site_supervise -q

# Get help and see all options
python -m src.site_supervise --help
```

**Command-Line Options:**
- `-h, --help`: Display help message with all options
- `-c, --config CONFIG`: Path to site configuration JSON file (default: built-in config)
- `-n, --measurements N`: Number of measurements per thermostat (overrides config)
- `--threading`: Enable multi-threading for parallel supervision (default)
- `--no-threading`: Disable multi-threading (run sequentially)
- `-v, --verbose`: Enable verbose logging (default)
- `-q, --quiet`: Disable verbose logging
- `--display-zones`: Display all zones and exit (no supervision)
- `--display-temps`: Display current temperatures and exit (no supervision)

**Interrupting Supervision:**

You can gracefully exit site supervision at any time by pressing `CTRL-C`. This will:
- Abort the current supervision loop
- Log a message indicating user interruption
- Exit cleanly without leaving threads running

This is useful when you want to stop long-running supervision tasks without waiting for completion.

### Python API Usage

For programmatic control, use the Python API directly:

```python
from src import thermostat_site as ts

# Use default configuration
site = ts.ThermostatSite()

# Display all zones
site.display_all_zones()

# Display current temperatures
site.display_all_temps()

# Supervise all zones with multi-threading
results = site.supervise_all_zones(use_threading=True)
```

### Custom Configuration

Create a JSON configuration file for your site:

```python
from src import thermostat_site as ts

# Create custom site configuration
config = {
    "site_name": "my_home",
    "thermostats": [
        {
            "thermostat_type": "honeywell",
            "zone": 0,
            "enabled": True,
            "poll_time": 60,
            "tolerance": 2,
            "target_mode": "AUTO_MODE",
            "measurements": 10,
        },
        {
            "thermostat_type": "kumocloud",
            "zone": 1,
            "enabled": True,
            "poll_time": 30,
            "tolerance": 3,
            "target_mode": "HEAT_MODE",
            "measurements": 10,
        },
    ],
}

site = ts.ThermostatSite(site_config_dict=config)
site.supervise_all_zones(use_threading=True)
```

**Using JSON Configuration File:**

Create a JSON file (e.g., `mysite.json`) with your site configuration:

```json
{
    "site_name": "my_home",
    "thermostats": [
        {
            "thermostat_type": "honeywell",
            "zone": 0,
            "enabled": true,
            "poll_time": 60,
            "tolerance": 2,
            "target_mode": "AUTO_MODE",
            "measurements": 10
        },
        {
            "thermostat_type": "kumocloud",
            "zone": 1,
            "enabled": true,
            "poll_time": 30,
            "tolerance": 3,
            "target_mode": "HEAT_MODE",
            "measurements": 10
        }
    ]
}
```

Then use it from the command line:

```bash
python -m src.site_supervise -c mysite.json
```

Or load it programmatically:

```python
import json
from src import thermostat_site as ts

with open('mysite.json', 'r') as f:
    config = json.load(f)

site = ts.ThermostatSite(site_config_dict=config)
site.supervise_all_zones(use_threading=True)
```

## Configuration

### Site Configuration Dictionary

The site configuration is a Python dictionary with the following structure:

```python
{
    "site_name": "string",  # Name of the site
    "thermostats": [        # List of thermostat configurations
        {
            "thermostat_type": "string",  # Type (e.g., "honeywell", "kumocloud")
            "zone": int,                  # Zone number
            "enabled": bool,              # Include in supervision (default: True)
            "poll_time": int,             # Poll interval in seconds
            "connection_time": int,       # Connection timeout in seconds
            "tolerance": int,             # Temperature tolerance in degrees F
            "target_mode": "string",      # Target mode (e.g., "AUTO_MODE")
            "measurements": int,          # Number of measurements to take
        },
        # Additional thermostats...
    ],
}
```

### Configuration Fields

#### Site-Level Fields
- **site_name** (str): A descriptive name for the site
- **thermostats** (list): List of thermostat configuration dictionaries

#### Per-Thermostat Fields
- **thermostat_type** (str, required): Type of thermostat (must be in `SUPPORTED_THERMOSTATS`)
  - Supported types: `emulator`, `honeywell`, `kumocloud`, `kumocloudv3`, `kumolocal`, `mmm`, `nest`, `sht31`, `blink`
- **zone** (int, required): Zone number for the thermostat
- **enabled** (bool, optional): Whether to include this thermostat in supervision (default: `True`)
- **poll_time** (int, optional): Polling interval in seconds (default varies by thermostat)
- **connection_time** (int, optional): Connection timeout in seconds
- **tolerance** (int, optional): Temperature tolerance in degrees Fahrenheit
- **target_mode** (str, optional): Target operating mode
  - Valid modes: `OFF_MODE`, `HEAT_MODE`, `COOL_MODE`, `AUTO_MODE`, `DRY_MODE`, `FAN_MODE`, `ECO_MODE`
- **measurements** (int, optional): Number of measurements to take per supervision session

## ThermostatSite Class

### Constructor

```python
ThermostatSite(site_config_dict=None, verbose=True)
```

**Parameters:**
- `site_config_dict` (dict, optional): Site configuration dictionary. If None, uses default configuration.
- `verbose` (bool, optional): Enable verbose logging (default: True)

### Methods

#### `display_all_zones()`

Display all zones within the site, including their configuration and enabled/disabled status.

```python
site.display_all_zones()
```

**Output Example:**
```
============================================================
Site: my_home
============================================================

  Thermostat 1: [ENABLED]
    Type: honeywell
    Zone: 0
    Poll Time: 60s
    Tolerance: 2°F

  Thermostat 2: [DISABLED]
    Type: kumocloud
    Zone: 1
    Poll Time: 30s
    Tolerance: 3°F
============================================================
```

#### `display_all_temps()`

Query and display current temperatures and conditions from all enabled thermostats.

```python
site.display_all_temps()
```

**Output Example:**
```
============================================================
Site Temperature Summary: my_home
============================================================

  Thermostat 1:
    Type: honeywell
    Zone: Living Room
    Temperature: 72.0°F
    Humidity: 45%
    Mode: AUTO_MODE

  Thermostat 2:
    Type: kumocloud
    Zone: Bedroom
    Temperature: 68.5°F
    Humidity: 50%
    Mode: HEAT_MODE
============================================================
```

#### `supervise_all_zones(measurement_count=1, use_threading=True)`

Supervise all enabled zones within the site.

**Parameters:**
- `measurement_count` (int, optional): Default number of measurements per thermostat. This value is overridden by per-thermostat 'measurements' config if present. (default: 1)
- `use_threading` (bool, optional): Use multi-threading for parallel supervision (default: True)

**Returns:**
- `dict`: Dictionary with two keys:
  - `'results'`: Dict of measurement results keyed by thermostat/zone identifier. Each entry contains a **list** of measurement dictionaries.
  - `'errors'`: Dict of errors keyed by thermostat/zone identifier for any thermostats that failed during supervision.

**Example:**
```python
result = site.supervise_all_zones(use_threading=True)

# Results structure:
{
    "results": {
        "honeywell_zone0": [  # List of measurements
            {
                "timestamp": 1234567890.0,
                "measurement": 1,
                "temperature": 72.0,
                "humidity": 45.0,
                "mode": "AUTO_MODE",
                "thread": "Thread-1-honeywell-Zone0",
            },
            {
                "timestamp": 1234567950.0,
                "measurement": 2,
                "temperature": 72.5,
                "humidity": 46.0,
                "mode": "AUTO_MODE",
                "thread": "Thread-1-honeywell-Zone0",
            },
            # Additional measurements...
        ],
        "kumocloud_zone1": [
            # List of measurements for zone 1...
        ],
    },
    "errors": {
        # If any thermostats fail, they appear here
        "nest_zone0": {
            "error": "Connection timeout",
            "thread": "Thread-3-nest-Zone0",
            "timestamp": 1234567890.0,
        }
    }
}

# Access results safely
results = result.get("results", {})
errors = result.get("errors", {})

for thermostat_key, measurements in results.items():
    print(f"{thermostat_key}: {len(measurements)} measurements")
    for measurement in measurements:
        print(f"  Temp: {measurement['temperature']}°F")
```

## Multi-Threading

The site supervision feature uses Python's `threading` module to monitor multiple thermostats concurrently. This provides several benefits:

- **Parallel Execution**: All thermostats are queried simultaneously, reducing total supervision time
- **Independent Polling**: Each thermostat operates on its own poll schedule
- **Thread Safety**: Results are collected using thread-safe locks
- **Graceful Handling**: Errors in one thermostat don't affect others

### Threading Behavior

- Each enabled thermostat runs in its own thread
- Threads are non-daemon (will complete their work before program exit)
- Thread naming convention: `Thread-{id}-{type}-Zone{zone}`
- Thread-safe result collection using locks

### Disabling Multi-Threading

For debugging or testing, you can disable multi-threading:

```python
results = site.supervise_all_zones(use_threading=False)
```

This will supervise thermostats sequentially (one at a time).

## Thermostat Exclusion

You can exclude specific thermostats from site operations using the `enabled` flag:

```python
config = {
    "site_name": "my_home",
    "thermostats": [
        {
            "thermostat_type": "honeywell",
            "zone": 0,
            "enabled": True,  # This thermostat will be monitored
        },
        {
            "thermostat_type": "kumocloud",
            "zone": 1,
            "enabled": False,  # This thermostat will be excluded
        },
    ],
}
```

**Use Cases for Exclusion:**
- Temporarily disable monitoring of a specific zone
- Exclude thermostats that are offline or under maintenance
- Test site operations with a subset of thermostats
- Seasonal zone management (e.g., disable garage monitoring in winter)

## Example Script

A comprehensive example script is provided in `examples/site_supervise_example.py` that demonstrates:
- Basic site usage with default configuration
- Custom site configuration
- Thermostat exclusion via enabled flag
- Multi-threaded site supervision
- Results processing and display

Run the example:
```bash
cd ThermostatSupervisor  # Navigate to project root
PYTHONPATH=. python examples/site_supervise_example.py
```

## Integration with Existing Code

The site supervise feature integrates seamlessly with the existing thermostat infrastructure:

- Uses existing `ThermostatClass` and `ThermostatZone` implementations
- Leverages `thermostat_api` for library loading and validation
- Compatible with all supported thermostat types
- Follows existing configuration patterns
- Uses standard logging and error handling

## Error Handling

The site supervision feature includes robust error handling:

- **Missing Environment Variables**: Validates required environment variables before starting
- **Connection Failures**: Catches and logs connection errors per thermostat
- **Query Failures**: Gracefully handles query failures without stopping other thermostats
- **Thread Safety**: Uses locks to prevent race conditions in result collection
- **Cleanup**: Properly closes thermostat connections and cleans up resources

## Performance Considerations

### Multi-Threading Benefits
- **Reduced Total Time**: Parallel execution significantly reduces total supervision time
- **Example**: Supervising 5 thermostats with 60-second polls:
  - Sequential: ~5 minutes total
  - Multi-threaded: ~1 minute total (limited by slowest thermostat)

### Resource Usage
- **Memory**: Each thread requires minimal memory overhead
- **CPU**: API calls are I/O-bound, so CPU usage remains low
- **Network**: Each thermostat maintains its own connection

### Recommendations
- Use multi-threading for sites with 2+ thermostats
- Configure appropriate poll times to avoid overwhelming external APIs
- Consider thermostat-specific rate limits when configuring poll intervals

## Testing

Comprehensive unit tests are provided in `tests/test_thermostat_site.py`:

```bash
# Run all site supervise tests
python -m unittest tests.test_thermostat_site -v

# Run specific test
python -m unittest tests.test_thermostat_site.TestThermostatSite.test_supervise_all_zones_threaded -v
```

**Test Coverage:**
- Site initialization with default and custom configs
- Thermostat filtering (enabled/disabled)
- Zone display methods
- Temperature query methods
- Sequential and multi-threaded supervision
- Empty site handling
- Result collection and validation

## Future Enhancements

Possible future enhancements to the site supervise feature:

1. **Site-Level Scheduling**: Define supervision schedules at the site level
2. **Site-Level Rules**: Implement inter-thermostat coordination rules
3. **Energy Optimization**: Balance heating/cooling across zones for efficiency
4. **Persistence**: Save site configurations to file or database
5. **Web Interface**: Add Flask endpoints for site management
6. **Alerts**: Site-wide alert configuration and notification
7. **Analytics**: Site-level energy usage and trend analysis

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'src'`
**Solution**: Set PYTHONPATH before running:
```bash
PYTHONPATH=/path/to/ThermostatSupervisor python your_script.py
```

**Issue**: Thread errors or race conditions
**Solution**: Disable multi-threading temporarily for debugging:
```python
results = site.supervise_all_zones(use_threading=False)
```

**Issue**: Missing environment variables
**Solution**: Ensure all required environment variables are set for each thermostat type. See `supervisor-env.txt.example` for reference.

**Issue**: Some thermostats not responding
**Solution**: Check the `enabled` flag for each thermostat and verify network connectivity.

## Contributing

When contributing to the site supervise feature:

1. Follow existing code style and conventions
2. Add unit tests for new functionality
3. Update documentation for API changes
4. Ensure multi-threading safety
5. Handle errors gracefully
6. Use existing logging patterns

## License

This feature is part of the ThermostatSupervisor project and follows the same license terms.
