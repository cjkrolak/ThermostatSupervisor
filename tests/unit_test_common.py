"""
Common functions used in multiple unit tests.
"""
# global imports
import pprint
import sys
import unittest

# local imports
from thermostatsupervisor import emulator_config
from thermostatsupervisor import supervise as sup
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util

# enable modes
ENABLE_FUNCTIONAL_INTEGRATION_TESTS = True  # enable func int tests
ENABLE_PERFORMANCE_INTEGRATION_TESTS = False and \
    not util.is_azure_environment()  # enable performance int tests
ENABLE_SUPERVISE_INTEGRATION_TESTS = True  # enable supervise int tests
ENABLE_FLASK_INTEGRATION_TESTS = True  # enable flask int tests
ENABLE_KUMOLOCAL_TESTS = False  # Kumolocal is local net only
ENABLE_MMM_TESTS = False  # mmm50 is local net only
ENABLE_SHT31_TESTS = True  # sht31 can fail on occasion


# generic argv list for unit testing
unit_test_sht31 = ["supervise.py",  # module
                   "sht31",  # thermostat
                   ["99", "1"][util.is_azure_environment()],  # zone
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

    thermostat_type = emulator_config.ALIAS  # was "UNITTEST"
    zone = emulator_config.supported_configs["zones"][0]
    user_inputs_backup = None
    Thermostat = None
    Zone = None
    is_off_mode_bckup = None

    def setup_mock_thermostat_zone(self):
        """Setup mock thermostat settings."""
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

    def teardown_mock_thermostat_zone(self):
        """Tear down the mock thermostat settings."""
        del api.thermostats[self.thermostat_type]
        api.user_inputs = self.user_inputs_backup
        self.Zone.is_off_mode = self.is_off_mode_bckup

    def print_test_result(self):
        """Print unit test result to console."""
        if hasattr(self, '_outcome'):  # Python 3.4+
            # These two methods have no side effects
            result = self.defaultTestResult()
            self._feedErrorsToResult(result, self._outcome.errors)
        else:  # Python 3.2 - 3.3 or 3.0 - 3.1 and 2.7
            raise OSError(
                "this code is designed to work on Python 3.4+")
            # result = getattr(self, '_outcomeForDoCleanups',
            #                 self._resultForDoCleanups)
        error = self.list2reason(result.errors)
        failure = self.list2reason(result.failures)
        result_ok = not error and not failure

        # Demo:   report short info immediately (not important)
        if not result_ok:
            typ, text = ('ERROR', error) if error else ('FAIL', failure)
            msg = [x for x in text.split('\n')[1:] if not x.startswith(' ')][0]
            print(f"\n{typ}: {self.id()}\n     {msg}")

    def list2reason(self, exc_list):
        """Parse reason from list."""
        if exc_list and exc_list[-1][0] is self:
            return exc_list[-1][1]
        else:
            return None

    def print_test_name(self):
        """Print out the unit test name to the console."""
        print("\n")
        print("-" * 60)
        print(f"testing '{self.id()}'")  # util.get_function_name(2))
        print("-" * 60)


class IntegrationTest(UnitTest):
    """Common integration test framework."""

    # thermostat_type = emulator_config.ALIAS  # was "UNITTEST"
    # zone = emulator_config.UNIT_TEST_ZONE  # was 1
    # user_inputs_backup = None
    # Thermostat = None
    Thermostat = None  # Thermostat object instance
    Zone = None  # Zone object instance
    mod = None  # module object
    mod_config = None  # config object
    unit_test_argv = []  # populated during setup
    timeout_limit = None
    timing_measurements = None
    timing_func = None
    temp_stdev_limit = None
    temp_repeatability_measurements = None
    humidity_stdev_limit = None
    humidity_repeatability_measurements = None
    poll_interval_sec = None

    def setup_common(self):
        """Test attributes common to all integration tests."""
        self.timeout_limit = 30  # 6 sigma timing upper limit in sec.
        self.timing_measurements = 10  # number of timing measurements.
        self.timing_func = None  # function used for timing measurement.
        self.temp_stdev_limit = 1  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 10  # number of temp msmts.
        self.humidity_stdev_limit = 1  # 1 sigma humid repeatability limit %RH
        self.humidity_repeatability_measurements = 10  # number of humid msmts.
        self.poll_interval_sec = 0  # delay between repeat measurements

    def setup_thermostat_zone(self):
        """Create a Thermostat and Zone instance for unit testing if needed."""
        # create new Thermostat and Zone instances
        if self.Thermostat is None and self.Zone is None:
            util.log_msg.debug = True  # debug mode set

            thermostat_type = self.unit_test_argv[
                api.get_argv_position("thermostat_type")]
            zone = int(self.unit_test_argv[api.get_argv_position("zone")])

            # create class instances
            self.Thermostat, self.Zone = tc.create_thermostat_instance(
                api, thermostat_type, zone, self.mod.ThermostatClass,
                self.mod.ThermostatZone)

        # return instances
        return self.Thermostat, self.Zone

    def tearDown(self):
        self.print_test_result()


@unittest.skipIf(not ENABLE_FUNCTIONAL_INTEGRATION_TESTS,
                 "functional integration tests are disabled")
class FunctionalIntegrationTest(IntegrationTest):
    """Functional integration tests."""
    metadata_field = None  # thermostat-specific
    metadata_type = str  # thermostat-specific

    def test_a_thermostat_basic_checkout(self):
        """
        Verify thermostat_basic_checkout on target thermostat.

        This test also creates the class instances so it should be run
        first in the integration test sequence.
        """
        IntegrationTest.Thermostat, IntegrationTest.Zone = \
            tc.thermostat_basic_checkout(
                api,
                self.unit_test_argv[api.get_argv_position("thermostat_type")],
                int(self.unit_test_argv[api.get_argv_position("zone")]),
                self.mod.ThermostatClass, self.mod.ThermostatZone
            )

    def test_report_heating_parameters(self):
        """
        Verify report_heating_parameters().
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        for test_case in self.mod_config.supported_configs["modes"]:
            print("-" * 80)
            print(f"test_case='{test_case}'")
            self.Zone.report_heating_parameters(test_case)
            print("-" * 80)

    def test_get_all_meta_data(self):
        """
        Verify get_all_metadata().
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        expected_return_type = dict
        metadata = self.Thermostat.get_all_metadata(
            zone=self.Thermostat.zone_number)
        self.assertTrue(isinstance(metadata, expected_return_type),
                        "metadata is type '%s', "
                        "expected type '%s'" %
                        (type(metadata), expected_return_type))

    def test_get_meta_data(self):
        """
        Verify get_metadata().
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        # test None case
        parameter = None
        expected_return_type = dict
        metadata = self.Thermostat.get_metadata(
            zone=self.Thermostat.zone_number,
            parameter=parameter)
        self.assertTrue(isinstance(metadata, expected_return_type),
                        "parameter='%s', metadata is type '%s', "
                        "expected type '%s'" %
                        (parameter, type(metadata), expected_return_type))

        # test parameter case
        parameter = self.metadata_field
        expected_return_type = self.metadata_type
        metadata = self.Thermostat.get_metadata(
            zone=self.Thermostat.zone_number,
            parameter=parameter)
        self.assertTrue(isinstance(metadata, expected_return_type),
                        "parameter='%s', value=%s, metadata is type '%s', "
                        "expected type '%s'" %
                        (parameter, metadata, type(metadata),
                         expected_return_type))


@unittest.skipIf(not ENABLE_SUPERVISE_INTEGRATION_TESTS,
                 "supervise integration test is disabled")
class SuperviseIntegrationTest(IntegrationTest):
    """Supervise integration tests common to all thermostat types."""

    def test_supervise(self):
        """
        Verify supervisor loop on target thermostat.
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        return_status = sup.exec_supervise(
            debug=True, argv_list=self.unit_test_argv)
        self.assertTrue(return_status,
                        f"return status={return_status}, expected True")


@unittest.skipIf(not ENABLE_PERFORMANCE_INTEGRATION_TESTS,
                 "performance integration tests are disabled")
class PerformanceIntegrationTest(IntegrationTest):
    """Performance integration tests common to all thermostat types."""

    def test_network_timing(self):
        """
        Verify network timing..
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        # measure thermostat response time
        measurements = self.timing_measurements
        print("%s Thermostat zone %s response times for %s measurements..." %
              (self.Zone.thermostat_type, self.Zone.zone_number, measurements))
        meas_data = \
            self.Zone.measure_thermostat_response_time(measurements)
        print("network timing stats (sec)")
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)

        # fail test if any measurement fails the limit.
        self.assertTrue(meas_data['max'] <= self.timeout_limit,
                        "max value observed (%s) is greater than "
                        "timout setting (%s)" % (meas_data['max'],
                                                 self.timeout_limit))

        # fail test if thermostat timing margin is poor vs. 6 sigma value
        self.assertTrue(meas_data['6sigma_upper'] <= self.timeout_limit,
                        "6 sigma timing margin (%s) is greater than "
                        "timout setting (%s)" % (meas_data['6sigma_upper'],
                                                 self.timeout_limit))

    def test_temperature_repeatability(self):
        """
        Verify temperature repeatability.
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        # measure thermostat temp repeatability
        measurements = self.temp_repeatability_measurements
        print("%s Thermostat zone %s temperature repeatability for %s "
              "measurements with %s sec delay between each measurement..." %
              (self.Zone.thermostat_type, self.Zone.zone_number, measurements,
               self.poll_interval_sec))
        meas_data = self.Zone.measure_thermostat_repeatability(
            measurements, self.poll_interval_sec)
        print("temperature repeatability stats (deg F)")
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)

        # fail test if thermostat temp repeatability is poor
        act_val = meas_data['stdev']
        self.assertTrue(
            act_val <= self.temp_stdev_limit,
            "temperature stdev (%s) is greater than "
            "temp repeatability limit (%s)" % (act_val,
                                               self.temp_stdev_limit))

    def test_humidity_repeatability(self):
        """
        Verify humidity repeatability.
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        # check for humidity support
        if not self.Zone.get_is_humidity_supported():
            print("humidity not supported on this thermostat, exiting")
            return

        # measure thermostat humidity repeatability
        measurements = self.temp_repeatability_measurements
        print("%s Thermostat zone %s humidity repeatability for %s "
              "measurements with %s sec delay betweeen each measurement..." %
              (self.Zone.thermostat_type, self.Zone.zone_number, measurements,
               self.poll_interval_sec))
        meas_data = self.Zone.measure_thermostat_repeatability(
            measurements, self.poll_interval_sec,
            self.Zone.get_display_humidity)
        print("humidity repeatability stats (%RH)")
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)

        # fail test if thermostat humidity repeatability is poor
        act_val = meas_data['stdev']
        self.assertTrue(
            act_val <= self.humidity_stdev_limit,
            "humidity stdev (%s) is greater than "
            "humidity repeatability limit (%s)" %
            (act_val, self.humidity_stdev_limit))


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
    print(f"skipped tests({len(result.skipped)}):")
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
    global_par = "ENABLE_FUNCTIONAL_INTEGRATION_TESTS"
    enable_flag = getattr(sys.modules[__name__], global_par)

    # parse runtime parameters
    if len(sys.argv) > 1:
        enable_int_test_flags = ["1", "t", "true"]
        enable_flag = bool(sys.argv[1].lower() in enable_int_test_flags)

    # update global parameter
    setattr(sys.modules[__name__], global_par, enable_flag)
    print(f"integration tests are {['disabled', 'enabled'][enable_flag]}")
    return enable_flag


if __name__ == "__main__":
    parse_unit_test_runtime_parameters()
    print("DEBUG: ENABLE_FUNCTIONAL_INTEGRATION_TESTS=%s" %
          ENABLE_FUNCTIONAL_INTEGRATION_TESTS)
    print("DEBUG: ENABLE_PERFORMANCE_INTEGRATION_TESTS=%s" %
          ENABLE_PERFORMANCE_INTEGRATION_TESTS)
    run_all_tests()
