"""
Tests for thermostat_common.py
"""
# built-in imports
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
                "args": [1, 1],
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

    # def test_GetCurrentMode(self):
    #     utc.print_test_name()
    #     self.Thermostat.get_current_mode(session_count=1, poll_count=1)
    #
    # def test_GetDisplayTemp(self):
    #     utc.print_test_name()
    #     return_val = self.Thermostat.get_display_temp()
    #     expected_type = float
    #     self.assertTrue(isinstance(return_val, expected_type),
    #                     "expected type=%s, actual type=%s" %
    #                     (expected_type, type(return_val)))
    #
    # def test_GetDisplayHumidity(self):
    #     utc.print_test_name()
    #     return_val = self.Thermostat.get_display_humidity()
    #     expected_type = float
    #     self.assertTrue(isinstance(return_val, expected_type),
    #                     "expected type=%s, actual type=%s" %
    #                     (expected_type, type(return_val)))
    #
    # def test_GetIsHumiditySupported(self):
    #     utc.print_test_name()
    #     return_val = self.Thermostat.get_is_humidity_supported()
    #     expected_type = bool
    #     self.assertTrue(isinstance(return_val, expected_type),
    #                     "expected type=%s, actual type=%s" %
    #                     (expected_type, type(return_val)))
    #
    # def test_GetSystemSwitchPosition(self):
    #     utc.print_test_name()
    #     return_val = self.Thermostat.get_system_switch_position()
    #     expected_type = int
    #     self.assertTrue(isinstance(return_val, expected_type),
    #                     "expected type=%s, actual type=%s" %
    #                     (expected_type, type(return_val)))
    #
    # def test_GetHeatSetpointRaw(self):
    #     utc.print_test_name()
    #     return_val = self.Thermostat.get_heat_setpoint_raw()
    #     self.assertTrue(isinstance(return_val, int))


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()
