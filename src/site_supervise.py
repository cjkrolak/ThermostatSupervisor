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
    # Load configuration
    if args.config:
        site_config_dict = load_site_config_from_file(args.config)
    else:
        util.log_msg(
            "Using default site configuration",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        site_config_dict = site_config.get_default_site_config()

    # Override measurement count if specified
    if args.measurements is not None:
        util.log_msg(
            f"Overriding measurement count to {args.measurements}",
            mode=util.BOTH_LOG,
            func_name=1,
        )
        for tstat in site_config_dict.get("thermostats", []):
            tstat["measurements"] = args.measurements

    # Create site object
    site = ts.ThermostatSite(
        site_config_dict=site_config_dict,
        verbose=args.verbose
    )

    # Handle display-only modes
    if args.display_zones:
        site.display_all_zones()
        return

    if args.display_temps:
        site.display_all_temps()
        return

    # Display site configuration
    site.display_all_zones()

    # Run site supervision
    util.log_msg(
        f"\nStarting site supervision with "
        f"{'multi-threading' if args.use_threading else 'sequential mode'}",
        mode=util.BOTH_LOG,
        func_name=1,
    )

    result = site.supervise_all_zones(
        measurement_count=args.measurements if args.measurements else 1,
        use_threading=args.use_threading
    )

    # Display results summary
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

    # Display any errors
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

    util.log_msg(
        "\nSite supervision completed successfully",
        mode=util.BOTH_LOG,
        func_name=1,
    )


def exec_site_supervise(debug=True, argv_list=None):
    """
    Execute site supervisor loop.

    Args:
        debug (bool): Enable debugging mode.
        argv_list (list, optional): argv overrides.

    Returns:
        bool: True if complete.
    """
    util.log_msg.debug = debug  # debug mode set

    # Parse command-line arguments
    args = parse_arguments(argv_list)

    # Run site supervisor
    site_supervisor(args)

    return True


if __name__ == "__main__":
    # Verify environment
    env.get_python_version()

    # Execute site supervision
    exec_site_supervise(debug=True, argv_list=sys.argv[1:])
