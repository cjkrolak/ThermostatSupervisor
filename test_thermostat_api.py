"""
Unit test module for thermostat_api.py.
"""
# built-in imports
import unittest

# local imports
import thermostat_api as api
import unit_test_common as utc
import utilities as util


class Test(unittest.TestCase):
    """Test functions in utilities.py."""
    tstat = "UNITTEST"

    def setUp(self):
        api.thermostats[self.tstat] = {  # dummy unit test thermostat
            "required_env_variables": {
                "GMAIL_USERNAME": None,
                "GMAIL_PASSWORD": None,
                },
            }

    def tearDown(self):
        del api.thermostats[self.tstat]

    def test_VerifyRequiredEnvVariables(self):
        """
        Verify verify_required_env_variables() passes in nominal
        condition and fails with missing key.
        """
        missing_key = "agrfg_"  # bogus key should be missing
        utc.print_test_name()
        # nominal condition, should pass
        print("testing nominal condition, will pass if gmail keys are present")
        self.assertTrue(api.verify_required_env_variables(self.tstat, "0"),
                        "test failed because one or more gmail keys "
                        "are missing")

        # missing key, should raise exception
        print("testing for with missing key 'unit_test', should fail")
        api.thermostats[self.tstat][
            "required_env_variables"][missing_key] = "bogus_value"
        try:
            self.assertFalse(api.verify_required_env_variables(
                self.tstat, "0"),
                             "test passed with missing key '%s',"
                             " should have failed" % missing_key)
        except KeyError:
            print("KeyError raised as expected for missing key")
        else:
            self.fail("expected KeyError but exception did not occur")
        finally:
            api.thermostats[self.tstat][
                "required_env_variables"].pop(missing_key)

    def test_ParseRuntimeParameter(self):
        """
        Verify test parse_runtime_parameter() returns expected
        values when input known values.
        """
        utc.print_test_name()
        input_list = ["supervise.py", "honeywell", "0", "9", "90", "3",
                      "HEAT_MODE"]

        # parse thermostat type parameter (argv[1] if present):
        tstat_type = api.parse_runtime_parameter(api.user_input_list[0],
                                                 1, str,
                                                 api.HONEYWELL,
                                                 api.SUPPORTED_THERMOSTATS,
                                                 input_list)
        self.assertEqual(tstat_type, api.HONEYWELL, "actual=%s, expected=%s" %
                         (tstat_type, api.HONEYWELL))

        # parse zone number parameter (argv[2] if present):
        zone_input = \
            api.parse_runtime_parameter(api.user_input_list[1], 2, int, 0,
                                        api.SUPPORTED_THERMOSTATS[
                                            tstat_type]["zones"],
                                        input_list)
        self.assertEqual(zone_input, 0, "actual=%s, expected=%s" %
                         (zone_input, 0))

        # parse the poll time override (argv[3] if present):
        poll_time_input = api.parse_runtime_parameter(api.user_input_list[2],
                                                      3, int,
                                                      10 * 60,
                                                      range(0, 24 * 60 * 60),
                                                      input_list)
        self.assertEqual(poll_time_input, 9, "actual=%s, expected=%s" %
                         (poll_time_input, 9))

        # parse the connection time override (argv[4] if present):
        connection_time_input = \
            api.parse_runtime_parameter(api.user_input_list[3], 4,
                                        int, 8 * 60 * 60,
                                        range(0, 24 * 60 * 60), input_list)
        self.assertEqual(connection_time_input, 90, "actual=%s, expected=%s" %
                         (connection_time_input, 90))

        # parse the tolerance override (argv[5] if present):
        tolerance_degrees_input = \
            api.parse_runtime_parameter(api.user_input_list[4], 5,
                                        int, 2, range(0, 10), input_list)
        self.assertEqual(tolerance_degrees_input, 3, "actual=%s, expected=%s" %
                         (tolerance_degrees_input, 3))

        # parse the target mode override (argv[6] if present):
        target_mode_input = \
            api.parse_runtime_parameter(api.user_input_list[5], 6,
                                        str, None, api.SUPPORTED_THERMOSTATS[
                                            tstat_type]["modes"], input_list)
        self.assertEqual(target_mode_input, "HEAT_MODE", "actual=%s, "
                         "expected=%s" %
                         (target_mode_input, "HEAT_MODE"))

        # test out of range parameter
        # parse the tolerance override (argv[5] if present):
        input_list_backup = input_list
        try:
            input_list[5] = "-1"  # out of range value
            tolerance_degrees_input = \
                api.parse_runtime_parameter(api.user_input_list[4], 5,
                                            int, 2, range(0, 10), input_list)
            # defaults should be used
            default_value = 2
            self.assertEqual(tolerance_degrees_input, default_value,
                             "actual=%s, expected=%s" %
                             (tolerance_degrees_input, default_value))
        finally:
            input_list = input_list_backup  # restore original

        # test missing input parameter
        # parse the tolerance override (argv[5] if present):
        input_list_backup = input_list
        try:
            input_list.pop()  # pop last element
            tolerance_degrees_input = \
                api.parse_runtime_parameter(api.user_input_list[-1],
                                            len(api.user_input_list),
                                            int, 2, range(0, 10), input_list)
            # defaults should be used
            default_value = 2
            self.assertEqual(tolerance_degrees_input, default_value,
                             "actual=%s, expected=%s" %
                             (tolerance_degrees_input, default_value))
        finally:
            input_list = input_list_backup  # restore original

        # test bad data type for position input parameter (should be int)
        with self.assertRaises(TypeError):
            print("attempting to invalid parameter type, "
                  "expect exception...")
            tstat_type = api.parse_runtime_parameter(api.user_input_list[0],
                                                     "1", str,
                                                     api.HONEYWELL,
                                                     api.SUPPORTED_THERMOSTATS,
                                                     input_list)

    def test_ParseAllRuntimeParameters(self):
        """
        Verify test parse_all_runtime_parameters() runs without error
        and return values match user_inputs dict.
        """
        utc.print_test_name()

        return_list = api.parse_all_runtime_parameters(utc.unit_test_argv)
        self.assertEqual(return_list["thermostat_type"],
                         api.user_inputs["thermostat_type"])
        self.assertEqual(return_list["zone"], api.user_inputs["zone"])
        self.assertEqual(return_list["poll_time_sec"],
                         api.user_inputs["poll_time_sec"])
        self.assertEqual(return_list["connection_time_sec"],
                         api.user_inputs["connection_time_sec"])
        self.assertEqual(return_list["tolerance_degrees"],
                         api.user_inputs["tolerance_degrees"])
        self.assertEqual(return_list["target_mode"],
                         api.user_inputs["target_mode"])
        self.assertEqual(return_list["measurements"],
                         api.user_inputs["measurements"])

    def test_DynamicModuleImport(self):
        """
        Verify dynamic_module_import() runs without error
        """
        utc.print_test_name()

        # test successful case
        pkg = api.dynamic_module_import(api.HONEYWELL)
        print("api.HONEYWELL returned package type %s" % type(pkg))
        self.assertTrue(isinstance(pkg, object),
                        "api.dynamic_module_import() returned type(%s),"
                        " expected an object" % type(pkg))
        del pkg

        # test failing case
        with self.assertRaises(ImportError):
            pkg = api.dynamic_module_import("bogus")
            print("'bogus' module returned package type %s" % type(pkg))

    def test_FindModule(self):
        """
        Verify find_module() runs without error
        """
        utc.print_test_name()

        # test successful case
        fp, path, desc = api.find_module(api.HONEYWELL)
        print("api.HONEYWELL returned path %s" % path)
        self.assertTrue(isinstance(path, str),
                        "api.find_module() returned type(%s),"
                        " for path, expected a string" % type(path))
        self.assertTrue(isinstance(desc, tuple),
                        "api.find_module() returned type(%s),"
                        " for desc, expected a string" % type(desc))
        del fp

        # test failing case
        with self.assertRaises(ImportError):
            print("attempting to open invalid file, "
                  "expect exception...")
            fp, path, desc = api.find_module("bogus")
            print("'bogus' module returned fp=%s, path=%s, desc=%s, "
                  "expected an exception" % (fp, path, desc))

    def test_LoadModule(self):
        """
        Verify load_module() runs without error
        """
        utc.print_test_name()

        # test successful case
        fp, path, desc = api.find_module(api.HONEYWELL)
        pkg = api.load_module(api.HONEYWELL, fp, path, desc)
        print("api.HONEYWELL returned package type %s" % type(pkg))
        self.assertTrue(isinstance(pkg, object),
                        "api.load_module() returned type(%s),"
                        " expected an object" % type(pkg))
        del pkg

        # test failing case
        with self.assertRaises(FileNotFoundError):
            print("attempting to load 'bogus' module, expect exception...")
            pkg = api.load_module(api.HONEYWELL, fp, "", desc)
            print("'bogus' module returned package type %s" % type(pkg))

    def test_LoadHardwareLibrary(self):
        """
        Verify load_hardware_library() runs without error
        """
        utc.print_test_name()
        # test successful case
        pkg = api.load_hardware_library(api.HONEYWELL)
        print("api.HONEYWELL returned package type %s" % type(pkg))
        self.assertTrue(isinstance(pkg, object),
                        "api.dynamic_module_import() returned type(%s),"
                        " expected an object" % type(pkg))
        del pkg

        # test failing case
        with self.assertRaises(KeyError):
            print("attempting to access 'bogus' dictionary key, "
                  "expect exception...")
            pkg = api.load_hardware_library("bogus")
            print("'bogus' returned package type %s, "
                  "exception should have been raised" % type(pkg))
            del pkg

    def test_max_measurement_count_exceeded(self):
        """
        Verify max_measurement_count_exceeded() runs as expected.
        """
        utc.print_test_name()
        test_cases = {
            "within_range": {"measurement": 13, "max_measurements": 14,
                             "exp_result": False},
            "at_range": {"measurement": 17, "max_measurements": 17,
                         "exp_result": False},
            "over_range": {"measurement": 15, "max_measurements": 14,
                           "exp_result": True},
            "default": {"measurement": 13, "max_measurements": None,
                        "exp_result": False},
            }
        max_measurement_bkup = api.user_inputs["measurements"]
        try:
            for test_case, parameters in test_cases.items():
                api.user_inputs["measurements"] = \
                    parameters["max_measurements"]
                act_result = api.max_measurement_count_exceeded(
                    parameters["measurement"])
                exp_result = parameters["exp_result"]
                self.assertEqual(exp_result, act_result,
                                 "test case '%s', expected=%s, actual=%s" %
                                 (test_case, exp_result, act_result))
        finally:
            api.user_inputs["measurements"] = max_measurement_bkup


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
