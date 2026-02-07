"""
Unit test module for thermostat_api.py.
"""

# built-in imports
import os
import sys
import unittest

# local imports
from src import emulator_config
from src import thermostat_api as api
from src import utilities as util
from tests import unit_test_common as utc

thermostat_type = emulator_config.ALIAS
zone_name = emulator_config.default_zone_name


class Test(utc.UnitTest):
    """Test functions in thermostat_api.py."""

    tstat = thermostat_type
    zone_name = zone_name

    def setUp(self):
        super().setUp()
        # Save original thermostat configuration before any modifications
        self.original_thermostat_config = None
        if self.thermostat_type in api.thermostats:
            self.original_thermostat_config = api.thermostats[
                self.thermostat_type
            ].copy()

        # Set up mock configuration without using setup_mock_thermostat_zone
        # since that conflicts with our save/restore logic
        api.thermostats[self.thermostat_type] = {  # dummy unit test thermostat
            "required_env_variables": {
                "GMAIL_USERNAME": None,
                "GMAIL_PASSWORD": None,
            },
        }

        # Set up user inputs manually to avoid calling setup_mock_thermostat_zone
        self.unit_test_argv = ["supervise.py", self.thermostat_type, "0"]
        self.user_inputs_backup = getattr(api.uip, "user_inputs", None)

    def tearDown(self):
        try:
            # Restore original thermostat configuration
            if self.original_thermostat_config is not None and hasattr(
                self, "original_thermostat_config"
            ):
                api.thermostats[self.thermostat_type] = self.original_thermostat_config

            # Restore user inputs backup
            if hasattr(self, "user_inputs_backup") and api.uip:
                api.uip.user_inputs = self.user_inputs_backup
        finally:
            super().tearDown()

    def test_verify_required_env_variables(self):
        """
        Verify verify_required_env_variables() passes in nominal
        condition and fails with missing key.
        """
        from unittest.mock import patch

        missing_key = "agrfg_"  # bogus key should be missing

        # Mock environment variables for testing
        mock_env = {
            "GMAIL_USERNAME": "test@example.com",
            "GMAIL_PASSWORD": "test_password",
        }

        # nominal condition, should pass
        print("testing nominal condition, will pass if gmail keys are present")
        with patch.dict("os.environ", mock_env):
            self.assertTrue(
                api.verify_required_env_variables(self.thermostat_type, "0"),
                "test failed because one or more gmail keys are missing",
            )

        # missing key, should raise exception
        print("testing for with missing key 'unit_test', should fail")
        api.thermostats[self.thermostat_type]["required_env_variables"][
            missing_key
        ] = "bogus_value"
        try:
            with patch.dict("os.environ", mock_env):
                self.assertFalse(
                    api.verify_required_env_variables(self.thermostat_type, "0"),
                    f"test passed with missing key '{missing_key}', should have failed",
                )
        except KeyError:
            print("KeyError raised as expected for missing key")
        else:
            self.fail("expected KeyError but exception did not occur")
        finally:
            api.thermostats[self.thermostat_type]["required_env_variables"].pop(
                missing_key
            )

    def test_load_hardware_library(self):
        """
        Verify load_hardware_library() runs without error
        """
        # test successful case
        pkg = api.load_hardware_library(emulator_config.ALIAS)
        print(f"default thermostat returned package type {type(pkg)}")
        self.assertTrue(
            isinstance(pkg, object),
            f"dynamic_module_import() returned type({type(pkg)}), "
            f"expected an object",
        )
        print(f"package name={pkg.__name__}")
        del sys.modules[pkg.__name__]
        del pkg

        # test failing case
        with self.assertRaises(KeyError):
            print("attempting to access 'bogus' dictionary key, expect exception...")
            pkg = api.load_hardware_library("bogus")
            print(
                f"'bogus' returned package type {type(pkg)}, exception "
                f"should have been raised"
            )
            del pkg
        print("test passed")

    def test_max_measurement_count_exceeded(self):
        """
        Verify max_measurement_count_exceeded() runs as expected.
        """
        test_cases = {
            "within_range": {
                "measurement": 13,
                "max_measurements": 14,
                "exp_result": False,
            },
            "at_range": {
                "measurement": 17,
                "max_measurements": 17,
                "exp_result": False,
            },
            "over_range": {
                "measurement": 15,
                "max_measurements": 14,
                "exp_result": True,
            },
            "default": {
                "measurement": 13,
                "max_measurements": None,
                "exp_result": False,
            },
        }
        # backup max_measurements
        api.uip = api.UserInputs(
            self.unit_test_argv, "unit test parser", self.tstat, self.zone_name
        )
        max_measurement_bkup = api.uip.get_user_inputs(
            api.uip.zone_name, api.input_flds.measurements
        )
        try:
            for test_case, parameters in test_cases.items():
                api.uip.set_user_inputs(
                    api.uip.zone_name,
                    api.input_flds.measurements,
                    parameters["max_measurements"],
                )
                act_result = api.uip.max_measurement_count_exceeded(
                    parameters["measurement"]
                )
                exp_result = parameters["exp_result"]
                self.assertEqual(
                    exp_result,
                    act_result,
                    f"test case '{test_case}', "
                    f"expected={exp_result}, actual={act_result}",
                )
        finally:
            # restore max masurements
            api.uip.set_user_inputs(
                api.uip.zone_name, api.input_flds.measurements, max_measurement_bkup
            )

    def test_load_user_inputs(self):
        """Test load_user_inputs() function."""
        # Mock a config module
        from unittest.mock import MagicMock

        mock_config = MagicMock()
        mock_config.default_zone_name = "test_zone"
        mock_config.argv = ["test_script", "emulator", "0"]
        mock_config.ALIAS = "emulator"

        # Call load_user_inputs
        zone_number = api.load_user_inputs(mock_config)

        # Verify that the UserInputs was created and zone number returned
        self.assertIsInstance(zone_number, int)
        self.assertEqual(zone_number, 0)

        # Verify global uip was set
        self.assertIsNotNone(api.uip)
        # The zone_name gets modified to include thermostat type and zone number
        self.assertTrue(api.uip.zone_name.startswith("emulator"))


class RuntimeParameterTest(utc.RuntimeParameterTest):
    """API Runtime parameter tests."""

    mod = api  # module to test

    script = os.path.realpath(__file__)
    thermostat_type = thermostat_type
    # parent_key = zone_name  # aka zone_name in this context
    zone_number = 0
    poll_time_sec = 9
    connection_time_sec = 90
    tolerance = 3
    target_mode = "HEAT_MODE"
    measurements = 1
    input_file = utc.unit_test_argv_file

    # fields for testing, mapped to class variables.
    # (value, field name)
    test_fields = [
        (script, os.path.realpath(__file__)),
        (thermostat_type, api.input_flds.thermostat_type),
        (zone_number, api.input_flds.zone),
        (poll_time_sec, api.input_flds.poll_time),
        (connection_time_sec, api.input_flds.connection_time),
        (tolerance, api.input_flds.tolerance),
        (target_mode, api.input_flds.target_mode),
        (measurements, api.input_flds.measurements),
    ]
    # test case with input file
    test_fields_with_file = [
        (script, os.path.realpath(__file__)),
        (thermostat_type, api.input_flds.thermostat_type),
        (zone_number, api.input_flds.zone),
        (poll_time_sec, api.input_flds.poll_time),
        (connection_time_sec, api.input_flds.connection_time),
        (tolerance, api.input_flds.tolerance),
        (target_mode, api.input_flds.target_mode),
        (measurements, api.input_flds.measurements),
        (input_file, api.input_flds.input_file),
    ]


if __name__ == "__main__":
    util.log_msg.debug = True  # type: ignore[attr-defined]
    unittest.main(verbosity=2)
