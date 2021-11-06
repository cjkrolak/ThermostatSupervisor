"""
Tests for thermostat_common.py
"""
# built-in imports
import operator
import unittest

# local imports
import thermostat_api as api
import thermostat_common as tc
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
        self.user_inputs_backup = api.user_inputs
        api.user_inputs = {
            "thermostat_type": self.tstat,
            "zone": 1,
            "poll_time_sec": 55,
            "connection_time_sec": 155,
            }

        self.Zone = tc.ThermostatCommonZone()
        self.Zone.update_runtime_parameters(api.user_inputs)

    def tearDown(self):
        del api.thermostats[self.tstat]
        api.user_inputs = self.user_inputs_backup

    def test_CheckReturnTypes(self):
        """
        Verify return type of each function is as expected.
        """
        utc.print_test_name()
        func_dict = {
            "get_current_mode": {
                "key": self.Zone.get_current_mode,
                "args": [1, 1],  # flag_all_deviations==False
                "return_type": dict},
            "Get_current_mode": {  # Capitalize for unique key
                "key": self.Zone.get_current_mode,
                "args": [1, 1, True, True],  # flag_all_deviations==True
                "return_type": dict},
            "get_display_temp": {
                "key": self.Zone.get_display_temp,
                "args": None,
                "return_type": float},
            "get_display_humidity": {
                "key": self.Zone.get_display_humidity,
                "args": None,
                "return_type": float},
            "get_is_humidity_supported": {
                "key": self.Zone.get_is_humidity_supported,
                "args": None,
                "return_type": bool},
            "get_system_switch_position": {
                "key": self.Zone.get_system_switch_position,
                "args": None,
                "return_type": int},
            "get_heat_setpoint_raw": {
                "key": self.Zone.get_heat_setpoint_raw,
                "args": None,
                "return_type": int},
            "get_schedule_heat_sp": {
                "key": self.Zone.get_schedule_heat_sp,
                "args": None,
                "return_type": int},
            "get_cool_setpoint_raw": {
                "key": self.Zone.get_cool_setpoint_raw,
                "args": None,
                "return_type": int},
            "get_schedule_cool_sp": {
                "key": self.Zone.get_schedule_cool_sp,
                "args": None,
                "return_type": int},
            "get_is_invacation_hold_mode": {
                "key": self.Zone.get_is_invacation_hold_mode,
                "args": None,
                "return_type": bool},
            "get_temporary_hold_until_time": {
                "key": self.Zone.get_temporary_hold_until_time,
                "args": None,
                "return_type": int},
            "refresh_zone_info": {
                "key": self.Zone.refresh_zone_info,
                "args": None,
                "return_type": type(None)},
            "report_heating_parameters": {
                "key": self.Zone.report_heating_parameters,
                "args": None,
                "return_type": type(None)},
            "update_runtime_parameters": {
                "key": self.Zone.update_runtime_parameters,
                "args": [{"zone": 1}],
                "return_type": type(None)},
            }
        for k, v in func_dict.items():
            print("key=%s" % k)
            print("v=%s" % v)
            expected_type = v["return_type"]
            print("expected type=%s" % expected_type)
            if v["args"] is not None:
                return_val = v["key"](*v["args"])
            else:
                return_val = v["key"]()
            self.assertTrue(isinstance(return_val, expected_type),
                            "func=%s, expected type=%s, actual type=%s" %
                            (k, expected_type, type(return_val)))

    def test_ValidateNumeric(self):
        """Test validate_numeric() function."""
        utc.print_test_name()
        for test_case in [1, 1.0, "1", True]:
            print("test case=%s" % type(test_case))
            if isinstance(test_case, (int, float)):
                expected_val = test_case
                actual_val = self.Zone.validate_numeric(test_case,
                                                        "test_case")
                self.assertEqual(
                    expected_val, actual_val,
                    "expected return value=%s, type(%s), actual=%s,"
                    "type(%s)" % (expected_val, type(expected_val), actual_val,
                                  type(actual_val)))
            else:
                with self.assertRaises(TypeError):
                    self.Zone.validate_numeric(
                        test_case, "test_case")

    def test_WarnIfOutsideGlobalLimit(self):
        """Test warn_if_outside_global_limit() function."""
        utc.print_test_name()
        self.assertTrue(self.Zone.warn_if_outside_global_limit(
            2, 1, operator.gt, "heat"),
            "function result should have been True")
        self.assertFalse(self.Zone.warn_if_outside_global_limit(
            2, 3, operator.gt, "heat"),
            "function result should have been False")
        self.assertTrue(self.Zone.warn_if_outside_global_limit(
            2, 3, operator.lt, "cool"),
            "function result should have been True")
        self.assertFalse(self.Zone.warn_if_outside_global_limit(
            2, 1, operator.lt, "cool"),
            "function result should have been False")

    def test_GetCurrentMode(self):
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
                "mode": "heat_mode",
                "humidity": False,
                "heat_mode": True,
                "cool_mode": False,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,
                },
            "heat mode and following schedule and humidity": {
                "mode": "heat_mode",
                "humidity": True,
                "heat_mode": True,
                "cool_mode": False,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,
                },
            "heat mode and deviation": {
                "mode": "heat_mode",
                "humidity": False,
                "heat_mode": True,
                "cool_mode": False,
                "heat_deviation": True,
                "cool_deviation": False,
                "hold_mode": True,
                },
            "heat mode and deviation and humidity": {
                "mode": "heat_mode",
                "humidity": True,
                "heat_mode": True,
                "cool_mode": False,
                "heat_deviation": True,
                "cool_deviation": False,
                "hold_mode": True,
                },
            "cool mode and following schedule": {
                "mode": "cool_mode",
                "humidity": False,
                "heat_mode": False,
                "cool_mode": True,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,
                },
            "cool mode and following schedule and humidity": {
                "mode": "cool_mode",
                "humidity": True,
                "heat_mode": False,
                "cool_mode": True,
                "heat_deviation": False,
                "cool_deviation": False,
                "hold_mode": False,
                },
            "cool mode and deviation": {
                "mode": "cool_mode",
                "humidity": False,
                "heat_mode": False,
                "cool_mode": True,
                "heat_deviation": False,
                "cool_deviation": True,
                "hold_mode": True,
                },
            "cool mode and deviation and humidity": {
                "mode": "cool_mode",
                "humidity": True,
                "heat_mode": False,
                "cool_mode": True,
                "heat_deviation": False,
                "cool_deviation": True,
                "hold_mode": True,
                },
            }
        utc.print_test_name()
        # return  # test is not ready
        self.backup_functions()
        try:
            for test_case in test_cases:
                # mock up mode, set points, and humidity setting
                self.mock_set_mode(test_cases[test_case]["mode"])
                self.mock_set_points(test_cases[test_case]["heat_deviation"],
                                     test_cases[test_case]["cool_deviation"])
                self.mock_set_humidity_support(
                    test_cases[test_case]["humidity"])

                # call function and print return value
                ret_dict = self.Zone.get_current_mode(1, 1, True, False)
                print("test case '%s' result: '%s'" % (test_case, ret_dict))

                # verify return states are correct
                for return_val in ["heat_mode", "cool_mode", "heat_deviation",
                                   "cool_deviation", "hold_mode"]:
                    self.assertEqual(ret_dict[return_val],
                                     test_cases[test_case][return_val],
                                     "test case '%s' parameter '%s', "
                                     "result=%s, expected=%s" %
                                     (test_case, return_val,
                                      ret_dict[return_val],
                                      test_cases[test_case][return_val]))

                # verify humidity reporting
                if test_cases[test_case]["humidity"]:
                    self.assertTrue("humidity" in ret_dict["status_msg"])
                else:
                    self.assertTrue("humidity" not in ret_dict["status_msg"])
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
        self.Zone.is_heat_mode = \
            (lambda *_, **__: mock_mode == "heat_mode")
        self.Zone.is_cool_mode = \
            (lambda *_, **__: mock_mode == "cool_mode")

    def mock_set_points(self, heat_deviation, cool_deviation):
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

        self.Zone.get_heat_setpoint_raw = (lambda *_, **__: heat_sp)
        self.Zone.get_schedule_heat_sp = (lambda *_, **__: heat_sched_sp)
        self.Zone.get_cool_setpoint_raw = (lambda *_, **__: cool_sp)
        self.Zone.get_schedule_cool_sp = (lambda *_, **__: cool_sched_sp)

    def mock_set_humidity_support(self, bool_val):
        """
        Mock humidity support.

        inputs:
            bool_val(bool): humidity support state
        returns:
            None
        """
        self.Zone.get_is_humidity_supported = \
            (lambda *_, **__: bool_val)

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


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()
