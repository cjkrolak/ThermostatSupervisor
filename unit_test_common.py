"""
Common functions used in multiple unit tests.
"""

# local imports
import utilities as util

unit_test_argv = ["supervise.py",  # module
                  "sht31",  # thermostat
                  "1",  # str(util.UNIT_TEST_ZONE),  # zone
                  "19",  # poll time in sec
                  "359",  # reconnect time in sec
                  "3",  # tolerance
                  "OFF_MODE",  # thermostat mode
                  "2",  # number of measurements
                  ]


def print_test_name():
    """Print out the unit test name to the console."""
    print("\n")
    print("=" * 40)
    print("testing '%s'" % util.get_function_name(2))
    print("=" * 40)


def is_azure_environment():
    """
    Return True if machine is Azure pipeline.

    Function assumes '192.' IP addresses are not Azure,
    everything else is Azure.
    """
    return '192.' not in util.get_local_ip()
