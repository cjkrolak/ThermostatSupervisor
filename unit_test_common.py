"""
Common functions used in multiple unit tests.
"""
# global imports
import unittest

# local imports
import utilities as util

unit_test_argv = ["supervise.py",  # module
                  "sht31",  # thermostat
                  "99",  # str(util.UNIT_TEST_ZONE),  # zone
                  "19",  # poll time in sec
                  "359",  # reconnect time in sec
                  "3",  # tolerance
                  "OFF_MODE",  # thermostat mode
                  "2",  # number of measurements
                  ]


class UnitTestCommon(unittest.TestCase):
    """Extensions to unit test framework."""

    def print_test_result(self):
        if hasattr(self, '_outcome'):  # Python 3.4+
            # These two methods have no side effects
            result = self.defaultTestResult()
            self._feedErrorsToResult(result, self._outcome.errors)
        else:  # Python 3.2 - 3.3 or 3.0 - 3.1 and 2.7
            raise EnvironmentError(
                "this code is designed to work on Python 3.4+")
            # result = getattr(self, '_outcomeForDoCleanups',
            #                 self._resultForDoCleanups)
        error = self.list2reason(result.errors)
        failure = self.list2reason(result.failures)
        ok = not error and not failure

        # Demo:   report short info immediately (not important)
        if not ok:
            typ, text = ('ERROR', error) if error else ('FAIL', failure)
            msg = [x for x in text.split('\n')[1:] if not x.startswith(' ')][0]
            print("\n%s: %s\n     %s" % (typ, self.id(), msg))

    def list2reason(self, exc_list):
        if exc_list and exc_list[-1][0] is self:
            return exc_list[-1][1]

    def print_test_name(self):
        """Print out the unit test name to the console."""
        print("\n")
        print("-" * 60)
        print("testing '%s'" % self.id())  # util.get_function_name(2))
        print("-" * 60)


def is_azure_environment():
    """
    Return True if machine is Azure pipeline.

    Function assumes '192.' IP addresses are not Azure,
    everything else is Azure.
    """
    return '192.' not in util.get_local_ip()
