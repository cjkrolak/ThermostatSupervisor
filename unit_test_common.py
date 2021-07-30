"""
Common functions used in multiple unit tests.
"""

# local imports
import utilities as util


def print_test_name():
    """Print out the unit test name to the console."""
    print("testing '%s'" % util.get_function_name())
