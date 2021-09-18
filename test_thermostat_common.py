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

        self.Thermostat = tc.ThermostatCommonZone()
        self.Thermostat.update_runtime_parameters(api.user_inputs)

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
                "key": self.Thermostat.get_current_mode,
                "args": [1, 1],  # flag_all_deviations==False
                "return_type": dict},
            "Get_current_mode": {  # Capitalize for unique key
                "key": self.Thermostat.get_current_mode,
                "args": [1, 1, True, True],  # flag_all_deviations==True
                "return_type": dict},
            "get_display_temp": {
                "key": self.Thermostat.get_display_temp,
                "args": None,
                "return_type": float},
            "get_display_humidity": {
                "key": self.Thermostat.get_display_humidity,
                "args": None,
                "return_type": float},
            "get_is_humidity_supported": {
                "key": self.Thermostat.get_is_humidity_supported,
                "args": None,
                "return_type": bool},
            "get_system_switch_position": {
                "key": self.Thermostat.get_system_switch_position,
                "args": None,
                "return_type": int},
            "get_heat_setpoint_raw": {
                "key": self.Thermostat.get_heat_setpoint_raw,
                "args": None,
                "return_type": int},
            "get_schedule_heat_sp": {
                "key": self.Thermostat.get_schedule_heat_sp,
                "args": None,
                "return_type": int},
            "get_cool_setpoint_raw": {
                "key": self.Thermostat.get_cool_setpoint_raw,
                "args": None,
                "return_type": int},
            "get_schedule_cool_sp": {
                "key": self.Thermostat.get_schedule_cool_sp,
                "args": None,
                "return_type": int},
            "get_is_invacation_hold_mode": {
                "key": self.Thermostat.get_is_invacation_hold_mode,
                "args": None,
                "return_type": bool},
            "get_temporary_hold_until_time": {
                "key": self.Thermostat.get_temporary_hold_until_time,
                "args": None,
                "return_type": int},
            "refresh_zone_info": {
                "key": self.Thermostat.refresh_zone_info,
                "args": None,
                "return_type": type(None)},
            "report_heating_parameters": {
                "key": self.Thermostat.report_heating_parameters,
                "args": None,
                "return_type": type(None)},
            "update_runtime_parameters": {
                "key": self.Thermostat.update_runtime_parameters,
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
        for test_case in [1, 1.0, "1", True]:
            if isinstance(test_case, (int, float)):
                expected_val = test_case
                actual_val = self.Thermostat.validate_numeric(test_case,
                                                              "test_case")
                self.assertEqual(
                    expected_val, actual_val,
                    "expected return value=%s, type(%s), actual=%s,"
                    "type(%s)" % (expected_val, type(expected_val), actual_val,
                                  type(actual_val)))
            else:
                self.assertRaises(self.Thermostat.validate_numeric(
                    test_case, "test_case"), TypeError)

    def test_WarnIfOutsideGlobalLimit(self):
        """Test warn_if_outside_global_limit() function."""
        self.assertTrue(self.Thermostat.warn_if_outside_global_limit(
            2, 1, operator.gt, "heat"),
            "function result should have been True")
        self.assertFalse(self.Thermostat.warn_if_outside_global_limit(
            2, 3, operator.gt, "heat"),
            "function result should have been False")
        self.assertTrue(self.Thermostat.warn_if_outside_global_limit(
            2, 3, operator.lt, "cool"),
            "function result should have been True")
        self.assertFalse(self.Thermostat.warn_if_outside_global_limit(
            2, 1, operator.lt, "cool"),
            "function result should have been False")

    def test_GetCurrentMode(self):
        """
        Verify get_current_mode runs in all permutations.

        test cases:
        heat mode and following schedule
        heat mode and deviation
        cool mode and following schedule
        cool mode and cool deviation
        """
        utc.print_test_name()
        return  # test is not ready
        self.backup_functions()
        try:
            # heat mode and following schedule
            self.Thermostat.get_system_switch_position = \
                (lambda *_, **__:
                 self.Thermostat.system_switch_position[
                     self.Thermostat.HEAT_MODE])
            ret_dict = self.Thermostat.get_current_mode(1, 1, True, False)

            # heat mode and deviation
            self.Thermostat.get_system_switch_position = \
                (lambda *_, **__:
                 self.Thermostat.system_switch_position[
                     self.Thermostat.HEAT_MODE])
            ret_dict = self.Thermostat.get_current_mode(1, 1, True, False)
            # cool mode and following schedule
            # self.Thermostat.get_system_switch_position() = \
            #    self.Thermostat.system_switch_position[self.COOL_MODE]
            ret_dict = self.Thermostat.get_current_mode(1, 1, True, False)
            print("%s" % ret_dict)
            # cool mode and cool deviation
        finally:
            self.restore_functions()

    def backup_functions(self):
        """Backup functions prior to mocking return values."""
        self.switch_pos_bckup = self.Thermostat.get_system_switch_position
        self.heat_raw_bckup = self.Thermostat.get_heat_setpoint_raw
        self.schedule_heat_sp_bckup = self.Thermostat.get_schedule_heat_sp

    def restore_functions(self):
        """Restore backed up functions."""
        self.Thermostat.get_system_switch_position = self.switch_pos_bckup
        self.Thermostat.get_heat_setpoint_raw = self.heat_raw_bckup
        self.Thermostat.get_schedule_heat_sp = self.schedule_heat_sp_bckup


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()
