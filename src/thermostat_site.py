"""
ThermostatSite class for managing multiple thermostats at a single site.

This module provides site-level orchestration for monitoring and
controlling multiple thermostats simultaneously with multi-threading
support.
"""

# built-ins
from datetime import datetime
import threading
import time
from typing import Dict, Optional

# local imports
from src import site_config
from src import thermostat_api as api
from src import thermostat_common as tc
from src import utilities as util


class ThermostatSite:
    """
    Manage multiple thermostats at a single site.

    This class provides orchestration for monitoring multiple thermostats
    simultaneously, with support for per-thermostat settings and selective
    thermostat inclusion/exclusion.
    """

    def __init__(
        self,
        site_config_dict: Optional[Dict] = None,
        verbose: bool = True
    ):
        """
        Initialize ThermostatSite with configuration.

        Args:
            site_config_dict (dict, optional): Site configuration dictionary
                with thermostats and their settings. Defaults to None which
                uses the default site configuration.
            verbose (bool, optional): Enable verbose logging. Defaults to True.

        Raises:
            ValueError: If site_config_dict is malformed or missing required
                fields.
        """
        self.verbose = verbose
        self.site_config = (
            site_config_dict
            if site_config_dict
            else site_config.get_default_site_config()
        )

        # Validate configuration structure
        self._validate_config()

        self.site_name = self.site_config.get(
            "site_name", "unnamed_site"
        )
        self.thermostats = []
        # Shared measurement cache updated from multiple supervision threads
        self.measurement_results = {}
        # Lock protects concurrent access to measurement_results across
        # multiple threads during supervision operations
        self._lock = threading.Lock()
        # Track thread errors for reporting
        self.thread_errors = {}

        # Validate and initialize thermostats
        self._initialize_thermostats()

    def _validate_config(self):
        """
        Validate site configuration structure.

        Raises:
            ValueError: If configuration is malformed or missing required
                fields.
        """
        if not isinstance(self.site_config, dict):
            raise ValueError(
                "site_config_dict must be a dictionary"
            )

        if "thermostats" not in self.site_config:
            raise ValueError(
                "site_config_dict must contain 'thermostats' key"
            )

        if not isinstance(self.site_config["thermostats"], list):
            raise ValueError(
                "'thermostats' must be a list"
            )

        # Validate each thermostat configuration
        for idx, tstat in enumerate(self.site_config["thermostats"]):
            if not isinstance(tstat, dict):
                raise ValueError(
                    f"Thermostat config at index {idx} must be a dictionary"
                )

            required_fields = ["thermostat_type", "zone"]
            for field in required_fields:
                if field not in tstat:
                    raise ValueError(
                        f"Thermostat config at index {idx} missing required "
                        f"field: '{field}'"
                    )

    def _initialize_thermostats(self):
        """
        Initialize thermostat configurations.

        This method validates the site configuration and prepares the list
        of thermostats to be monitored.
        """
        thermostat_configs = self.site_config.get("thermostats", [])

        if not thermostat_configs:
            util.log_msg(
                "WARNING: No thermostats configured in site",
                mode=util.BOTH_LOG,
                func_name=1,
            )
            return

        # Filter to only enabled thermostats
        self.thermostats = [
            tstat for tstat in thermostat_configs if tstat.get("enabled", True)
        ]

        if self.verbose:
            util.log_msg(
                f"Site '{self.site_name}': initialized with "
                f"{len(self.thermostats)} thermostats "
                f"({len(thermostat_configs) - len(self.thermostats)} "
                f"disabled)",
                mode=util.BOTH_LOG,
                func_name=1,
            )

    def display_all_zones(self) -> None:
        """
        Display all zones within the site.

        Lists all configured thermostats and their zones, including status
        (enabled/disabled).
        """
        util.log_msg(
            f"\n{'='*60}\nSite: {self.site_name}\n{'='*60}",
            mode=util.BOTH_LOG,
        )

        all_thermostats = self.site_config.get("thermostats", [])
        if not all_thermostats:
            util.log_msg(
                "No thermostats configured in site",
                mode=util.BOTH_LOG,
            )
            return

        for idx, tstat in enumerate(all_thermostats, 1):
            status = "ENABLED" if tstat.get("enabled", True) else "DISABLED"
            util.log_msg(
                f"\n  Thermostat {idx}: [{status}]\n"
                f"    Type: {tstat.get('thermostat_type', 'unknown')}\n"
                f"    Zone: {tstat.get('zone', 'unknown')}\n"
                f"    Poll Time: {tstat.get('poll_time', 'N/A')}s\n"
                f"    Tolerance: {tstat.get('tolerance', 'N/A')}"
                f"{tc.DEGREE_SIGN}F",
                mode=util.BOTH_LOG,
            )

        util.log_msg(f"{'='*60}\n", mode=util.BOTH_LOG)

    def display_all_temps(self) -> None:
        """
        Display temperatures from all zones within the site.

        Queries each enabled thermostat and displays current temperature
        and humidity readings.
        """
        util.log_msg(
            f"\n{'='*60}\nSite Temperature Summary: {self.site_name}\n"
            f"{'='*60}",
            mode=util.BOTH_LOG,
        )

        if not self.thermostats:
            util.log_msg(
                "No enabled thermostats to query",
                mode=util.BOTH_LOG,
            )
            return

        for idx, tstat_config in enumerate(self.thermostats, 1):
            thermostat_type = tstat_config.get("thermostat_type")
            zone_num = tstat_config.get("zone")

            try:
                # Load the thermostat library
                mod = api.load_hardware_library(thermostat_type)

                # Create thermostat and zone objects
                Thermostat = mod.ThermostatClass(zone_num)
                Zone = mod.ThermostatZone(Thermostat)

                # Query current conditions
                Zone.query_thermostat_zone()

                # Display results
                temp = Zone.display_temp
                humidity = Zone.display_humidity
                mode = Zone.current_mode

                util.log_msg(
                    f"\n  Thermostat {idx}:\n"
                    f"    Type: {thermostat_type}\n"
                    f"    Zone: {Zone.zone_name}\n"
                    f"    Temperature: {temp}{tc.DEGREE_SIGN}F\n"
                    f"    Humidity: {humidity}%\n"
                    f"    Mode: {mode}",
                    mode=util.BOTH_LOG,
                )

                # Clean up
                if hasattr(Thermostat, "close"):
                    Thermostat.close()
                del Zone
                del Thermostat

            except Exception as ex:
                util.log_msg(
                    f"\n  Thermostat {idx}: ERROR\n"
                    f"    Type: {thermostat_type}\n"
                    f"    Zone: {zone_num}\n"
                    f"    Error: {str(ex)}",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )

        util.log_msg(f"{'='*60}\n", mode=util.BOTH_LOG)

    def _supervise_single_thermostat(
        self,
        tstat_config: Dict,
        thread_id: int,
        measurement_count: int = 1
    ) -> None:
        """
        Supervise a single thermostat in a separate thread.

        This helper is intended to run in its own thread, using a
        human-readable thread name for logging. The effective number of
        measurements is typically controlled by the thermostat configuration
        (for example, ``max_measurements`` in ``tstat_config``) and may
        override the ``measurement_count`` argument.

        Args:
            tstat_config (dict): Configuration for the thermostat, including
                per-thermostat settings such as maximum measurements.
            thread_id (int): Unique identifier used to build a descriptive
                thread name for logging and debugging purposes.
            measurement_count (int, optional): Default or legacy value for the
                number of measurements to take. In current implementations,
                this value may be overridden by configuration values read from
                ``tstat_config`` (for example, ``max_measurements``).
                Defaults to 1.
        """
        thermostat_type = tstat_config.get("thermostat_type")
        zone_num = tstat_config.get("zone")
        thread_name = (
            f"Thread-{thread_id}-{thermostat_type}-Zone{zone_num}"
        )

        util.log_msg(
            f"{thread_name}: Starting supervision",
            mode=util.BOTH_LOG,
            func_name=1,
        )

        try:
            # Load the thermostat library
            mod = api.load_hardware_library(thermostat_type)

            # Verify environment variables
            api.verify_required_env_variables(thermostat_type, str(zone_num))

            # Create thermostat and zone objects
            Thermostat = mod.ThermostatClass(zone_num)
            Zone = mod.ThermostatZone(Thermostat)

            # Update runtime parameters from config
            if tstat_config.get("poll_time"):
                Zone.poll_time_sec = tstat_config["poll_time"]
            if tstat_config.get("connection_time"):
                Zone.connection_time_sec = tstat_config["connection_time"]
            if tstat_config.get("tolerance"):
                Zone.tolerance_degrees = tstat_config["tolerance"]
            if tstat_config.get("target_mode"):
                Zone.target_mode = tstat_config["target_mode"]

            # Set measurement limits
            max_measurements = tstat_config.get("measurements", 1)

            util.log_msg(
                f"{thread_name}: Zone={Zone.zone_name}, "
                f"max_measurements={max_measurements}",
                mode=util.BOTH_LOG,
                func_name=1,
            )

            # Supervision loop - using for loop for clarity
            for measurement in range(1, max_measurements + 1):
                # Query the thermostat
                Zone.query_thermostat_zone()

                # Store results
                with self._lock:
                    result_key = f"{thermostat_type}_zone{zone_num}"
                    if result_key not in self.measurement_results:
                        self.measurement_results[result_key] = []

                    self.measurement_results[result_key].append({
                        "timestamp": time.time(),
                        "measurement": measurement,
                        "temperature": Zone.display_temp,
                        "humidity": Zone.display_humidity,
                        "mode": Zone.current_mode,
                        "thread": thread_name,
                    })

                timestamp = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                util.log_msg(
                    f"[{timestamp}] {thread_name}: Measurement {measurement}/"
                    f"{max_measurements} - "
                    f"Temp: {Zone.display_temp}{tc.DEGREE_SIGN}F, "
                    f"Humidity: {Zone.display_humidity}%",
                    mode=util.BOTH_LOG,
                    func_name=1,
                )

                # Wait before next measurement (except after last measurement)
                if measurement < max_measurements:
                    time.sleep(Zone.poll_time_sec)

            util.log_msg(
                f"{thread_name}: Completed {max_measurements} measurements",
                mode=util.BOTH_LOG,
                func_name=1,
            )

            # Clean up external resources; Python will garbage-collect
            # these objects when they go out of scope
            if hasattr(Thermostat, "close"):
                Thermostat.close()

        except Exception as ex:
            # Track error for reporting
            result_key = f"{thermostat_type}_zone{zone_num}"
            with self._lock:
                self.thread_errors[result_key] = {
                    "error": str(ex),
                    "thread": thread_name,
                    "timestamp": time.time(),
                }

            util.log_msg(
                f"{thread_name}: ERROR - {str(ex)}",
                mode=util.BOTH_LOG,
                func_name=1,
            )
            import traceback
            util.log_msg(
                f"{thread_name}: Traceback:\n{traceback.format_exc()}",
                mode=util.DEBUG_LOG,
                func_name=1,
            )

    def supervise_all_zones(
        self,
        measurement_count: int = 1,
        use_threading: bool = True
    ) -> Dict:
        """
        Supervise all enabled zones within the site.

        The measurement_count parameter provides a default value, but
        per-thermostat 'measurements' configuration takes precedence if
        specified in the thermostat config dictionary.

        Args:
            measurement_count (int, optional): Default number of measurements
                per thermostat. This value is overridden by per-thermostat
                'measurements' config if present. Defaults to 1.
            use_threading (bool, optional): Use multi-threading for parallel
                supervision. Defaults to True.

        Returns:
            dict: Dictionary with two keys:
                - 'results': Dict of measurement results keyed by
                  thermostat/zone identifier. Each entry contains a list of
                  measurement dictionaries.
                - 'errors': Dict of errors keyed by thermostat/zone identifier
                  for any thermostats that failed during supervision.
        """
        util.log_msg(
            f"\nStarting site supervision: {self.site_name}",
            mode=util.BOTH_LOG,
            func_name=1,
        )

        if not self.thermostats:
            util.log_msg(
                "No enabled thermostats to supervise",
                mode=util.BOTH_LOG,
                func_name=1,
            )
            return {"results": {}, "errors": {}}

        # Clear previous results under lock for thread safety
        with self._lock:
            self.measurement_results = {}
            self.thread_errors = {}

        if use_threading:
            # Multi-threaded approach for parallel supervision
            threads = []
            thread_configs = []
            for idx, tstat_config in enumerate(self.thermostats, 1):
                # Use measurement count from config if available
                measurements = tstat_config.get(
                    "measurements", measurement_count
                )
                thread_configs.append((tstat_config, measurements))
                thread = threading.Thread(
                    target=self._supervise_single_thermostat,
                    args=(tstat_config, idx, measurements),
                    daemon=False,
                )
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete with timeout
            # Calculate timeout: max(connection_time + poll_time * measurements)
            max_timeout = 0
            for tstat_config, measurements in thread_configs:
                conn_time = tstat_config.get("connection_time", 300)
                poll_time = tstat_config.get("poll_time", 60)
                safety_margin = 60  # Extra time for processing
                timeout = conn_time + (poll_time * measurements) + safety_margin
                max_timeout = max(max_timeout, timeout)

            for thread in threads:
                thread.join(timeout=max_timeout)
                if thread.is_alive():
                    util.log_msg(
                        f"WARNING: Thread {thread.name} did not complete "
                        f"within timeout ({max_timeout}s)",
                        mode=util.BOTH_LOG,
                        func_name=1,
                    )

            util.log_msg(
                f"All {len(threads)} supervision threads completed",
                mode=util.BOTH_LOG,
                func_name=1,
            )
        else:
            # Sequential approach (for testing or debugging)
            for idx, tstat_config in enumerate(self.thermostats, 1):
                measurements = tstat_config.get(
                    "measurements", measurement_count
                )
                self._supervise_single_thermostat(
                    tstat_config, idx, measurements
                )

        # Log summary
        util.log_msg(
            f"\nSite supervision completed: {self.site_name}",
            mode=util.BOTH_LOG,
            func_name=1,
        )

        # Calculate total measurements efficiently (only done once at end)
        total_measurements = sum(
            len(v) for v in self.measurement_results.values()
        )
        util.log_msg(
            f"Total results collected: {total_measurements} "
            f"measurements across {len(self.measurement_results)} "
            f"thermostats",
            mode=util.BOTH_LOG,
            func_name=1,
        )

        # Report any errors
        if self.thread_errors:
            util.log_msg(
                f"Errors occurred in {len(self.thread_errors)} thermostat(s)",
                mode=util.BOTH_LOG,
                func_name=1,
            )

        return {
            "results": self.measurement_results,
            "errors": self.thread_errors
        }
