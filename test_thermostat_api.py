"""
Unit test module for thermostat_api.py.
"""
# built-in imports
import random
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

    # def test_SetTargetZone(self):
    #     """
    #     Confirm target zone can be set and read back.
    #     """
    #     utc.print_test_name()
    #     test_cases = self.generate_random_list(10, 0, 99)
    #     for zone in test_cases:
    #         print("testing set_target_zone(%s)" % zone)
    #         api.set_target_zone(self.tstat, zone)
    #         self.assertEqual(api.thermostats[self.tstat]["zone"], zone)

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

    def generate_random_list(self, count, min_val, max_val):
        """
        Generate a list of random numbers between a range.

        inputs:
            count(int): number of values
            min_val(int): lower end of range
            max_val(int): upper end of range.
        returns:
            list
        """
        random_list = []
        for _ in range(0, count):
            n = random.randint(min_val, max_val)
            random_list.append(n)
        return random_list

    def test_ParseRuntimeParameter(self):
        """
        Verify test parse_runtime_parameter() returns expected
        values when input known values.
        """
        utc.print_test_name()
        input_list = ["supervise.py", "honeywell", "0", "9", "90", "3"]

        # parse thermostat type parameter (argv[1] if present):
        tstat_type = api.parse_runtime_parameter("thermostat_type", 1, str,
                                                 api.HONEYWELL,
                                                 api.SUPPORTED_THERMOSTATS,
                                                 input_list)
        self.assertEqual(tstat_type, api.HONEYWELL, "actual=%s, expected=%s" %
                         (tstat_type, api.HONEYWELL))

        # parse zone number parameter (argv[2] if present):
        zone_input = \
            api.parse_runtime_parameter("zone", 2, int, 0,
                                        api.SUPPORTED_THERMOSTATS[
                                            tstat_type]["zones"],
                                        input_list)
        self.assertEqual(zone_input, 0, "actual=%s, expected=%s" %
                         (zone_input, 0))

        # parse the poll time override (argv[3] if present):
        poll_time_input = api.parse_runtime_parameter("poll_time_sec", 3, int,
                                                      10 * 60,
                                                      range(0, 24 * 60 * 60),
                                                      input_list)
        self.assertEqual(poll_time_input, 9, "actual=%s, expected=%s" %
                         (poll_time_input, 9))

        # parse the connection time override (argv[4] if present):
        connection_time_input = \
            api.parse_runtime_parameter("connection_time_sec", 4,
                                        int, 8 * 60 * 60,
                                        range(0, 24 * 60 * 60), input_list)
        self.assertEqual(connection_time_input, 90, "actual=%s, expected=%s" %
                         (connection_time_input, 90))

        # parse the tolerance override (argv[5] if present):
        tolerance_degrees_input = \
            api.parse_runtime_parameter("tolerance_degrees", 5,
                                        int, 2, range(0, 10), input_list)
        self.assertEqual(tolerance_degrees_input, 3, "actual=%s, expected=%s" %
                         (tolerance_degrees_input, 3))

        # test out of range parameter
        # parse the tolerance override (argv[5] if present):
        input_list_backup = input_list
        try:
            input_list[5] = "-1"  # out of range value
            tolerance_degrees_input = \
                api.parse_runtime_parameter("tolerance_degrees", 5,
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
            input_list.pop(5)  # pop 5th element
            tolerance_degrees_input = \
                api.parse_runtime_parameter("tolerance_degrees", 5,
                                            int, 2, range(0, 10), input_list)
            # defaults should be used
            default_value = 2
            self.assertEqual(tolerance_degrees_input, default_value,
                             "actual=%s, expected=%s" %
                             (tolerance_degrees_input, default_value))
        finally:
            input_list = input_list_backup  # restore original

    def test_ParseAllRuntimeParameters(self):
        """
        Verify test parse_all_runtime_parameters() runs without error
        and return values match user_inputs dict.
        """
        utc.print_test_name()

        return_list = api.parse_all_runtime_parameters()
        self.assertEqual(return_list[0], api.user_inputs["thermostat_type"])
        self.assertEqual(return_list[1], api.user_inputs["zone"])
        self.assertEqual(return_list[2], api.user_inputs["poll_time_sec"])
        self.assertEqual(return_list[3],
                         api.user_inputs["connection_time_sec"])
        self.assertEqual(return_list[4], api.user_inputs["tolerance_degrees"])

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

    def ttest_LoadHardwareLibrary(self):
        """
        Verify load_hardware_library() runs without error
        """
        # test successful case
        pkg = api.load_hardware_library(api.HONEYWELL)
        print("api.HONEYWELL returned package type %s" % type(pkg))
        del pkg

        # test failing case
        with self.assertRaises(KeyError):
            pkg = api.load_hardware_library("bogus")
            print("'bogus' returned package type %s" % type(pkg))
            del pkg


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()
