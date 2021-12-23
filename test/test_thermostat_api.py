"""
Unit test module for thermostat_api.py.
"""
# built-in imports
import sys
import unittest

# local imports
from supervisor import azure_context  # noqa F401, pylint: disable=unused-import.
from supervisor import thermostat_api as api
import unit_test_common as utc
from supervisor import utilities as util


class Test(utc.UnitTest):
    """Test functions in utilities.py."""
    tstat = "UNITTEST"

    def setUp(self):
        self.print_test_name()
        api.thermostats[self.tstat] = {  # dummy unit test thermostat
            "required_env_variables": {
                "GMAIL_USERNAME": None,
                "GMAIL_PASSWORD": None,
                },
            }

    def tearDown(self):
        del api.thermostats[self.tstat]
        self.print_test_result()

    def test_VerifyRequiredEnvVariables(self):
        """
        Verify verify_required_env_variables() passes in nominal
        condition and fails with missing key.
        """
        missing_key = "agrfg_"  # bogus key should be missing

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
        tstat_type = api.DEFAULT_THERMOSTAT
        test_list = [
            "supervise.py",  # script
            tstat_type,  # thermostat_type
            "0",  # zone
            "9",  # poll time sec
            "90",  # connection time
            "3",  # tolerance
            "HEAT_MODE",  # target mode
            1,  # measurements
            ]

        # test case default should be different from test_list above
        test_cases = {
            "thermostat_type": {"datatype": str,
                                "default_value": "bogus",
                                "supported_values": api.SUPPORTED_THERMOSTATS,
                                "input_list": test_list,
                                },
            "zone": {"datatype": int,
                     "default_value": 2,
                     "supported_values": api.SUPPORTED_THERMOSTATS[
                         tstat_type]["zones"],
                     "input_list": test_list,
                     },
            "poll_time_sec": {"datatype": int,
                              "default_value": 10 * 60,
                              "supported_values": range(0, 24 * 60 * 60),
                              "input_list": test_list,
                              },
            "connection_time_sec": {"datatype": int,
                                    "default_value": 8 * 60 * 60,
                                    "supported_values": range(0, 24 * 60 * 60),
                                    "input_list": test_list,
                                    },
            "tolerance_degrees": {"datatype": int,
                                  "default_value": 2,
                                  "supported_values": range(0, 10),
                                  "input_list": test_list,
                                  },
            "target_mode": {"datatype": str,
                            "default_value": "OFF_MODE",
                            "supported_values": api.SUPPORTED_THERMOSTATS[
                                tstat_type]["modes"],
                            "input_list": test_list,
                            },
            "measurements": {"datatype": int,
                             "default_value": 2,
                             "supported_values": range(0, 100000),
                             "input_list": test_list,
                             },
            }

        for key, inputs in test_cases.items():
            print("testing parse of input parameter=%s" % key)
            expected_value = inputs["datatype"](test_list[
                api.get_argv_position(key)])
            actual_value = api.parse_runtime_parameter(
                key,
                inputs["datatype"],
                inputs["default_value"],
                inputs["supported_values"],
                inputs["input_list"]
                )
            print("key=%s, actual=%s, expected=%s" % (key, actual_value,
                                                      expected_value))
            self.assertEqual(actual_value, expected_value,
                             "actual=%s, expected=%s" %
                             (actual_value, expected_value))

        # test out of range parameter
        # parse the tolerance override:
        test_list_backup = test_list
        try:
            # out of range value
            key = "tolerance_degrees"
            test_list[api.get_argv_position(key)] = "-1"

            # defaults should be used
            default_value = 2
            tolerance_degrees_input = \
                api.parse_runtime_parameter(key, int, default_value,
                                            range(0, 10), test_list)
            self.assertEqual(tolerance_degrees_input, default_value,
                             "actual=%s, expected=%s" %
                             (tolerance_degrees_input, default_value))
        finally:
            test_list = test_list_backup  # restore original

        # test missing input parameter
        # parse the tolerance override:
        test_list_backup = test_list
        try:
            key = api.argv_order[len(api.argv_order) - 1]
            test_list.pop(-1)  # pop last element
            # defaults should be used
            default_value = 2
            measurements_input = \
                api.parse_runtime_parameter(key,
                                            int, str(default_value),
                                            range(0, 10),
                                            test_list)
            self.assertEqual(measurements_input, default_value,
                             "actual=%s, expected=%s" %
                             (measurements_input, default_value))
        finally:
            test_list = test_list_backup  # restore original

        # test bad data type for position input parameter (should be int)
        with self.assertRaises(TypeError):
            print("attempting to invalid parameter type, "
                  "expect exception...")
            tstat_type = api.parse_runtime_parameter(
                "thermostat_type",
                "bogus",  # datatype
                api.DEFAULT_THERMOSTAT,
                api.SUPPORTED_THERMOSTATS,
                test_list)

        # test default behavior with input_list == None
        print("argv list=%s" % sys.argv)
        expected_result = [api.DEFAULT_THERMOSTAT]
        argv0 = api.parse_runtime_parameter(
            "thermostat_type",
            str,
            api.DEFAULT_THERMOSTAT,
            expected_result,
            argv_list=None)
        self.assertTrue(argv0 in expected_result, "actual=%s, expected=%s" %
                        (argv0, expected_result))

    def test_ParseAllRuntimeParameters(self):
        """
        Verify test parse_all_runtime_parameters() runs without error
        and return values match user_inputs dict.
        """

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

        # test default case
        print("argv list=%s" % sys.argv)
        # argv=['python -m unittest', 'discover', '-v'] case
        if '-v' in sys.argv:
            # parsing should fail parsing -v from argv list
            with self.assertRaises(ValueError):
                print("attempting to run parse_all_runtime_parameters() with "
                      "unittest argv list, should fail for ValueError since "
                      "'-v' is not parseable into a value...")
                return_list = api.parse_all_runtime_parameters()
                print("parsed input parameter list=%s" % return_list)
        else:
            if len(sys.argv) > 1:
                # argv list > 1, arbitrary list, can't evaluate
                print("unittest sys.argv list is not empty, parsing result "
                      "is indeterminant")
            else:
                # argv list is 1 element, thermostat_type missing, will default
                expected_result = [api.DEFAULT_THERMOSTAT]
                return_list = api.parse_all_runtime_parameters()

                self.assertTrue(return_list[
                    "thermostat_type"] in expected_result,
                    "actual=%s, expected=%s" %
                    (return_list["thermostat_type"], expected_result))

    def test_DynamicModuleImport(self):
        """
        Verify dynamic_module_import() runs without error

        TODO: this module results in a resourcewarning within unittest:
        sys:1: ResourceWarning: unclosed <socket.socket fd=628,
        family=AddressFamily.AF_INET, type=SocketKind.SOCK_DGRAM, proto=0,
        laddr=('0.0.0.0', 64963)>
        """

        # test successful case
        pkg = api.dynamic_module_import(api.DEFAULT_THERMOSTAT)
        print("default thermostat returned package type %s" % type(pkg))
        self.assertTrue(isinstance(pkg, object),
                        "api.dynamic_module_import() returned type(%s),"
                        " expected an object" % type(pkg))
        del sys.modules[api.DEFAULT_THERMOSTAT]
        del pkg

        # test failing case
        with self.assertRaises(ImportError):
            print("attempting to open bogus package name, expect exception...")
            pkg = api.dynamic_module_import("bogus")
            print("'bogus' module returned package type %s" % type(pkg))
        print("test passed")

    def test_FindModule(self):
        """
        Verify find_module() runs without error
        """

        # test successful case
        fp, path, desc = api.find_module(api.DEFAULT_THERMOSTAT)
        print("default thermostat returned path %s" % path)
        self.assertTrue(isinstance(path, str),
                        "api.find_module() returned type(%s),"
                        " for path, expected a string" % type(path))
        self.assertTrue(isinstance(desc, tuple),
                        "api.find_module() returned type(%s),"
                        " for desc, expected a string" % type(desc))
        fp.close()

        # test failing case
        with self.assertRaises(ImportError):
            print("attempting to open invalid file, "
                  "expect exception...")
            fp, path, desc = api.find_module("bogus")
            print("'bogus' module returned fp=%s, path=%s, desc=%s, "
                  "expected an exception" % (fp, path, desc))
        print("test passed")

    def test_LoadModule(self):
        """
        Verify load_module() runs without error
        """
        # test successful case
        try:
            fp, path, desc = api.find_module(api.DEFAULT_THERMOSTAT)
            pkg = api.load_module(api.DEFAULT_THERMOSTAT, fp, path, desc)
            print("default thermostat returned package type %s" % type(pkg))
            self.assertTrue(isinstance(pkg, object),
                            "api.load_module() returned type(%s),"
                            " expected an object" % type(pkg))
            del pkg

            # test failing case
            with self.assertRaises(FileNotFoundError):
                print("attempting to load 'bogus' module, expect exception...")
                pkg = api.load_module(api.DEFAULT_THERMOSTAT, fp, "", desc)
                print("'bogus' module returned package type %s" % type(pkg))
            print("test passed")
        finally:
            fp.close()

    def test_LoadHardwareLibrary(self):
        """
        Verify load_hardware_library() runs without error
        """
        # test successful case
        pkg = api.load_hardware_library(api.DEFAULT_THERMOSTAT)
        print("default thermostat returned package type %s" % type(pkg))
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
        print("test passed")

    def test_MaxMeasurementCountExceeded(self):
        """
        Verify max_measurement_count_exceeded() runs as expected.
        """
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