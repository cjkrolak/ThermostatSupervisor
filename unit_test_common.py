"""
Common functions used in multiple unit tests.
"""
# global imports
import pprint
import sys
import unittest

# thermostat configs
import sht31_config

# local imports
import supervise as sup
import thermostat_api as api
import thermostat_common as tc
import utilities as util

# enable modes
enable_integration_tests = True  # use to bypass integration tests
enable_kumolocal_tests = False  # Kumolocal is local net only
enable_mmm_tests = False  # mmm50 is local net only
enable_sht31_tests = False  # sht31 can fail on occasion


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

    def setUpCommon(self):
        self.timeout_limit = 30  # 6 sigma timing upper limit in sec.
        self.timing_measurements = 10  # number of timing measurements.
        self.timing_func = None  # function used for timing measurement.
        self.temp_stdev_limit = 1  # 1 sigma temp repeatability limit in F
        self.temp_repeatability_measurements = 10  # number of temp msmts.
        self.humidity_stdev_limit = 1  # 1 sigma humid repeatability limit %RH
        self.humidity_repeatability_measurements = 10  # number of humid msmts.
        self.poll_interval_sec = 0  # delay between repeat measurements

    def setUpThermostatZone(self):
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

    def test_A_ThermostatBasicCheckout(self):
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

    def test_B_NetworkTiming(self):
        """
        Verify network timing..
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setUpThermostatZone()

        # measure thermostat response time
        measurements = self.timing_measurements
        print("%s Thermostat zone %s response times for %s measurements..." %
              (self.Zone.thermostat_type, self.Zone.zone_number, measurements))
        meas_data = \
            self.Zone.measure_thermostat_response_time(measurements)
        print("network timing stats (sec)")
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)

        # fail test if thermostat timing margin is poor
        self.assertTrue(meas_data['6sigma_upper'] < self.timeout_limit,
                        "6 sigma timing margin (%s) is greater than "
                        "timout setting (%s)" % (meas_data['6sigma_upper'],
                                                 self.timeout_limit))

    def test_C_TemperatureRepeatability(self):
        """
        Verify temperature repeatability.
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setUpThermostatZone()

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
            act_val < self.temp_stdev_limit,
            "temperature stdev (%s) is greater than "
            "temp repeatability limit (%s)" % (act_val,
                                               self.temp_stdev_limit))

    def test_D_HumidityRepeatability(self):
        """
        Verify humidity repeatability.
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setUpThermostatZone()

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
            act_val < self.humidity_stdev_limit,
            "humidity stdev (%s) is greater than "
            "humidity repeatability limit (%s)" %
            (act_val, self.humidity_stdev_limit))

    def test_ReportHeatingParameters(self):
        """
        Verify report_heating_parameters().
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setUpThermostatZone()

        for test_case in self.mod_config.supported_configs["modes"]:
            print("-" * 80)
            print("test_case='%s'" % test_case)
            self.Zone.report_heating_parameters(test_case)
            print("-" * 80)

    def test_Z_Supervise(self):
        """
        Verify supervisor loop on target thermostat.
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setUpThermostatZone()

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
