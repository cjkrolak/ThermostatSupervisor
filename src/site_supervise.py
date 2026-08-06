"""
Site Supervisor - Monitor multiple thermostats at a single site.

This module provides command-line interface for site-level thermostat
supervision with concurrent monitoring of multiple thermostats.
"""

# built-ins
import argparse
import sys

# local imports
from src import environment as env
from src import site_config
from src import thermostat_site as ts
from src import utilities as util


def parse_arguments(argv_list=None):
    """
    Parse command-line arguments for site supervision.

    Args:
        argv_list (list, optional): Override sys.argv. Defaults to None.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Site Supervisor - Monitor multiple thermostats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default site configuration
  python -m src.site_supervise

  # Use custom site configuration file
  python -m src.site_supervise -c mysite.json

  # Enable threading (default)
  python -m src.site_supervise --threading

  # Disable threading for debugging
  python -m src.site_supervise --no-threading

  # Set custom measurement count for all thermostats
  python -m src.site_supervise -n 5
        """,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help="Path to site configuration file (JSON format). If not "
        "specified, uses default configuration.",
    )

    parser.add_argument(
        "-n",
        "--measurements",
        type=int,
        default=None,
        help="Number of measurements per thermostat (overrides config "
        "values).",
    )

    parser.add_argument(
        "--threading",
        dest="use_threading",
        action="store_true",
        default=True,
        help="Enable multi-threading for parallel supervision (default).",
    )

    parser.add_argument(
        "--no-threading",
        dest="use_threading",
        action="store_false",
        help="Disable multi-threading (run thermostats sequentially).",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=True,
        help="Enable verbose logging (default).",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        dest="verbose",
        action="store_false",
        help="Disable verbose logging.",
    )

    parser.add_argument(
        "--display-zones",
        action="store_true",
        help="Display all zones and exit (no supervision).",
    )

    parser.add_argument(
        "--display-temps",
        action="store_true",
        help="Display current temperatures and exit (no supervision).",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (default: False).",
    )

    if argv_list is None:
        argv_list = sys.argv[1:]

    return parser.parse_args(argv_list)


def load_site_config_from_file(config_path):
    """
    Load site configuration from JSON file.

    Args:
        config_path (str): Path to configuration file.

    Returns:
        dict: Site configuration dictionary.
    """
    import json

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        util.log_msg(
            f"Loaded site configuration from {config_path}",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        return config
    except FileNotFoundError:
        util.log_msg(
            f"ERROR: Configuration file not found: {config_path}",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        sys.exit(1)
    except json.JSONDecodeError as ex:
        util.log_msg(
            f"ERROR: Invalid JSON in configuration file: {str(ex)}",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        sys.exit(1)


def site_supervisor(args):
    """
    Execute site supervision.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    site_config_dict = _get_site_config(args)
    _apply_measurement_override(site_config_dict, args)

    # Create site object
    site = ts.ThermostatSite(site_config_dict=site_config_dict, verbose=args.verbose)

    # Handle display-only modes
    if _handle_display_only_mode(site, args):
        return

    # Display site configuration
    site.display_all_zones()

    # Run site supervision
    _log_supervision_start(args)
    result = _run_site_supervision(site, args)
    _display_supervision_results(result)

    util.log_msg(
        "\nSite supervision completed successfully",
        mode=util.BOTH_LOG,
        func_name=1,
    )


def _get_site_config(args):
    """Return site configuration from file or defaults."""
    if args.config:
        return load_site_config_from_file(args.config)
    util.log_msg(
        "Using default site configuration",
        mode=util.BOTH_LOG,
        func_name=1,
    )
    return site_config.get_default_site_config()


def _apply_measurement_override(site_config_dict, args) -> None:
    """Apply a global measurement override to all thermostats."""
    if args.measurements is None:
        return
    util.log_msg(
        f"Overriding measurement count to {args.measurements}",
        mode=util.BOTH_LOG,
        func_name=1,
    )
    for tstat in site_config_dict.get("thermostats", []):
        tstat["measurements"] = args.measurements


def _handle_display_only_mode(site, args) -> bool:
    """Handle display-only commands and return whether execution is complete."""
    if args.display_zones:
        site.display_all_zones()
        return True
    if args.display_temps:
        site.display_all_temps()
        return True
    return False


def _log_supervision_start(args) -> None:
    """Log supervision mode before site execution."""
    mode_name = "multi-threading" if args.use_threading else "sequential mode"
    util.log_msg(
        f"\nStarting site supervision with {mode_name}",
        mode=util.BOTH_LOG,
        func_name=1,
    )


def _run_site_supervision(site, args):
    """Run site supervision and handle keyboard interruption gracefully."""
    try:
        return site.supervise_all_zones(
            measurement_count=args.measurements if args.measurements else 1,
            use_threading=args.use_threading,
        )
    except KeyboardInterrupt:
        util.log_msg(
            "\n\nSite supervision interrupted by user (CTRL-C)",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        util.log_msg(
            "Exiting gracefully...",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        sys.exit(0)


def _display_supervision_results(result) -> None:
    """Display supervision summaries for successful and failed thermostats."""
    results = result.get("results", {})
    errors = result.get("errors", {})

    if results:
        util.log_msg(
            f"\n{'='*60}\nSite Supervision Results\n{'='*60}",
            mode=util.BOTH_LOG,
        )
        for tstat_key, measurements in results.items():
            util.log_msg(
                f"\n{tstat_key}: {len(measurements)} measurements",
                mode=util.BOTH_LOG,
            )

    if errors:
        util.log_msg(
            f"\n{'='*60}\nErrors\n{'='*60}",
            mode=util.BOTH_LOG,
        )
        for tstat_key, error_info in errors.items():
            util.log_msg(
                f"\n{tstat_key}: {error_info.get('error', 'Unknown error')}",
                mode=util.BOTH_LOG,
            )


def exec_site_supervise(debug=None, argv_list=None):
    """
    Execute site supervisor loop.

    Args:
        debug (bool, optional): Enable debugging mode. If None, uses the
            --debug flag from parsed arguments. Explicit True/False values
            override the parsed flag.
        argv_list (list, optional): argv overrides.

    Returns:
        bool: True if complete.
    """
    # Parse command-line arguments
    args = parse_arguments(argv_list)

    # Set debug mode: explicit parameter overrides parsed flag
    if debug is not None:
        util.log_msg.debug = debug
    else:
        util.log_msg.debug = args.debug

    # Run site supervisor
    site_supervisor(args)

    return True


if __name__ == "__main__":
    # Verify environment
    env.get_python_version()

    # Execute site supervision (debug flag parsed inside exec_site_supervise)
    exec_site_supervise(argv_list=sys.argv[1:])
