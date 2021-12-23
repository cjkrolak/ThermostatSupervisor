"""
Common functions used in multiple unit tests.
"""
# global imports
import sys
import unittest

# local imports
from ... import azure_context  # noqa F401, pylint: disable=unused-import.
import sht31_config
import supervise as sup
import thermostat_api as api
import thermostat_common as tc
import utilities as util

# enable modes
enable_integration_tests = True  # use to bypass integration tests
enable_kumolocal_tests = False  # Kumolocal is local net only
enable_mmm_tests = False  # mmm50 is local net only
enable_sht31_tests = False  # sht31 can fail on occasion


def is_azure_environment():
    """
    Return True if machine is Azure pipeline.

    Function assumes '192.' IP addresses are not Azure,
    everything else is Azure.
    """
    return '192.' not in util.get_local_ip()


# generic argv list for unit testing
unit_test_sht31 = ["supervise.py",  # module
                   "sht31",  # thermostat
                   ["99", "1"][is_azure_environment()],  # zone
                   "19",  # poll time in sec
                   "359",  # reconnect time in sec
                   "3",  # tolerance
                   "OFF_MODE",  # thermostat mode
                   "2",  # number of measurements
                   ]

unit_test_honeywell = [
    "supervise.py",  # module
    "honeywell",  # thermostat
    "0",  # str(util.UNIT_TEST_ZONE),  # zone
    "19",  # poll time in sec
    "359",  # reconnect time in sec
    "3",  # tolerance
    "OFF_MODE",  # thermostat mode
    "2",  # number of measurements
    ]

unit_test_argv = unit_test_sht31


class UnitTest(unittest.TestCase):
    """Extensions to unit test framework."""

    thermostat_type = sht31_config.ALIAS  # was "UNITTEST"
    zone = sht31_config.UNIT_TEST_ZONE  # was 1
    user_inputs_backup = None
    Thermostat = None
    Zone = None
    is_off_mode_bckup = None

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
        self.Zone.current_mode = self.Zone.OFF_MODE
        self.is_off_mode_bckup = self.Zone.is_off_mode
        self.Zone.is_off_mode = lambda *_, **__: 1

    def tearDown_mock_thermostat_zone(self):
        del api.thermostats[self.thermostat_type]
        api.user_inputs = self.user_inputs_backup
        self.Zone.is_off_mode = self.is_off_mode_bckup

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


class IntegrationTest(UnitTest):
    """Common integration test framework."""

    # thermostat_type = sht31_config.ALIAS  # was "UNITTEST"
    # zone = sht31_config.UNIT_TEST_ZONE  # was 1
    # user_inputs_backup = None
    # Thermostat = None
    Zone = None  # Zone object
    mod = None  # module object
    mod_config = None  # config object
    unit_test_argv = []  # populated during setup

    def tearDown(self):
        self.print_test_result()

    def test_A_ThermostatBasicCheckout(self):
        """
        Verify thermostat_basic_checkout on target thermostat.
        """
        _, IntegrationTest.Zone = tc.thermostat_basic_checkout(
            api,
            self.unit_test_argv[api.get_argv_position("thermostat_type")],
            self.unit_test_argv[api.get_argv_position("zone")],
            self.mod.ThermostatClass, self.mod.ThermostatZone
            )

    def test_ReportHeatingParameters(self):
        """
        Verify report_heating_parameters().
        """
        for test_case in self.mod_config.supported_configs["modes"]:
            print("-" * 80)
            print("test_case='%s'" % test_case)
            self.Zone.report_heating_parameters(test_case)
            print("-" * 80)

    def test_Z_Supervise(self):
        """
        Verify supervisor loop on target thermostat.
        """
        return_status = sup.exec_supervise(
            debug=True, argv_list=self.unit_test_argv)
        self.assertTrue(return_status, "return status=%s, expected True" %
                        return_status)


def run_all_tests():
    """
    Run all enabled unit tests.
    """
    # discover all unit test files in current directory
    print("discovering tests...")
    suite = unittest.TestLoader().discover('.', pattern="test_*.py")

    # run all unit tests
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    # flush stdout so that the following output will be at the end
    sys.stdout.flush()
    print("-" * 80)
    print("skipped tests(%s):" % len(result.skipped))
    for name, reason in result.skipped:
        print(name, reason)
    print("-" * 80)


def parse_unit_test_runtime_parameters():
    """
    Parse runtime parameters passed in to unit test modules.

    unit test runtime args:
    0 = script_name
    1 = enable integration tests (default = enabled)
    """
    # parameter 1: enable integration tests
    global_par = "enable_integration_tests"
    enable_flag = getattr(sys.modules[__name__], global_par)

    # parse runtime parameters
    if len(sys.argv) > 1:
        enable_int_test_flags = ["1", "t", "true"]
        if sys.argv[1].lower() in enable_int_test_flags:
            enable_flag = True
        else:
            enable_flag = False

    # update global parameter
    setattr(sys.modules[__name__], global_par, enable_flag)
    print("integration tests are %s" % ["disabled", "enabled"][enable_flag])
    return enable_flag


if __name__ == "__main__":
    parse_unit_test_runtime_parameters()
    print("DEBUG: enable_integration_tests=%s" % enable_integration_tests)
    run_all_tests()
