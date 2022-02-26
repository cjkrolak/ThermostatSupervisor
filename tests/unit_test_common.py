"""
Common functions used in multiple unit tests.
"""
# global imports
import distutils.util
import os
import pprint
import sys
import unittest
from unittest.mock import patch

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
ENABLE_SHT31_TESTS = False  # sht31 can fail on occasion


# generic argv list for unit testing
unit_test_emulator = [
    "supervise.py",  # module
    "emulator",  # thermostat
    emulator_config.supported_configs["zones"][0],  # zone
    "19",  # poll time in sec
    "359",  # reconnect time in sec
    "3",  # tolerance
    "OFF_MODE",  # thermostat mode
    "2",  # number of measurements
    ]

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

unit_test_argv = unit_test_emulator


class PatchMeta(type):
    """A metaclass to patch all inherited classes."""

    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("DEBUG: in PatchMeta for %s, patch args=%s" %
              (cls, str(cls.patch_args)))
        patch.object(*cls.patch_args)(cls)


# mock argv to prevent unit test runtime arguments from polluting tests
# that use argv parameters.  Azure pipelines is susceptible to this issue.
def mock_patch(_cls):
    print("DEBUG: in mock patch decorator for %s" % _cls)

    def wrapper():
        print("DEBUG: sys.argv before patch=%s" % sys.argv)
        with patch.object(sys, 'argv', [os.path.realpath(__file__)]):
            print("DEBUG: sys.argv after patch=%s" % sys.argv)
            return _cls()
    return wrapper


# mock argv to prevent azure runtime args from polluting test.
#@patch.object(sys, 'argv', [os.path.realpath(__file__)])  # noqa e501, pylint:disable=undefined-variable
class UnitTest(unittest.TestCase, metaclass=PatchMeta):
    """Extensions to unit test framework."""

    # mock argv to prevent unit test runtime arguments from polluting tests
    # that use argv parameters.  Azure pipelines is susceptible to this issue.
    __metaclass__ = PatchMeta
    patch_args = (sys, 'argv', [os.path.realpath(__file__)])

    thermostat_type = unit_test_argv[1]
    zone = unit_test_argv[2]
    user_inputs_backup = None
    Thermostat = None
    Zone = None
    is_off_mode_bckup = None

    # def __init_subclass__(cls, **kwargs):
    #    return mock_patch(_cls=cls)

    def setUp(self):
        """Default setup method."""
        self.print_test_name()
        self.unit_test_argv = unit_test_argv

    def tearDown(self):
        """Default teardown method."""
        self.print_test_result()

    def setup_thermostat_zone(self):
        """
        Create a Thermostat and Zone instance for unit testing if needed.

        This function is called at the beginning of integration tests.
        """
        # parse runtime arguments
        api.uip = api.UserInputs(self.unit_test_argv)

        # create new Thermostat and Zone instances
        if self.Thermostat is None and self.Zone is None:
            util.log_msg.debug = True  # debug mode set
            thermostat_type = api.uip.get_user_inputs(api.THERMOSTAT_TYPE_FLD)
            zone = api.uip.get_user_inputs(api.ZONE_FLD)

            # create class instances
            self.Thermostat, self.Zone = tc.create_thermostat_instance(
                api, thermostat_type, zone, self.mod.ThermostatClass,
                self.mod.ThermostatZone)

        # return instances
        return self.Thermostat, self.Zone

    def setup_mock_thermostat_zone(self):
        """Setup mock thermostat settings."""
        api.thermostats[self.thermostat_type] = {  # dummy unit test thermostat
            "required_env_variables": {
                "GMAIL_USERNAME": None,
                "GMAIL_PASSWORD": None,
            },
        }
        self.unit_test_argv = unit_test_argv  # use defaults
        self.user_inputs_backup = getattr(api.uip, "user_inputs", None)
        # parse runtime arguments
        api.uip = api.UserInputs(self.unit_test_argv)
        # api.uip.set_user_inputs(api.THERMOSTAT_TYPE_FLD,
        # self.thermostat_type)
        # api.uip.set_user_inputs(api.ZONE_FLD, self.zone)
        # api.uip.set_user_inputs(api.POLL_TIME_FLD, 55)
        # api.uip.set_user_inputs(api.CONNECT_TIME_FLD, 155)
        # api.uip.set_user_inputs(api.TARGET_MODE_FLD, "OFF_MODE")
        # api.uip.set_user_inputs(api.MEASUREMENTS_FLD, 3)

        self.Thermostat = tc.ThermostatCommon()
        self.Zone = tc.ThermostatCommonZone()
        self.Zone.update_runtime_parameters(api.uip.user_inputs)
        self.Zone.current_mode = self.Zone.OFF_MODE
        self.is_off_mode_bckup = self.Zone.is_off_mode
        self.Zone.is_off_mode = lambda *_, **__: 1

    def teardown_mock_thermostat_zone(self):
        """Tear down the mock thermostat settings."""
        del api.thermostats[self.thermostat_type]
        api.uip.user_inputs = self.user_inputs_backup
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


#@patch.object(sys, 'argv', [os.path.realpath(__file__)])  # noqa e501, pylint:disable=undefined-variable
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
        """
        Create a Thermostat and Zone instance for integration testing.

        This function is called at the beginning of integration tests.
        If an existing thermostat/zone exists from previous test this function
        will use the existing instances.
        """
        # parse runtime arguments
        print("DEBUG(%s): setting up user inputs" % util.get_function_name())
        api.uip = api.UserInputs(self.unit_test_argv)

        # create new Thermostat and Zone instances
        if self.Thermostat is None and self.Zone is None:
            util.log_msg.debug = True  # debug mode set
            thermostat_type = api.uip.get_user_inputs(api.THERMOSTAT_TYPE_FLD)
            zone = api.uip.get_user_inputs(api.ZONE_FLD)

            # create class instances
            self.Thermostat, self.Zone = tc.create_thermostat_instance(
                api, thermostat_type, zone, self.mod.ThermostatClass,
                self.mod.ThermostatZone)

        # update runtime parameters
        self.Zone.update_runtime_parameters(api.uip.user_inputs)

        # return instances
        return self.Thermostat, self.Zone


@unittest.skipIf(not ENABLE_FUNCTIONAL_INTEGRATION_TESTS,
                 "functional integration tests are disabled")
#@patch.object(sys, 'argv', [os.path.realpath(__file__)])  # noqa e501, pylint:disable=undefined-variable
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
        api.uip = api.UserInputs(self.unit_test_argv)

        IntegrationTest.Thermostat, IntegrationTest.Zone = \
            tc.thermostat_basic_checkout(
                api,
                api.uip.get_user_inputs(api.THERMOSTAT_TYPE_FLD),
                api.uip.get_user_inputs(api.ZONE_FLD),
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
        self.assertTrue(
            isinstance(
                metadata,
                expected_return_type),
            f"metadata is type '{type(metadata)}', "
            f"expected type '{expected_return_type}'")

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
        self.assertTrue(
            isinstance(
                metadata,
                expected_return_type),
            f"parameter='{parameter}', metadata is type '{type(metadata)}', "
            f"expected type '{expected_return_type}'")

        # test parameter case
        parameter = self.metadata_field
        expected_return_type = self.metadata_type
        metadata = self.Thermostat.get_metadata(
            zone=self.Thermostat.zone_number,
            parameter=parameter)
        self.assertTrue(
            isinstance(
                metadata,
                expected_return_type),
            f"parameter='{parameter}', value={metadata}, metadata is type "
            f"'{type(metadata)}', expected type '{expected_return_type}'")


@unittest.skipIf(not ENABLE_SUPERVISE_INTEGRATION_TESTS,
                 "supervise integration test is disabled")
# @patch.object(sys, 'argv', [os.path.realpath(__file__)])  # noqa e501, pylint:disable=undefined-variable
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
#@patch.object(sys, 'argv', [os.path.realpath(__file__)])  # noqa e501, pylint:disable=undefined-variable
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
        print(f"{self.Zone.thermostat_type} Thermostat zone "
              f"{self.Zone.zone_number} response times for {measurements} "
              f"measurements...")
        meas_data = \
            self.Zone.measure_thermostat_response_time(measurements)
        print("network timing stats (sec)")
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)

        # fail test if any measurement fails the limit.
        self.assertTrue(
            meas_data['max'] <= self.timeout_limit,
            f"max value observed ({meas_data['max']}) is greater than timout"
            f" setting ({self.timeout_limit})")

        # fail test if thermostat timing margin is poor vs. 6 sigma value
        self.assertTrue(
            meas_data['6sigma_upper'] <= self.timeout_limit,
            f"6 sigma timing margin ({meas_data['6sigma_upper']}) is greater "
            f"than timout setting ({self.timeout_limit})")

    def test_temperature_repeatability(self):
        """
        Verify temperature repeatability.
        """
        # setup class instances
        self.Thermostat, self.Zone = self.setup_thermostat_zone()

        # measure thermostat temp repeatability
        measurements = self.temp_repeatability_measurements
        print(f"{self.Zone.thermostat_type} Thermostat zone "
              f"{self.Zone.zone_number} temperature repeatability for "
              f"{measurements} measurements with {self.poll_interval_sec} "
              f"sec delay between each measurement...")
        meas_data = self.Zone.measure_thermostat_repeatability(
            measurements, self.poll_interval_sec)
        print("temperature repeatability stats (deg F)")
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)

        # fail test if thermostat temp repeatability is poor
        act_val = meas_data['stdev']
        self.assertTrue(
            act_val <= self.temp_stdev_limit,
            f"temperature stdev ({act_val}) is greater than temp repeatability"
            f" limit ({self.temp_stdev_limit})")

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
        print(f"{self.Zone.thermostat_type} Thermostat zone "
              f"{self.Zone.zone_number} humidity repeatability for "
              f"{measurements} measurements with {self.poll_interval_sec} "
              f"sec delay betweeen each measurement...")
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
            f"humidity stdev ({act_val}) is greater than humidity "
            f"repeatability limit ({self.humidity_stdev_limit})")


#@patch.object(sys, 'argv', [os.path.realpath(__file__)])  # noqa e501, pylint:disable=undefined-variable
class RuntimeParameterTest(UnitTest):
    """Runtime parameter tests."""

    # mock argv to prevent unit test runtime arguments from polluting tests
    # that use argv parameters.  Azure pipelines is susceptible to this issue.
    # __metaclass__ = PatchMeta
    # patch_args = (sys.argv, [os.path.realpath(__file__)])

    uip = None
    mod = None

    def get_test_list(self):
        """Return the test list with string elemeents."""
        test_list = []
        for k, _ in self.test_fields:
            test_list.append(k)
        return test_list

    def get_expected_vals_dict(self):
        """Return the expected values dictionary."""
        expected_values = {}
        # element 0 (script) is omitted from expected_values dict.
        for x in range(1, len(self.test_fields)):
            expected_values[self.test_fields[x][1]] = self.test_fields[x][0]
        return expected_values

    def get_named_list(self, flag):
        """
        Return the named parameter list.

        inputs:
            flag(str): flag.
        returns:
            (list): named parameter list
        """
        test_list_named_flag = []
        # script placeholder for 0 element
        test_list_named_flag.append(self.test_fields[0][1])

        # element 0 (script) is omitted from expected_values dict.
        for x in range(1, len(self.test_fields)):
            test_list_named_flag.append(self.uip.get_user_inputs(
                self.test_fields[x][1], flag) + " " +
                str(self.test_fields[x][0]))
        return test_list_named_flag

    def parse_user_inputs_dict(self):
        """
        Parse the user_inputs_dict into list matching
        order of test_list.
        """
        actual_values = []
        for x in range(0, len(self.test_fields)):
            actual_values.append(self.uip.get_user_inputs(
                self.test_fields[x][1]))
        return actual_values

    def setUp(self):
        self.print_test_name()
        util.log_msg.file_name = "unit_test.txt"
        self.initialize_user_inputs()

    def tearDown(self):
        self.print_test_result()

    def verify_parsed_values(self):
        """
        Verify values were parsed correctly by comparing to expected values.
        """
        expected_values = self.get_expected_vals_dict()
        for k in expected_values:
            self.assertEqual(expected_values[k],
                             self.uip.get_user_inputs(k),
                             f"expected({type(expected_values[k])}) "
                             f"{expected_values[k]} != "
                             f"actual({type(self.uip.get_user_inputs(k))}) "
                             f"{self.uip.get_user_inputs(k)}")

    def initialize_user_inputs(self):
        """
        Re-initialize user_inputs dict.
        """
        self.uip = self.mod.UserInputs()
        for k in self.uip.user_inputs:
            self.uip.set_user_inputs(k, None)

    def test_parse_argv_list(self):
        """
        Verify test parse_argv_list() returns expected
        values when input known values.
        """
        test_list = self.get_test_list()
        print(f"test_list={test_list}")
        self.uip = self.mod.UserInputs(test_list, "unit test parser")
        print(f"user_inputs={self.uip.user_inputs}")
        self.verify_parsed_values()

    def test_parser(self):
        """
        Generic test for argparser.
        """
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('-a', type=int)
        # argv = '-a 1'.split()  # or ['-a','1','foo']
        # argv = ["-a 1", "--b 2"]  # double dash doesn't work yet.
        argv = ["-a 1"]
        args = parser.parse_args(argv)
        assert(args.a == 1)
        # assert(args.b == 2)

    def test_parse_named_arguments_sflag(self):
        """
        Verify test parse_named_arguments() returns expected
        values when input known values with sflag.
        """
        # build the named sflag list
        self.uip = self.mod.UserInputs()
        named_sflag_list = self.get_named_list("sflag")
        print("sflag_list=%s" % named_sflag_list)

        # clear out user inputs
        self.initialize_user_inputs()

        # parse named sflag list
        self.uip = self.mod.UserInputs(
            named_sflag_list, "unittest parsing named sflag arguments")
        self.verify_parsed_values()

    def test_parse_named_arguments_lflag(self):
        """
        Verify test parse_named_arguments() returns expected
        values when input known values with sflag.
        """
        return  # not yet working

        # build the named sflag list
        self.uip = self.mod.UserInputs()
        named_lflag_list = self.get_named_list("lflag")
        print("lflag_list=%s" % named_lflag_list)

        # clear out user inputs
        self.initialize_user_inputs()

        # parse named sflag list
        self.uip = self.mod.UserInputs(
            named_lflag_list, "unittest parsing named sflag arguments")
        self.verify_parsed_values()

    def parse_named_arguments(self, test_list, label_str):
        """
        Verify test parse_named_arguments() returns expected
        values when input known values.

        inputs:
            test_list(list): list of named arguments
            label_str(str): description pass-thru
        """
        print(f"testing named arg list='{test_list}")
        self.uip = self.mod.UserInputs(test_list, label_str)
        print(f"user_inputs={self.uip.user_inputs}")
        self.verify_parsed_values()

    def test_parse_runtime_parameters(self):
        """
        Test the upper level function for parsing.
        """
        self.uip = self.mod.UserInputs()
        # print("test 1, input None, will raise error")
        # self.initialize_user_inputs()
        # with self.assertRaises(ValueError):
        #     self.uip.parse_runtime_parameters(argv_list=None)

        # initialize parser so that lower level functions can be tested.
        self.uip = self.mod.UserInputs(help_description="unit test parsing")

        print("test 2, input list, will parse list")
        self.initialize_user_inputs()
        test_list = self.get_test_list()
        print("test2 test_list=%s" % test_list)
        self.uip.parse_runtime_parameters(
            argv_list=test_list)
        self.verify_parsed_values()

        print("test 3, input named parameter list, will parse list")
        self.initialize_user_inputs()
        self.uip.parse_runtime_parameters(
            argv_list=self.get_named_list("sflag"))
        self.verify_parsed_values()

        print("test 4, input dict, will parse sys.argv argument list")
        self.initialize_user_inputs()
        with patch.object(sys, 'argv', self.get_test_list()):  # noqa e501, pylint:disable=undefined-variable
            self.uip.parse_runtime_parameters(argv_list=None)
        self.verify_parsed_values()

        print("test 5, input dict, will parse sys.argv named args")
        self.initialize_user_inputs()
        with patch.object(sys, 'argv', self.get_named_list("sflag")):  # noqa e501, pylint:disable=undefined-variable
            self.uip.parse_runtime_parameters()
        self.verify_parsed_values()

    def test_validate_argv_inputs(self):
        """
        Verify validate_argv_inputs() works as expected.
        """
        test_cases = {
            "fail_missing_value": {
                "value": None,
                "type": int,
                "default": 1,
                "valid_range": range(0, 4),
                "expected_value": 1,
                },
            "fail_datatype_error": {
                "value": "5",
                "type": int,
                "default": 2,
                "valid_range": range(0, 10),
                "expected_value": 2,
                },
            "fail_out_of_range_int": {
                "value": 6,
                "type": int,
                "default": 3,
                "valid_range": range(0, 3),
                "expected_value": 3,
                },
            "fail_out_of_range_str": {
                "value": "6",
                "type": str,
                "default": "4",
                "valid_range": ["a", "b"],
                "expected_value": "4",
                },
            "in_range_int": {
                "value": 7,
                "type": int,
                "default": 4,
                "valid_range": range(0, 10),
                "expected_value": 7,
                },
            "in_range_str": {
                "value": "8",
                "type": str,
                "default": "5",
                "valid_range": ["a", "8", "abc"],
                "expected_value": "8",
                },
            }

        key = "test_case"
        for test_case, test_dict in test_cases.items():
            result_dict = self.uip.validate_argv_inputs({key: test_dict})
            actual_value = result_dict[key]["value"]

            if "fail_" in test_case:
                expected_value = result_dict[key]["default"]
            else:
                expected_value = result_dict[key]["expected_value"]

            self.assertEqual(expected_value, actual_value,
                             f"test case ({test_case}), "
                             f"expected={expected_value}, "
                             f"actual={actual_value}")


# user input fields
BOOL_FLD = "bool_field"
INT_FLD = "int_field"
FLOAT_FLD = "float_field"
STR_FLD = "str_field"
uip = {}


class UserInputs(util.UserInputs):
    """Manage runtime arguments for generic unit testing."""

    def __init__(self, argv_list=None, help_description=None):
        """
        UserInputs constructor for generic unit testing.

        inputs:
            argv_list(list): override runtime values
            help_description(str): description field for help text
        """
        self.argv_list = argv_list

        # initialize parent class
        super().__init__(argv_list, help_description)

    def initialize_user_inputs(self):
        """
        Populate user_inputs dict.
        """
        # define the user_inputs dict.
        self.user_inputs = {
            BOOL_FLD: {
                "order": 1,    # index in the argv list
                "value": None,
                "type": lambda x: bool(distutils.util.strtobool(
                    str(x).strip())),
                "default": False,
                "valid_range": [True, False, 1, 0],
                "sflag": "-b",
                "lflag": "--" + BOOL_FLD,
                "help": "bool input parameter"},
            INT_FLD: {
                "order": 2,    # index in the argv list
                "value": None,
                "type": int,
                "default": 49,
                "valid_range": range(0, 99),
                "sflag": "-i",
                "lflag": "--" + INT_FLD,
                "help": "int input parameter"},
            FLOAT_FLD: {
                "order": 3,    # index in the argv list
                "value": None,
                "type": float,
                "default": 59.0,
                "valid_range": None,
                "sflag": "-f",
                "lflag": "--" + FLOAT_FLD,
                "help": "float input parameter"},
            STR_FLD: {
                "order": 4,    # index in the argv list
                "value": None,
                "type": str,
                "default": "this is a string",
                "valid_range": None,
                "sflag": "-s",
                "lflag": "--" + STR_FLD,
                "help": "str input parameter"},
        }
        self.valid_sflags = [self.user_inputs[k]["sflag"]
                             for k in self.user_inputs]


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
    print(
        f"DEBUG: ENABLE_FUNCTIONAL_INTEGRATION_TESTS="
        f"{ENABLE_FUNCTIONAL_INTEGRATION_TESTS}")
    print(
        f"DEBUG: ENABLE_PERFORMANCE_INTEGRATION_TESTS="
        f"{ENABLE_PERFORMANCE_INTEGRATION_TESTS}")
    run_all_tests()
