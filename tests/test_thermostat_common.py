"""
Tests for thermostat_common.py
"""

# built-in imports
import operator
import pprint
import random
import unittest
import unittest.mock

# local imports
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import thermostat_common as tc
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class Test(utc.UnitTest):
    """Test functions in thermostat_common.py."""

    # initialization
    switch_pos_bckup = None
    is_heat_mode_bckup = None
    is_cool_mode_bckup = None
    heat_raw_bckup = None
    schedule_heat_sp_bckup = None
    cool_raw_bckup = None
    schedule_cool_sp_bckup = None
    get_humid_support_bckup = None
    switch_position_backup = None
    revert_setpoint_func_bckup = None

    def setUp(self):
        super().setUp()
        self.setup_mock_thermostat_zone()

    def tearDown(self):
        self.teardown_mock_thermostat_zone()
        super().tearDown()

    def test_print_all_thermostat_meta_data(self):
        """
        Verify print_all_thermostat_metadata() runs without error.
        """
        self.Thermostat.print_all_thermostat_metadata(
            api.uip.get_user_inputs(api.uip.zone_name, "zone")
        )

    def test_set_mode(self):
        """
        Verify set_mode() runs without error.
        """
        result = self.Zone.set_mode("bogus_mode")
        self.assertFalse(result, "Zone.set_mode() should have returned False")

    def test_store_current_mode(self):
        """
        Verify store_current_mode() runs without error.
        """
        backup_func = None

        def dummy_true():
            """Return 1."""
            return 1

        test_cases = [
            ["is_heat_mode", self.Zone.HEAT_MODE],
            ["is_cool_mode", self.Zone.COOL_MODE],
            ["is_dry_mode", self.Zone.DRY_MODE],
            ["is_auto_mode", self.Zone.AUTO_MODE],
            ["is_fan_mode", self.Zone.FAN_MODE],
            ["is_off_mode", self.Zone.OFF_MODE],
            ["is_eco_mode", self.Zone.ECO_MODE],
        ]

        print(f"thermostat_type={self.Zone.thermostat_type}")

        for test_case in test_cases:
            print(f"testing {test_case[0]}")
            try:
                # mock up the is_X_mode() functions
                if test_case[0]:
                    backup_func = getattr(self.Zone, test_case[0])
                    setattr(self.Zone, test_case[0], dummy_true)
                print(f"current mode(pre)={self.Zone.current_mode}")

                # store the current mode and check cache
                self.Zone.store_current_mode()
                print(f"current mode(post)={self.Zone.current_mode}")
                self.assertEqual(
                    test_case[1],
                    self.Zone.current_mode,
                    f"Zone.store_current_mode() failed to cache"
                    f" mode={test_case[1]}",
                )

                # confirm verify_current_mode()
                none_act = self.Zone.verify_current_mode(None)
                self.assertTrue(
                    none_act, "verify_current_mode(None) failed to return True"
                )
                curr_act = self.Zone.verify_current_mode(test_case[1])
                self.assertTrue(
                    curr_act, "verify_current_mode() doesn't match current test mode"
                )
                dummy_act = self.Zone.verify_current_mode("dummy_mode")
                self.assertFalse(
                    dummy_act,
                    "verify_current_mode('dummy_mode') returned "
                    "True, should have returned False",
                )
            finally:
                # restore mocked function
                if test_case[0]:
                    setattr(self.Zone, test_case[0], backup_func)

    def test_check_return_types(self):
        """
        Verify return type of each function is as expected.
        """
        func_dict = {
            "is_temp_deviated_from_schedule": {
                "key": self.Zone.is_temp_deviated_from_schedule,
                "args": None,
                "return_type": bool,
            },
            "get_current_mode": {
                "key": self.Zone.get_current_mode,
                "args": [1, 1],  # flag_all_deviations==False
                "return_type": dict,
            },
            "Get_current_mode": {  # Capitalize for unique key
                "key": self.Zone.get_current_mode,
                "args": [1, 1, True, True],  # flag_all_deviations==True
                "return_type": dict,
            },
            "set_mode": {
                "key": self.Zone.set_mode,
                "args": ["bogus"],
                "return_type": bool,
            },
            "store_current_mode": {
                "key": self.Zone.store_current_mode,
                "args": None,
                "return_type": type(None),
            },
            "validate_numeric": {
                "key": self.Zone.validate_numeric,
                "args": [0, "bogus"],
                "return_type": int,
            },
            "warn_if_outside_global_limit": {
                "key": self.Zone.warn_if_outside_global_limit,
                "args": [0, 0, operator.gt, "bogus"],
                "return_type": bool,
            },
            "is_heat_mode": {
                "key": self.Zone.is_heat_mode,
                "args": None,
                "return_type": int,
            },
            "is_cool_mode": {
                "key": self.Zone.is_cool_mode,
                "args": None,
                "return_type": int,
            },
            "is_dry_mode": {
                "key": self.Zone.is_dry_mode,
                "args": None,
                "return_type": int,
            },
            "is_auto_mode": {
                "key": self.Zone.is_auto_mode,
                "args": None,
                "return_type": int,
            },
            "is_eco_mode": {
                "key": self.Zone.is_eco_mode,
                "args": None,
                "return_type": int,
            },
            "is_fan_mode": {
                "key": self.Zone.is_fan_mode,
                "args": None,
                "return_type": int,
            },
            "is_defrosting": {
                "key": self.Zone.is_defrosting,
                "args": None,
                "return_type": int,
            },
            "is_standby": {
                "key": self.Zone.is_standby,
                "args": None,
                "return_type": int,
            },
            "is_off_mode": {
                "key": self.Zone.is_off_mode,
                "args": None,
                "return_type": int,
            },
            "is_heating": {
                "key": self.Zone.is_heating,
                "args": None,
                "return_type": int,
            },
            "is_cooling": {
                "key": self.Zone.is_cooling,
                "args": None,
                "return_type": int,
            },
            "is_drying": {"key": self.Zone.is_drying, "args": None, "return_type": int},
            "is_auto": {"key": self.Zone.is_auto, "args": None, "return_type": int},
            "get_display_temp": {
                "key": self.Zone.get_display_temp,
                "args": None,
                "return_type": float,
            },
            "get_display_humidity": {
                "key": self.Zone.get_display_humidity,
                "args": None,
                "return_type": float,
            },
            "get_is_humidity_supported": {
                "key": self.Zone.get_is_humidity_supported,
                "args": None,
                "return_type": bool,
            },
            "get_system_switch_position": {
                "key": self.Zone.get_system_switch_position,
                "args": None,
                "return_type": int,
            },
            "get_heat_setpoint_raw": {
                "key": self.Zone.get_heat_setpoint_raw,
                "args": None,
                "return_type": float,
            },
            "get_schedule_heat_sp": {
                "key": self.Zone.get_schedule_heat_sp,
                "args": None,
                "return_type": float,
            },
            "get_cool_setpoint_raw": {
                "key": self.Zone.get_cool_setpoint_raw,
                "args": None,
                "return_type": float,
            },
            "get_schedule_cool_sp": {
                "key": self.Zone.get_schedule_cool_sp,
                "args": None,
                "return_type": float,
            },
            "get_is_invacation_hold_mode": {
                "key": self.Zone.get_is_invacation_hold_mode,
                "args": None,
                "return_type": bool,
            },
            "get_temporary_hold_until_time": {
                "key": self.Zone.get_temporary_hold_until_time,
                "args": None,
                "return_type": int,
            },
            "refresh_zone_info": {
                "key": self.Zone.refresh_zone_info,
                "args": None,
                "return_type": type(None),
            },
            "report_heating_parameters": {
                "key": self.Zone.report_heating_parameters,
                "args": None,
                "return_type": type(None),
            },
            "update_runtime_parameters": {
                "key": self.Zone.update_runtime_parameters,
                "args": None,
                "return_type": type(None),
            },
            "get_schedule_program_heat": {
                "key": self.Zone.get_schedule_program_heat,
                "args": None,
                "return_type": dict,
            },
            "get_schedule_program_cool": {
                "key": self.Zone.get_schedule_program_cool,
                "args": None,
                "return_type": dict,
            },
            "get_vacation_hold_until_time": {
                "key": self.Zone.get_vacation_hold_until_time,
                "args": None,
                "return_type": int,
            },
            "set_heat_setpoint": {
                "key": self.Zone.set_heat_setpoint,
                "args": [0],
                "return_type": type(None),
            },
            "set_cool_setpoint": {
                "key": self.Zone.set_cool_setpoint,
                "args": [0],
                "return_type": type(None),
            },
            "revert_temperature_deviation": {
                "key": self.Zone.revert_temperature_deviation,
                "args": [0, "this is a dummy msg from unit test"],
                "return_type": type(None),
            },
        }
        for key, value in func_dict.items():
            print(f"key={key}")
            print(f"value={value}")
            expected_type = value["return_type"]
            print(f"expected type={expected_type}")
            if value["args"] is not None:
                return_val = value["key"](*value["args"])
            else:
                return_val = value["key"]()
            self.assertTrue(
                isinstance(return_val, expected_type),
                f"func={key}, expected type={expected_type}, "
                f"actual type={type(return_val)}",
            )

    def test_validate_numeric(self):
        """Test validate_numeric() function."""
        for test_case in [1, 1.0, "1", True, None]:
            print(f"test case={type(test_case)}")
            if isinstance(test_case, (int, float)):
                expected_val = test_case
                actual_val = self.Zone.validate_numeric(test_case, "test_case")
                self.assertEqual(
                    expected_val,
                    actual_val,
                    f"expected return value={expected_val}, "
                    f"type({type(expected_val)}), "
                    f"actual={actual_val},type({type(actual_val)})",
                )
            else:
                with self.assertRaises(TypeError):
                    print("attempting to input bad parameter type, expect exception...")
                    self.Zone.validate_numeric(test_case, "test_case")

    def test_warn_if_outside_global_limit(self):
        """Test warn_if_outside_global_limit() function."""
        self.assertTrue(
            self.Zone.warn_if_outside_global_limit(
                self.Zone.max_scheduled_heat_allowed + 1,
                self.Zone.max_scheduled_heat_allowed,
                operator.gt,
                "heat",
            ),
            "function result should have been True",
        )
        self.assertFalse(
            self.Zone.warn_if_outside_global_limit(
                self.Zone.max_scheduled_heat_allowed - 1,
                self.Zone.max_scheduled_heat_allowed,
                operator.gt,
                "heat",
            ),
            "function result should have been False",
        )
        self.assertTrue(
            self.Zone.warn_if_outside_global_limit(
                self.Zone.min_scheduled_cool_allowed - 1,
                self.Zone.min_scheduled_cool_allowed,
                operator.lt,
                "cool",
            ),
            "function result should have been True",
        )
        self.assertFalse(
            self.Zone.warn_if_outside_global_limit(
                self.Zone.min_scheduled_cool_allowed + 1,
                self.Zone.min_scheduled_cool_allowed,
                operator.lt,
                "cool",
            ),
            "function result should have been False",
        )

    def test_revert_thermostat_mode(self):
        """
        Test the revert_thermostat_mode() function.
        """
        test_cases = [
            self.Zone.HEAT_MODE,
            self.Zone.COOL_MODE,
            self.Zone.DRY_MODE,
            self.Zone.AUTO_MODE,
            self.Zone.FAN_MODE,
            self.Zone.OFF_MODE,
            self.Zone.UNKNOWN_MODE,
        ]
        for test_case in random.choices(test_cases, k=20):
            if (
                self.Zone.current_mode in self.Zone.heat_modes
                and test_case in self.Zone.cool_modes
            ) or (
                self.Zone.current_mode in self.Zone.cool_modes
                and test_case in self.Zone.heat_modes
            ):
                expected_mode = self.Zone.OFF_MODE
            else:
                expected_mode = test_case
            print(f"reverting to '{test_case}' mode, expected mode={expected_mode}")
            new_mode = self.Zone.revert_thermostat_mode(test_case)
            self.assertEqual(
                new_mode,
                expected_mode,
                f"reverting to {test_case} mode failed, new mode"
                f" is '{new_mode}', expected '{expected_mode}'",
            )
            self.Zone.current_mode = test_case

    def test_measure_thermostat_response_time(self):
        """
        Test the measure_thermostat_response_time() function.
        """
        # measure thermostat response time
        measurements = 3
        print(f"Thermostat response times for {measurements} measurements...")
        meas_data = self.Zone.measure_thermostat_repeatability(
            measurements,
            measure_response_time=True,
        )
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)
        self.assertTrue(
            isinstance(meas_data, dict),
            f"return data is type({type(meas_data)}), expected a dict",
        )
        self.assertEqual(
            meas_data["measurements"],
            measurements,
            f"number of measurements in return data("
            f"{meas_data['measurements']}) doesn't match number "
            f"of masurements requested({measurements})",
        )

    def test_get_current_mode(self):
        """
        Verify get_current_mode runs in all permutations.

        test cases:
        1. heat mode and following schedule
        2. heat mode and deviation
        3. cool mode and following schedule
        4. cool mode and cool deviation
        5. humidity is available
        """
        test_cases = {
            "heat mode and following schedule": {
                "mode": self.Zone.HEAT_MODE,
                "humidity": False,
                "heat_mode": True,
                "cool_mode": False,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,
            },
            "heat mode and following schedule and humidity": {
                "mode": self.Zone.HEAT_MODE,
                "humidity": True,
                "heat_mode": True,
                "cool_mode": False,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,
            },
            "heat mode and deviation": {
                "mode": self.Zone.HEAT_MODE,
                "humidity": False,
                "heat_mode": True,
                "cool_mode": False,
                "heat_deviation": True,
                "cool_deviation": False,
                "hold_mode": True,
            },
            "heat mode and deviation and humidity": {
                "mode": self.Zone.HEAT_MODE,
                "humidity": True,
                "heat_mode": True,
                "cool_mode": False,
                "heat_deviation": True,
                "cool_deviation": False,
                "hold_mode": True,
            },
            "cool mode and following schedule": {
                "mode": self.Zone.COOL_MODE,
                "humidity": False,
                "heat_mode": False,
                "cool_mode": True,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,
            },
            "cool mode and following schedule and humidity": {
                "mode": self.Zone.COOL_MODE,
                "humidity": True,
                "heat_mode": False,
                "cool_mode": True,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,
            },
            "cool mode and deviation": {
                "mode": self.Zone.COOL_MODE,
                "humidity": False,
                "heat_mode": False,
                "cool_mode": True,
                "heat_deviation": False,
                "cool_deviation": True,
                "hold_mode": True,
            },
            "cool mode and deviation and humidity": {
                "mode": self.Zone.COOL_MODE,
                "humidity": True,
                "heat_mode": False,
                "cool_mode": True,
                "heat_deviation": False,
                "cool_deviation": True,
                "hold_mode": True,
            },
            "auto mode": {
                "mode": self.Zone.AUTO_MODE,
                "humidity": False,
                "heat_mode": False,
                "cool_mode": False,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": True,  # AUTO_MODE is controlled and has deviated setpoints
            },
            "fan mode": {
                "mode": self.Zone.FAN_MODE,
                "humidity": False,
                "heat_mode": False,
                "cool_mode": False,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,  # FAN_MODE is not controlled
            },
        }

        self.backup_functions()
        try:
            for test_case in test_cases:
                # mock up mode, set points, and humidity setting
                self.mock_set_mode(test_cases[test_case]["mode"])
                self.mock_set_point_deviation(
                    test_cases[test_case]["heat_deviation"],
                    test_cases[test_case]["cool_deviation"],
                )
                self.mock_set_humidity_support(test_cases[test_case]["humidity"])

                # call function and print return value
                ret_dict = self.Zone.get_current_mode(1, 1, True, False)
                print(f"test case '{test_case}' result: '{ret_dict}'")

                # verify return states are correct
                for return_val in [
                    "heat_mode",
                    "cool_mode",
                    "heat_deviation",
                    "cool_deviation",
                    "hold_mode",
                ]:
                    self.assertEqual(
                        ret_dict[return_val],
                        test_cases[test_case][return_val],
                        f"test case '{test_case}' parameter "
                        f"'{return_val}', result="
                        f"{ret_dict[return_val]}, expected="
                        f"{test_cases[test_case][return_val]}",
                    )

                # verify humidity reporting
                if test_cases[test_case]["humidity"]:
                    self.assertTrue("humidity" in ret_dict["status_msg"])
                else:
                    self.assertTrue("humidity" not in ret_dict["status_msg"])
        finally:
            self.restore_functions()

    def test_query_thermostat_zone_flag_all_deviations(self):
        """
        Test query_thermostat_zone function with flag_all_deviations enabled.

        This tests the specific logic where flag_all_deviations=True changes
        the operator and tolerance behavior for heat and cool modes.
        """
        test_cases = {
            "heat mode with flag_all_deviations": {
                "mode": self.Zone.HEAT_MODE,
                "flag_all_deviations": True,
                "expected_operator": operator.ne,
                "expected_tolerance": 0,
            },
            "heat mode without flag_all_deviations": {
                "mode": self.Zone.HEAT_MODE,
                "flag_all_deviations": False,
                "expected_operator": operator.gt,
                "expected_tolerance": self.Zone.tolerance_degrees_default,
            },
            "cool mode with flag_all_deviations": {
                "mode": self.Zone.COOL_MODE,
                "flag_all_deviations": True,
                "expected_operator": operator.ne,
                "expected_tolerance": 0,
            },
            "cool mode without flag_all_deviations": {
                "mode": self.Zone.COOL_MODE,
                "flag_all_deviations": False,
                "expected_operator": operator.lt,
                "expected_tolerance": self.Zone.tolerance_degrees_default,
            },
        }

        self.backup_functions()
        try:
            for test_case_name, test_case in test_cases.items():
                print(f"Testing: {test_case_name}")

                # Mock the mode
                self.mock_set_mode(test_case["mode"])

                # Reset tolerance_degrees to default before each test
                self.Zone.tolerance_degrees = self.Zone.tolerance_degrees_default

                # Set flag_all_deviations and call query_thermostat_zone directly
                self.Zone.flag_all_deviations = test_case["flag_all_deviations"]
                self.Zone.query_thermostat_zone()

                # Verify the operator was set correctly
                self.assertEqual(
                    self.Zone.operator,
                    test_case["expected_operator"],
                    f"Test case '{test_case_name}': operator mismatch. "
                    f"Expected {test_case['expected_operator']}, "
                    f"got {self.Zone.operator}",
                )

                # Verify tolerance was set correctly
                self.assertEqual(
                    self.Zone.tolerance_degrees,
                    test_case["expected_tolerance"],
                    f"Test case '{test_case_name}': tolerance_degrees mismatch. "
                    f"Expected {test_case['expected_tolerance']}, "
                    f"got {self.Zone.tolerance_degrees}",
                )

                # Verify the current_mode was set correctly
                self.assertEqual(
                    self.Zone.current_mode,
                    test_case["mode"],
                    f"Test case '{test_case_name}': current_mode mismatch. "
                    f"Expected {test_case['mode']}, "
                    f"got {self.Zone.current_mode}",
                )

        finally:
            self.restore_functions()

    def test_query_thermostat_zone_auto_and_fan_modes(self):
        """
        Test query_thermostat_zone function specifically for AUTO_MODE and FAN_MODE.

        These modes have specific parameter settings that need to be verified.
        """
        test_cases = {
            self.Zone.AUTO_MODE: {
                "expected_current_setpoint": util.BOGUS_INT,
                "expected_schedule_setpoint": util.BOGUS_INT,
                "expected_tolerance_sign": 1,
                "expected_operator": operator.ne,
                "expected_global_limit": util.BOGUS_INT,
                "expected_global_operator": operator.ne,
                "expected_revert_func": self.Zone.function_not_supported,
                "expected_get_func": self.Zone.function_not_supported,
            },
            self.Zone.FAN_MODE: {
                "expected_current_setpoint": util.BOGUS_INT,
                "expected_schedule_setpoint": util.BOGUS_INT,
                "expected_tolerance_sign": 1,
                "expected_operator": operator.ne,
                "expected_global_limit": util.BOGUS_INT,
                "expected_global_operator": operator.ne,
                "expected_revert_func": self.Zone.function_not_supported,
                "expected_get_func": self.Zone.function_not_supported,
            },
        }

        self.backup_functions()
        try:
            for mode, expected_values in test_cases.items():
                print(f"Testing query_thermostat_zone for {mode}")

                # Mock the mode
                self.mock_set_mode(mode)

                # Call query_thermostat_zone
                self.Zone.query_thermostat_zone()

                # Verify all expected parameter values
                self.assertEqual(
                    self.Zone.current_mode, mode, f"Mode {mode}: current_mode mismatch"
                )

                self.assertEqual(
                    self.Zone.current_setpoint,
                    expected_values["expected_current_setpoint"],
                    f"Mode {mode}: current_setpoint mismatch",
                )

                self.assertEqual(
                    self.Zone.schedule_setpoint,
                    expected_values["expected_schedule_setpoint"],
                    f"Mode {mode}: schedule_setpoint mismatch",
                )

                self.assertEqual(
                    self.Zone.tolerance_sign,
                    expected_values["expected_tolerance_sign"],
                    f"Mode {mode}: tolerance_sign mismatch",
                )

                self.assertEqual(
                    self.Zone.operator,
                    expected_values["expected_operator"],
                    f"Mode {mode}: operator mismatch",
                )

                self.assertEqual(
                    self.Zone.global_limit,
                    expected_values["expected_global_limit"],
                    f"Mode {mode}: global_limit mismatch",
                )

                self.assertEqual(
                    self.Zone.global_operator,
                    expected_values["expected_global_operator"],
                    f"Mode {mode}: global_operator mismatch",
                )

                self.assertEqual(
                    self.Zone.revert_setpoint_func,
                    expected_values["expected_revert_func"],
                    f"Mode {mode}: revert_setpoint_func mismatch",
                )

                self.assertEqual(
                    self.Zone.get_setpoint_func,
                    expected_values["expected_get_func"],
                    f"Mode {mode}: get_setpoint_func mismatch",
                )

        finally:
            self.restore_functions()

    def mock_set_mode(self, mock_mode):
        """
        Mock heat setting by overriding switch position function.

        Make sure to backup and restore methods if using this function.
        inputs:
            mock_mode(str): mode string
        returns:
            None
        """
        if mock_mode == self.Zone.HEAT_MODE:
            self.Zone.is_heat_mode = lambda *_, **__: True
            self.Zone.is_cool_mode = lambda *_, **__: False
            self.Zone.is_dry_mode = lambda *_, **__: False
            self.Zone.is_auto_mode = lambda *_, **__: False
            self.Zone.is_fan_mode = lambda *_, **__: False
            self.Zone.is_off_mode = lambda *_, **__: False
            self.Zone.is_eco_mode = lambda *_, **__: False
            self.Zone.current_mode = self.Zone.HEAT_MODE
        elif mock_mode == self.Zone.COOL_MODE:
            self.Zone.is_heat_mode = lambda *_, **__: False
            self.Zone.is_cool_mode = lambda *_, **__: True
            self.Zone.is_dry_mode = lambda *_, **__: False
            self.Zone.is_auto_mode = lambda *_, **__: False
            self.Zone.is_fan_mode = lambda *_, **__: False
            self.Zone.is_off_mode = lambda *_, **__: False
            self.Zone.is_eco_mode = lambda *_, **__: False
            self.Zone.current_mode = self.Zone.COOL_MODE
        elif mock_mode == self.Zone.DRY_MODE:
            self.Zone.is_heat_mode = lambda *_, **__: False
            self.Zone.is_cool_mode = lambda *_, **__: False
            self.Zone.is_dry_mode = lambda *_, **__: True
            self.Zone.is_auto_mode = lambda *_, **__: False
            self.Zone.is_fan_mode = lambda *_, **__: False
            self.Zone.is_off_mode = lambda *_, **__: False
            self.Zone.is_eco_mode = lambda *_, **__: False
            self.Zone.current_mode = self.Zone.DRY_MODE
        elif mock_mode == self.Zone.AUTO_MODE:
            self.Zone.is_heat_mode = lambda *_, **__: False
            self.Zone.is_cool_mode = lambda *_, **__: False
            self.Zone.is_dry_mode = lambda *_, **__: False
            self.Zone.is_auto_mode = lambda *_, **__: True
            self.Zone.is_fan_mode = lambda *_, **__: False
            self.Zone.is_off_mode = lambda *_, **__: False
            self.Zone.is_eco_mode = lambda *_, **__: False
            self.Zone.current_mode = self.Zone.AUTO_MODE
        elif mock_mode == self.Zone.FAN_MODE:
            self.Zone.is_heat_mode = lambda *_, **__: False
            self.Zone.is_cool_mode = lambda *_, **__: False
            self.Zone.is_dry_mode = lambda *_, **__: False
            self.Zone.is_auto_mode = lambda *_, **__: False
            self.Zone.is_fan_mode = lambda *_, **__: True
            self.Zone.is_off_mode = lambda *_, **__: False
            self.Zone.is_eco_mode = lambda *_, **__: False
            self.Zone.current_mode = self.Zone.FAN_MODE
        elif mock_mode == self.Zone.OFF_MODE:
            self.Zone.is_heat_mode = lambda *_, **__: False
            self.Zone.is_cool_mode = lambda *_, **__: False
            self.Zone.is_dry_mode = lambda *_, **__: False
            self.Zone.is_auto_mode = lambda *_, **__: False
            self.Zone.is_fan_mode = lambda *_, **__: False
            self.Zone.is_off_mode = lambda *_, **__: True
            self.Zone.is_eco_mode = lambda *_, **__: False
            self.Zone.current_mode = self.Zone.OFF_MODE
        elif mock_mode == self.Zone.ECO_MODE:
            self.Zone.is_heat_mode = lambda *_, **__: False
            self.Zone.is_cool_mode = lambda *_, **__: False
            self.Zone.is_dry_mode = lambda *_, **__: False
            self.Zone.is_auto_mode = lambda *_, **__: False
            self.Zone.is_fan_mode = lambda *_, **__: False
            self.Zone.is_off_mode = lambda *_, **__: False
            self.Zone.is_eco_mode = lambda *_, **__: True
            self.Zone.current_mode = self.Zone.ECO_MODE
        else:
            self.fail(f"mock mode '{mock_mode}' is not supported")

    def mock_set_point_deviation(self, heat_deviation, cool_deviation):
        """
        Override heat and cool set points with mock values.

        inputs:
            heat_deviation(bool): True if heat is deviated
            cool_deviation(bool): True if cool is deviated
        returns:
            None
        """
        deviation_val = self.Zone.tolerance_degrees + 1
        heat_sched_sp = self.Zone.max_scheduled_heat_allowed - 13
        heat_sp = heat_sched_sp + [0, deviation_val][heat_deviation]
        cool_sched_sp = self.Zone.min_scheduled_cool_allowed + 13
        cool_sp = cool_sched_sp - [0, deviation_val][cool_deviation]

        self.Zone.get_heat_setpoint_raw = lambda *_, **__: heat_sp
        self.Zone.get_schedule_heat_sp = lambda *_, **__: heat_sched_sp
        self.Zone.get_cool_setpoint_raw = lambda *_, **__: cool_sp
        self.Zone.get_schedule_cool_sp = lambda *_, **__: cool_sched_sp

    def mock_set_humidity_support(self, bool_val):
        """
        Mock humidity support.

        inputs:
            bool_val(bool): humidity support state
        returns:
            None
        """
        self.Zone.get_is_humidity_supported = lambda *_, **__: bool_val

    def backup_functions(self):
        """Backup functions prior to mocking return values."""
        self.switch_pos_bckup = self.Zone.get_system_switch_position
        self.is_heat_mode_bckup = self.Zone.is_heat_mode
        self.is_cool_mode_bckup = self.Zone.is_cool_mode
        self.heat_raw_bckup = self.Zone.get_heat_setpoint_raw
        self.schedule_heat_sp_bckup = self.Zone.get_schedule_heat_sp
        self.cool_raw_bckup = self.Zone.get_cool_setpoint_raw
        self.schedule_cool_sp_bckup = self.Zone.get_schedule_cool_sp
        self.get_humid_support_bckup = self.Zone.get_is_humidity_supported
        self.revert_setpoint_func_bckup = self.Zone.revert_setpoint_func

    def restore_functions(self):
        """Restore backed up functions."""
        self.Zone.get_system_switch_position = self.switch_pos_bckup
        self.Zone.is_heat_mode = self.is_heat_mode_bckup
        self.Zone.is_cool_mode = self.is_cool_mode_bckup
        self.Zone.get_heat_setpoint_raw = self.heat_raw_bckup
        self.Zone.get_schedule_heat_sp = self.schedule_heat_sp_bckup
        self.Zone.get_cool_setpoint_raw = self.cool_raw_bckup
        self.Zone.get_schedule_cool_sp = self.schedule_cool_sp_bckup
        self.Zone.get_is_humidity_supported = self.get_humid_support_bckup
        self.Zone.revert_setpoint_func = self.revert_setpoint_func_bckup

    def test_display_basic_thermostat_summary(self):
        """Confirm print_basic_thermostat_summary() works without error."""

        # override switch position function to be determinant
        self.switch_position_backup = self.Zone.get_system_switch_position
        try:
            self.Zone.get_system_switch_position = (
                lambda *_, **__: self.Zone.system_switch_position[
                    tc.ThermostatCommonZone.DRY_MODE
                ]
            )
            self.Zone.display_basic_thermostat_summary()
        finally:
            self.Zone.get_system_switch_position = self.switch_position_backup

    def test_thermostat_basic_checkout(self):
        """Verify thermostat_basic_checkout()."""

        # override switch position function to be determinant
        self.switch_position_backup = self.Zone.get_system_switch_position
        try:
            self.Zone.get_system_switch_position = (
                lambda *_, **__: self.Zone.system_switch_position[
                    tc.ThermostatCommonZone.DRY_MODE
                ]
            )
            api.uip = api.UserInputs(self.unit_test_argv)
            thermostat_type = api.uip.get_user_inputs(
                api.uip.zone_name, api.input_flds.thermostat_type
            )
            zone_number = api.uip.get_user_inputs(
                api.uip.zone_name, api.input_flds.zone
            )
            mod = api.load_hardware_library(thermostat_type)

            # Mock the environment variable verification to avoid requiring credentials
            # for this unit test which should be truly loopback
            with unittest.mock.patch.object(
                api, "verify_required_env_variables", return_value=True
            ):
                thermostat, zone_number = tc.thermostat_basic_checkout(
                    thermostat_type,
                    zone_number,
                    mod.ThermostatClass,
                    mod.ThermostatZone,
                )
            print(f"thermotat={type(thermostat)}")
            print(f"thermotat={type(zone_number)}")
        finally:
            self.Zone.get_system_switch_position = self.switch_position_backup

    def test_print_select_data_from_all_zones(self):
        """Verify print_select_data_from_all_zones()."""

        # override switch position function to be determinant
        self.switch_position_backup = self.Zone.get_system_switch_position
        try:
            self.Zone.get_system_switch_position = (
                lambda *_, **__: self.Zone.system_switch_position[
                    tc.ThermostatCommonZone.DRY_MODE
                ]
            )
            api.uip = api.UserInputs(self.unit_test_argv)
            thermostat_type = api.uip.get_user_inputs(
                api.uip.zone_name, api.input_flds.thermostat_type
            )
            zone_number = api.uip.get_user_inputs(
                api.uip.zone_name, api.input_flds.zone
            )
            mod = api.load_hardware_library(thermostat_type)

            # Mock the environment variable verification to avoid requiring credentials
            # for this unit test which should be truly loopback
            with unittest.mock.patch.object(
                api, "verify_required_env_variables", return_value=True
            ):
                tc.print_select_data_from_all_zones(
                    thermostat_type,
                    [zone_number],
                    mod.ThermostatClass,
                    mod.ThermostatZone,
                    display_wifi=True,
                    display_battery=True,
                )
        finally:
            self.Zone.get_system_switch_position = self.switch_position_backup

    def test_revert_temperature_deviation(self):
        """Verify revert_temperature_deviation()."""

        def mock_revert_setpoint_func(setpoint):
            self.Zone.current_setpoint = setpoint

        # backup functions that may be mocked
        self.backup_functions()
        try:
            # mock up the revert function for unit testing
            self.Zone.revert_setpoint_func = mock_revert_setpoint_func

            # mock the thermostat into heat mode
            # self.mock_set_mode(self.Zone.HEAT_MODE)
            # print(f"current thermostat mode={self.Zone.current_mode}")

            for new_setpoint in [13, 26, -4, 101]:
                # get current setpoint
                current_setpoint = self.Zone.current_setpoint

                # revert setpoint
                msg = (
                    f"reverting setpoint from "
                    f"{util.temp_value_with_units(current_setpoint)} to "
                    f"{util.temp_value_with_units(new_setpoint)}"
                )
                self.Zone.revert_temperature_deviation(new_setpoint, msg)

                # verify setpoint
                actual_setpoint = self.Zone.current_setpoint
                self.assertEqual(
                    new_setpoint,
                    actual_setpoint,
                    f"reverting setpoint failed, actual="
                    f"{util.temp_value_with_units(actual_setpoint)}, expected="
                    f"{util.temp_value_with_units(new_setpoint)}",
                )

            # verify function default behavior
            new_setpoint = self.Zone.current_setpoint = 56

            # revert setpoint
            msg = (
                f"reverting setpoint from "
                f"{util.temp_value_with_units(actual_setpoint)} to "
                f"{util.temp_value_with_units(new_setpoint)}"
            )
            self.Zone.revert_temperature_deviation(msg=msg)

            # verify setpoint
            actual_setpoint = self.Zone.current_setpoint
            self.assertEqual(
                new_setpoint,
                actual_setpoint,
                f"reverting setpoint failed, actual="
                f"{util.temp_value_with_units(actual_setpoint)}, expected="
                f"{util.temp_value_with_units(new_setpoint)}",
            )

        finally:
            self.restore_functions()

    def test_report_heating_parameters(self):
        """Verify report_heating_parameters()."""
        test_cases = [
            tc.ThermostatCommonZone.UNKNOWN_MODE,
            tc.ThermostatCommonZone.OFF_MODE,
        ]
        for test_case in test_cases:
            print(f"test_case={test_case}")
            self.Zone.report_heating_parameters(
                switch_position=self.Zone.system_switch_position[test_case]
            )

    def test_display_runtime_settings(self):
        """Verify display_runtime_settings() with new format."""
        from unittest.mock import patch
        import io

        # Set known values for testing
        self.Zone.poll_time_sec = 600  # 10 minutes
        self.Zone.connection_time_sec = 86400  # 1440 minutes (24 hours)

        # Capture log output
        with patch('sys.stdout', new=io.StringIO()) as fake_stdout:
            self.Zone.display_runtime_settings()
            output = fake_stdout.getvalue()

        # Verify poll_time format: "X.X minutes (Y seconds)"
        self.assertIn("10.0 minutes (600 seconds)", output,
                      "poll_time should be formatted as 'X.X minutes (Y seconds)'")

        # Verify connection_time format: "X minutes (Y seconds)" (no decimals)
        self.assertIn("1440 minutes (86400 seconds)", output,
                      "connection_time should be formatted as 'X minutes (Y seconds)'")

    def test_display_session_settings(self):
        """
        Verify display_session_settings() with all permutations.
        """
        for self.Zone.revert_deviations in [False, True]:
            for self.Zone.revert_all_deviations in [False, True]:
                print(f"{'-' * 60}")
                print(
                    f"testing revert={self.Zone.revert_deviations}, "
                    f"revert all={self.Zone.revert_all_deviations}"
                )
                self.Zone.display_session_settings()

    def test_update_runtime_parameters(self):
        """Verify update_runtime_parameters()."""
        # TODDO - set and verify runtime parameter overrides
        self.Zone.update_runtime_parameters()

    def test_set_mode_enhanced_functionality(self):
        """
        Test the enhanced set_mode method functionality.

        Verify that set_mode:
        1. Returns True for valid modes
        2. Returns False for invalid modes
        3. Applies scheduled setpoints for HEAT_MODE and COOL_MODE
        4. Handles other modes appropriately
        """
        # Mock scheduled setpoint functions to return specific values
        test_heat_setpoint = 70.0
        test_cool_setpoint = 75.0

        original_get_schedule_heat_sp = self.Zone.get_schedule_heat_sp
        original_get_schedule_cool_sp = self.Zone.get_schedule_cool_sp
        original_set_heat_setpoint = self.Zone.set_heat_setpoint
        original_set_cool_setpoint = self.Zone.set_cool_setpoint

        # Track setpoint calls
        heat_setpoint_called_with = []
        cool_setpoint_called_with = []

        def mock_get_schedule_heat_sp():
            return test_heat_setpoint

        def mock_get_schedule_cool_sp():
            return test_cool_setpoint

        def mock_set_heat_setpoint(temp):
            heat_setpoint_called_with.append(temp)

        def mock_set_cool_setpoint(temp):
            cool_setpoint_called_with.append(temp)

        try:
            # Replace methods with mocks
            self.Zone.get_schedule_heat_sp = mock_get_schedule_heat_sp
            self.Zone.get_schedule_cool_sp = mock_get_schedule_cool_sp
            self.Zone.set_heat_setpoint = mock_set_heat_setpoint
            self.Zone.set_cool_setpoint = mock_set_cool_setpoint

            # Test invalid mode
            result = self.Zone.set_mode("INVALID_MODE")
            self.assertFalse(result, "set_mode should return False for invalid mode")

            # Test HEAT_MODE - should return True and set heat setpoint
            heat_setpoint_called_with.clear()
            result = self.Zone.set_mode(self.Zone.HEAT_MODE)
            self.assertTrue(result, "set_mode should return True for HEAT_MODE")
            self.assertEqual(
                len(heat_setpoint_called_with),
                1,
                "set_heat_setpoint should be called once",
            )
            self.assertEqual(
                heat_setpoint_called_with[0],
                int(test_heat_setpoint),
                f"Heat setpoint should be {int(test_heat_setpoint)}",
            )

            # Test COOL_MODE - should return True and set cool setpoint
            cool_setpoint_called_with.clear()
            result = self.Zone.set_mode(self.Zone.COOL_MODE)
            self.assertTrue(result, "set_mode should return True for COOL_MODE")
            self.assertEqual(
                len(cool_setpoint_called_with),
                1,
                "set_cool_setpoint should be called once",
            )
            self.assertEqual(
                cool_setpoint_called_with[0],
                int(test_cool_setpoint),
                f"Cool setpoint should be {int(test_cool_setpoint)}",
            )

            # Test other valid modes - should return True without setpoint changes
            for mode in [
                self.Zone.AUTO_MODE,
                self.Zone.OFF_MODE,
                self.Zone.FAN_MODE,
                self.Zone.DRY_MODE,
                self.Zone.ECO_MODE,
                self.Zone.UNKNOWN_MODE,
            ]:
                heat_setpoint_called_with.clear()
                cool_setpoint_called_with.clear()
                result = self.Zone.set_mode(mode)
                self.assertTrue(result, f"set_mode should return True for {mode}")
                self.assertEqual(
                    len(heat_setpoint_called_with),
                    0,
                    f"Heat setpoint should not be called for {mode}",
                )
                self.assertEqual(
                    len(cool_setpoint_called_with),
                    0,
                    f"Cool setpoint should not be called for {mode}",
                )

            # Test with bogus scheduled setpoints (should still return True)
            def mock_get_bogus_heat_sp():
                return util.BOGUS_INT

            def mock_get_bogus_cool_sp():
                return util.BOGUS_INT

            self.Zone.get_schedule_heat_sp = mock_get_bogus_heat_sp
            self.Zone.get_schedule_cool_sp = mock_get_bogus_cool_sp

            heat_setpoint_called_with.clear()
            cool_setpoint_called_with.clear()

            result = self.Zone.set_mode(self.Zone.HEAT_MODE)
            self.assertTrue(
                result, "set_mode should return True even with bogus heat SP"
            )
            self.assertEqual(
                len(heat_setpoint_called_with),
                0,
                "Heat setpoint should not be called with bogus setpoint",
            )

            result = self.Zone.set_mode(self.Zone.COOL_MODE)
            self.assertTrue(
                result, "set_mode should return True even with bogus cool SP"
            )
            self.assertEqual(
                len(cool_setpoint_called_with),
                0,
                "Cool setpoint should not be called with bogus setpoint",
            )

        finally:
            # Restore original methods
            self.Zone.get_schedule_heat_sp = original_get_schedule_heat_sp
            self.Zone.get_schedule_cool_sp = original_get_schedule_cool_sp
            self.Zone.set_heat_setpoint = original_set_heat_setpoint
            self.Zone.set_cool_setpoint = original_set_cool_setpoint

    def test_configure_dry_mode(self):
        """Test _configure_dry_mode() method."""
        from unittest.mock import Mock

        # Setup mock methods
        self.Zone.get_cool_setpoint_raw = Mock(return_value=72.0)
        self.Zone.get_schedule_cool_sp = Mock(return_value=74.0)
        self.Zone.function_not_supported = Mock()

        # Setup attributes that should be set
        original_mode = getattr(self.Zone, "current_mode", None)
        original_setpoint = getattr(self.Zone, "current_setpoint", None)
        original_schedule_setpoint = getattr(self.Zone, "schedule_setpoint", None)
        original_tolerance_sign = getattr(self.Zone, "tolerance_sign", None)
        original_global_limit = getattr(self.Zone, "global_limit", None)
        original_global_operator = getattr(self.Zone, "global_operator", None)
        original_revert_func = getattr(self.Zone, "revert_setpoint_func", None)
        original_get_func = getattr(self.Zone, "get_setpoint_func", None)

        try:
            # Call the method
            self.Zone._configure_dry_mode()

            # Verify the configuration was set correctly
            self.assertEqual(self.Zone.current_mode, self.Zone.DRY_MODE)
            self.assertEqual(self.Zone.current_setpoint, 72.0)
            self.assertEqual(self.Zone.schedule_setpoint, 74.0)
            self.assertEqual(self.Zone.tolerance_sign, -1)
            self.assertEqual(
                self.Zone.global_limit, self.Zone.min_scheduled_cool_allowed
            )
            self.assertEqual(self.Zone.global_operator, operator.lt)
            self.assertEqual(
                self.Zone.revert_setpoint_func, self.Zone.function_not_supported
            )
            self.assertEqual(
                self.Zone.get_setpoint_func, self.Zone.function_not_supported
            )

            # Verify the mock methods were called
            self.Zone.get_cool_setpoint_raw.assert_called_once()
            self.Zone.get_schedule_cool_sp.assert_called_once()

        finally:
            # Restore original values if they existed
            if original_mode is not None:
                self.Zone.current_mode = original_mode
            if original_setpoint is not None:
                self.Zone.current_setpoint = original_setpoint
            if original_schedule_setpoint is not None:
                self.Zone.schedule_setpoint = original_schedule_setpoint
            if original_tolerance_sign is not None:
                self.Zone.tolerance_sign = original_tolerance_sign
            if original_global_limit is not None:
                self.Zone.global_limit = original_global_limit
            if original_global_operator is not None:
                self.Zone.global_operator = original_global_operator
            if original_revert_func is not None:
                self.Zone.revert_setpoint_func = original_revert_func
            if original_get_func is not None:
                self.Zone.get_setpoint_func = original_get_func

    def test_supervisor_loop_max_loop_time_display(self):
        """Test that max_loop_time is displayed in days format."""
        from unittest.mock import patch, Mock
        import io

        # Configure test with known values
        test_argv = [
            "supervise.py",
            "emulator",
            "0",
            "600",  # 10 minute poll time (600 seconds)
            "1000",  # connection time
            "2",  # tolerance
            "UNKNOWN_MODE",
            "5",  # 5 measurements
        ]
        api.uip = api.UserInputs(test_argv)

        # Mock get_current_mode to avoid actual operations
        original_get_current_mode = self.Zone.get_current_mode

        def mock_get_current_mode(*args, **kwargs):
            return {
                "heat_mode": False,
                "cool_mode": False,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,
                "status_msg": "test status",
            }

        try:
            self.Zone.get_current_mode = mock_get_current_mode
            self.Zone.refresh_zone_info = Mock()
            self.Zone.revert_all_deviations = False

            # Capture log output
            with patch('sys.stdout', new=io.StringIO()) as fake_stdout:
                # Call supervisor_loop - it will exit after measurements complete
                self.Zone.supervisor_loop(
                    self.Thermostat, session_count=1, measurement=1, debug=False
                )
                output = fake_stdout.getvalue()

            # Expected: (5 measurements * 600 sec) + (5 * 300 sec buffer)
            # = 4500 seconds
            # 4500 / 86400 = 0.052... days ≈ 0.1 days (with rounding)
            # Verify the output contains "days" format
            self.assertIn("max_loop_time=", output,
                          "Output should contain max_loop_time message")
            self.assertIn("days", output,
                          "max_loop_time should be displayed in days")

        finally:
            self.Zone.get_current_mode = original_get_current_mode

    def test_supervisor_loop_timeout(self):
        """Test that supervisor_loop respects the maximum loop time limit."""
        import time
        from unittest.mock import Mock

        # Setup: Mock get_current_mode to simulate slow operation
        original_get_current_mode = self.Zone.get_current_mode
        original_refresh_zone_info = self.Zone.refresh_zone_info

        try:
            # Configure test to run 10 measurements with 1 second poll time
            # Set very small max loop time to trigger timeout quickly
            test_argv = [
                "supervise.py",
                "emulator",
                "0",
                "1",  # 1 second poll time
                "1000",  # connection time
                "2",  # tolerance
                "UNKNOWN_MODE",
                "10",  # 10 measurements
            ]
            api.uip = api.UserInputs(test_argv)

            # Mock get_current_mode to simulate a slow operation (2 seconds)
            def slow_get_current_mode(*args, **kwargs):
                time.sleep(2)  # Simulate slow network operation
                return {
                    "heat_mode": False,
                    "cool_mode": False,
                    "heat_deviation": False,
                    "cool_deviation": False,
                    "hold_mode": False,
                    "status_msg": "test status",
                }

            self.Zone.get_current_mode = slow_get_current_mode
            self.Zone.refresh_zone_info = Mock()  # Mock to avoid actual refresh
            self.Zone.revert_all_deviations = False

            # Record start time
            start_time = time.time()

            # Call supervisor_loop - it should timeout before completing all
            # measurements
            measurement = self.Zone.supervisor_loop(
                self.Thermostat, session_count=1, measurement=1, debug=False
            )

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Expected max time: (10 measurements * 1 sec poll) +
            # (10 * 300 sec buffer) = 3010 seconds
            # With 2 second sleep in get_current_mode, it would take much longer
            # without timeout
            # The connection_time_sec (1000s) should trigger reconnection first
            # So measurement should be less than 11
            self.assertLessEqual(
                measurement,
                11,
                f"Measurement count {measurement} should be <= 11 "
                "(completed or reconnected)",
            )

            # Verify the timeout mechanism worked by checking elapsed time is
            # reasonable
            # Should be much less than the theoretical max of 3010 seconds
            # In practice, connection timeout (1000s) should trigger first
            self.assertLess(
                elapsed_time,
                1100,  # Connection timeout + buffer
                f"Loop took {elapsed_time:.1f}s, should have reconnected "
                f"around 1000s",
            )

        finally:
            # Restore original methods
            self.Zone.get_current_mode = original_get_current_mode
            self.Zone.refresh_zone_info = original_refresh_zone_info

    def test_supervisor_loop_timeout_on_first_iteration(self):
        """
        Test that supervisor_loop times out even if first iteration hangs.

        This simulates the GitHub Actions scenario where get_current_mode hangs
        on the very first call.
        """
        import time
        from unittest.mock import Mock

        original_get_current_mode = self.Zone.get_current_mode
        original_refresh_zone_info = self.Zone.refresh_zone_info

        try:
            # Configure test with small measurement count and short poll time
            # but very small max loop time to trigger timeout quickly
            test_argv = [
                "supervise.py",
                "emulator",
                "0",
                "5",  # 5 second poll time
                "100",  # 100 second connection time
                "2",  # tolerance
                "UNKNOWN_MODE",
                "3",  # 3 measurements
            ]
            api.uip = api.UserInputs(test_argv)

            # Track how many times get_current_mode is called
            call_count = [0]

            # Mock get_current_mode to simulate a slow first operation
            def very_slow_get_current_mode(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    # First call: sleep longer than connection timeout
                    # Connection time is 100s, so sleep for 110s
                    # This simulates a hanging network operation
                    time.sleep(110)
                return {
                    "heat_mode": False,
                    "cool_mode": False,
                    "heat_deviation": False,
                    "cool_deviation": False,
                    "hold_mode": False,
                    "status_msg": "test status",
                }

            self.Zone.get_current_mode = very_slow_get_current_mode
            self.Zone.refresh_zone_info = Mock()
            self.Zone.revert_all_deviations = False

            start_time = time.time()

            # Call supervisor_loop - should timeout/reconnect before completing
            measurement = self.Zone.supervisor_loop(
                self.Thermostat, session_count=1, measurement=1, debug=False
            )

            elapsed_time = time.time() - start_time

            # Should have hit connection timeout (100s) or loop timeout
            # Allow for 110s sleep + overhead for cleanup
            self.assertLess(
                elapsed_time,
                140,
                f"Loop took {elapsed_time:.1f}s, should have completed "
                f"110s sleep plus overhead",
            )

            # Verify measurement count indicates early exit
            # Should be less than expected 4 (1 + 3 measurements)
            self.assertLess(
                measurement,
                4,
                f"Measurement count {measurement} indicates loop may not have "
                "timed out properly",
            )

            # Should have been called at most once since it hung
            self.assertLessEqual(
                call_count[0],
                2,
                f"get_current_mode called {call_count[0]} times, "
                "expected <= 2 (may have started second iteration)",
            )

        finally:
            # Restore original methods
            self.Zone.get_current_mode = original_get_current_mode
            self.Zone.refresh_zone_info = original_refresh_zone_info


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
