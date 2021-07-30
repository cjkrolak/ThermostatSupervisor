"""
Common functions used in multiple unit tests.
"""

# local imports
import utilities as util


def print_test_name():
    """Print out the unit test name to the console."""
    print("\n")
    print("=" * 40)
    print("testing '%s'" % util.get_function_name(2))
    print("=" * 40)
