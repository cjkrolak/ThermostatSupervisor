"""
Common functions used in multiple unit tests.
"""
# global imports
import unittest

# thermostat configs
import sht31_config

# local imports
import thermostat_api as api
import thermostat_common as tc
import utilities as util

# generic argv list for unit testing
unit_test_argv = api.user_inputs
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

    thermostat_type = sht31_config.ALIAS  # was "UNITTEST"
    zone = sht31_config.UNIT_TEST_ZONE  # was 1
    user_inputs_backup = None
    Thermostat = None
    Zone = None

    def setUp_mock_thermostat_zone(self):
        api.thermostats[self.thermostat_type] = {  # dummy unit test thermostat
            "required_env_variables": {
                "GMAIL_USERNAME": None,
                "GMAIL_PASSWORD": None,
                },
            }
        self.user_inputs_backup = api.user_inputs
        api.user_inputs = {
            "thermostat_type": self.thermostat_type,
            "zone": self.zone,
            "poll_time_sec": 55,
            "connection_time_sec": 155,
            "target_mode": "OFF_MODE",
            "measurements": 3,
            }

        self.Thermostat = tc.ThermostatCommon()
        self.Zone = tc.ThermostatCommonZone()
        self.Zone.update_runtime_parameters(api.user_inputs)
        self.Zone.current_mode = self.Zone.HEAT_MODE

    def tearDown_mock_thermostat_zone(self):
        del api.thermostats[self.thermostat_type]
        api.user_inputs = self.user_inputs_backup

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
