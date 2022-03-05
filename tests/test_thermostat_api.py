"""
Unit test module for thermostat_api.py.
"""
# built-in imports
import os
import sys
import unittest

# local imports
from thermostatsupervisor import emulator_config
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class Test(utc.UnitTest):
    """Test functions in thermostat_api.py."""
    tstat = emulator_config.ALIAS

    def setUp(self):
        super().setUp()
        self.setup_mock_thermostat_zone()
        api.thermostats[self.thermostat_type] = {  # dummy unit test thermostat
            "required_env_variables": {
                "GMAIL_USERNAME": None,
                "GMAIL_PASSWORD": None,
            },
        }

    def tearDown(self):
        self.teardown_mock_thermostat_zone()
        super().tearDown()

    def test_verify_required_env_variables(self):
        """
        Verify verify_required_env_variables() passes in nominal
        condition and fails with missing key.
        """
        missing_key = "agrfg_"  # bogus key should be missing

        # nominal condition, should pass
        print("testing nominal condition, will pass if gmail keys are present")
        self.assertTrue(api.verify_required_env_variables(
            self.thermostat_type, "0"),
            "test failed because one or more gmail keys "
            "are missing")

        # missing key, should raise exception
        print("testing for with missing key 'unit_test', should fail")
        api.thermostats[self.thermostat_type][
            "required_env_variables"][missing_key] = "bogus_value"
        try:
            self.assertFalse(api.verify_required_env_variables(
                self.thermostat_type, "0"),
                f"test passed with missing key '{missing_key}', "
                f"should have failed")
        except KeyError:
            print("KeyError raised as expected for missing key")
        else:
            self.fail("expected KeyError but exception did not occur")
        finally:
            api.thermostats[self.thermostat_type][
                "required_env_variables"].pop(missing_key)

    def test_load_hardware_library(self):
        """
        Verify load_hardware_library() runs without error
        """
        # test successful case
        pkg = api.load_hardware_library(emulator_config.ALIAS)
        print(f"default thermostat returned package type {type(pkg)}")
        self.assertTrue(isinstance(pkg, object),
                        f"dynamic_module_import() returned type({type(pkg)}), "
                        f"expected an object")
        del sys.modules[pkg.__name__]
        del pkg

        # test failing case
        with self.assertRaises(KeyError):
            print("attempting to access 'bogus' dictionary key, "
                  "expect exception...")
            pkg = api.load_hardware_library("bogus")
            print(f"'bogus' returned package type {type(pkg)}, exception "
                  f"should have been raised")
            del pkg
        print("test passed")

    def test_max_measurement_count_exceeded(self):
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
        api.uip = api.UserInputs(None, "unit test parser")
        max_measurement_bkup = api.uip.get_user_inputs(api.MEASUREMENTS_FLD)
        try:
            for test_case, parameters in test_cases.items():
                api.uip.set_user_inputs(api.MEASUREMENTS_FLD,
                                        parameters["max_measurements"])
                act_result = api.uip.max_measurement_count_exceeded(
                    parameters["measurement"])
                exp_result = parameters["exp_result"]
                self.assertEqual(exp_result, act_result,
                                 f"test case '{test_case}', "
                                 f"expected={exp_result}, actual={act_result}")
        finally:
            api.uip.set_user_inputs(api.MEASUREMENTS_FLD, max_measurement_bkup)


class RuntimeParameterTest(utc.RuntimeParameterTest):
    """API Runtime parameter tests."""

    mod = api  # module to test

    script = os.path.realpath(__file__)
    thermostat_type = emulator_config.ALIAS
    zone = 0
    poll_time_sec = 9
    connection_time_sec = 90
    tolerance = 3
    target_mode = "HEAT_MODE"
    measurements = 1

    # fields for testing, mapped to class variables.
    # (value, field name)
    test_fields = [
        (script, os.path.realpath(__file__)),
        (thermostat_type, api.THERMOSTAT_TYPE_FLD),
        (zone, api.ZONE_FLD),
        (poll_time_sec, api.POLL_TIME_FLD),
        (connection_time_sec, api.CONNECT_TIME_FLD),
        (tolerance, api.TOLERANCE_FLD),
        (target_mode, api.TARGET_MODE_FLD),
        (measurements, api.MEASUREMENTS_FLD),
    ]


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
