"""
Tests for thermostat_common.py
"""
# built-in imports
import operator
import pprint
import random
import unittest

# local imports
import thermostat_api as api
import thermostat_common as tc
import unit_test_common as utc
import utilities as util


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
        self.print_test_name()
        self.setUp_mock_thermostat_zone()

    def tearDown(self):
        self.tearDown_mock_thermostat_zone()
        self.print_test_result()

    def test_PrintAllThermostatMetaData(self):
        """
        Verify print_all_thermostat_metadata() runs without error.
        """
        self.Thermostat.print_all_thermostat_metadata()

    def test_SetMode(self):
        """
        Verify set_mode() runs without error.
        """
        result = self.Zone.set_mode("bogus_mode")
        self.assertFalse(result, "Zone.set_mode() should have returned False")

    def test_StoreCurrentMode(self):
        """
        Verify store_current_mode() runs without error.
        """
        def dummy_true(): return 1  # functions return ints

        test_cases = [["is_heat_mode", self.Zone.HEAT_MODE],
                      ["is_cool_mode", self.Zone.COOL_MODE],
                      ["is_dry_mode", self.Zone.DRY_MODE],
                      ["is_auto_mode", self.Zone.AUTO_MODE],
                      ["is_fan_mode", self.Zone.FAN_MODE],
                      ["is_off_mode", self.Zone.OFF_MODE]]

        print("thermostat_type=%s" % self.Zone.thermostat_type)

        for test_case in test_cases:
            print("testing %s" % test_case[0])
            try:
                # mock up the is_X_mode() functions
                if test_case[0]:
                    backup_func = getattr(self.Zone, test_case[0])
                    setattr(self.Zone, test_case[0], dummy_true)
                print("current mode(pre)=%s" % self.Zone.current_mode)

                # store the current mode and check cache
                self.Zone.store_current_mode()
                print("current mode(post)=%s" % self.Zone.current_mode)
                self.assertEqual(test_case[1], self.Zone.current_mode,
                                 "Zone.set_current_mode() failed to "
                                 "cache mode=%s" % test_case[1])

                # confirm verify_current_mode()
                none_act = self.Zone.verify_current_mode(None)
                self.assertTrue(none_act,
                                "verify_current_mode(None) failed "
                                "to return True")
                curr_act = self.Zone.verify_current_mode(test_case[1])
                self.assertTrue(curr_act,
                                "verify_current_mode() doesn't match "
                                "current test mode")
                dummy_act = self.Zone.verify_current_mode("dummy_mode")
                self.assertFalse(dummy_act,
                                 "verify_current_mode('dummy_mode') returned "
                                 "True, should have returned False")
            finally:
                # restore mocked function
                if test_case[0]:
                    setattr(self.Zone, test_case[0], backup_func)

    def test_CheckReturnTypes(self):
        """
        Verify return type of each function is as expected.
        """
        func_dict = {
            "is_temp_deviated_from_schedule": {
                "key": self.Zone.is_temp_deviated_from_schedule,
                "args": None,
                "return_type": bool},
            "get_current_mode": {
                "key": self.Zone.get_current_mode,
                "args": [1, 1],  # flag_all_deviations==False
                "return_type": dict},
            "Get_current_mode": {  # Capitalize for unique key
                "key": self.Zone.get_current_mode,
                "args": [1, 1, True, True],  # flag_all_deviations==True
                "return_type": dict},
            "set_mode": {
                "key": self.Zone.set_mode,
                "args": ["bogus"],
                "return_type": bool},
            "store_current_mode": {
                "key": self.Zone.store_current_mode,
                "args": None,
                "return_type": type(None)},
            "validate_numeric": {
                "key": self.Zone.validate_numeric,
                "args": [0, "bogus"],
                "return_type": int},
            "warn_if_outside_global_limit": {
                "key": self.Zone.warn_if_outside_global_limit,
                "args": [0, 0, operator.gt, "bogus"],
                "return_type": bool},
            "is_heat_mode": {
                "key": self.Zone.is_heat_mode,
                "args": None,
                "return_type": int},
            "is_cool_mode": {
                "key": self.Zone.is_cool_mode,
                "args": None,
                "return_type": int},
            "is_dry_mode": {
                "key": self.Zone.is_dry_mode,
                "args": None,
                "return_type": int},
            "is_auto_mode": {
                "key": self.Zone.is_auto_mode,
                "args": None,
                "return_type": int},
            "is_fan_mode": {
                "key": self.Zone.is_fan_mode,
                "args": None,
                "return_type": int},
            "is_off_mode": {
                "key": self.Zone.is_off_mode,
                "args": None,
                "return_type": int},
            "is_heating": {
                "key": self.Zone.is_heating,
                "args": None,
                "return_type": int},
            "is_cooling": {
                "key": self.Zone.is_cooling,
                "args": None,
                "return_type": int},
            "is_drying": {
                "key": self.Zone.is_drying,
                "args": None,
                "return_type": int},
            "is_auto": {
                "key": self.Zone.is_auto,
                "args": None,
                "return_type": int},
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
            "get_schedule_program_heat": {
                "key": self.Zone.get_schedule_program_heat,
                "args": None,
                "return_type": dict},
            "get_schedule_program_cool": {
                "key": self.Zone.get_schedule_program_cool,
                "args": None,
                "return_type": dict},
            "get_vacation_hold_until_time": {
                "key": self.Zone.get_vacation_hold_until_time,
                "args": None,
                "return_type": int},
            "set_heat_setpoint": {
                "key": self.Zone.set_heat_setpoint,
                "args": [0],
                "return_type": type(None)},
            "set_cool_setpoint": {
                "key": self.Zone.set_cool_setpoint,
                "args": [0],
                "return_type": type(None)},
            "revert_temperature_deviation": {
                "key": self.Zone.revert_temperature_deviation,
                "args": [0, "this is a dummy msg from unit test"],
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
                    print("attempting to input bad parameter type, "
                          "expect exception...")
                    self.Zone.validate_numeric(
                        test_case, "test_case")

    def test_WarnIfOutsideGlobalLimit(self):
        """Test warn_if_outside_global_limit() function."""
        self.assertTrue(self.Zone.warn_if_outside_global_limit(
            self.Zone.max_scheduled_heat_allowed + 1,
            self.Zone.max_scheduled_heat_allowed, operator.gt, "heat"),
            "function result should have been True")
        self.assertFalse(self.Zone.warn_if_outside_global_limit(
            self.Zone.max_scheduled_heat_allowed - 1,
            self.Zone.max_scheduled_heat_allowed, operator.gt, "heat"),
            "function result should have been False")
        self.assertTrue(self.Zone.warn_if_outside_global_limit(
            self.Zone.min_scheduled_cool_allowed - 1,
            self.Zone.min_scheduled_cool_allowed, operator.lt, "cool"),
            "function result should have been True")
        self.assertFalse(self.Zone.warn_if_outside_global_limit(
            self.Zone.min_scheduled_cool_allowed + 1,
            self.Zone.min_scheduled_cool_allowed, operator.lt, "cool"),
            "function result should have been False")

    def test_RevertThermostatMode(self):
        """
        Test the revert_thermostat_mode() function.
        """
        test_cases = [self.Zone.HEAT_MODE, self.Zone.COOL_MODE,
                      self.Zone.DRY_MODE, self.Zone.AUTO_MODE,
                      self.Zone.FAN_MODE, self.Zone.OFF_MODE]
        for test_case in random.choices(test_cases, k=20):
            if ((self.Zone.current_mode in self.Zone.heat_modes and
                 test_case in self.Zone.cool_modes)
                or (self.Zone.current_mode in self.Zone.cool_modes and
                    test_case in self.Zone.heat_modes)):
                expected_mode = self.Zone.OFF_MODE
            else:
                expected_mode = test_case
            print("reverting to '%s' mode, expected mode=%s" %
                  (test_case, expected_mode))
            new_mode = self.Zone.revert_thermostat_mode(test_case)
            self.assertEqual(new_mode, expected_mode,
                             "reverting to %s mode failed, "
                             "new mode is '%s', expected '%s'" %
                             (test_case, new_mode, expected_mode))
            self.Zone.current_mode = test_case

    def test_MeasureThermostatResponseTime(self):
        """
        Test the measure_thermostat_response_time() function.
        """
        # measure thermostat response time
        measurements = 3
        print("Thermostat response times for %s measurements..." %
              measurements)
        meas_data = self.Zone.measure_thermostat_response_time(measurements)
        ppp = pprint.PrettyPrinter(indent=4)
        ppp.pprint(meas_data)
        self.assertTrue(isinstance(meas_data, dict),
                        "return data is type(%s), expected a dict" %
                        type(meas_data))
        self.assertEqual(meas_data["measurements"], measurements,
                         "number of measurements in return data(%s) doesn't "
                         "match number of masurements requested(%s)" %
                         (meas_data["measurements"], measurements))

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
            }

        self.backup_functions()
        try:
            for test_case in test_cases:
                # mock up mode, set points, and humidity setting
                self.mock_set_mode(test_cases[test_case]["mode"])
                self.mock_set_point_deviation(
                    test_cases[test_case]["heat_deviation"],
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
        if mock_mode == self.Zone.HEAT_MODE:
            self.Zone.is_heat_mode = \
                (lambda *_, **__: True)
            self.Zone.is_cool_mode = \
                (lambda *_, **__: False)
            self.Zone.is_dry_mode = \
                (lambda *_, **__: False)
            self.Zone.is_auto_mode = \
                (lambda *_, **__: False)
            self.Zone.is_fan_mode = \
                (lambda *_, **__: False)
            self.Zone.is_off_mode = \
                (lambda *_, **__: False)
            self.Zone.current_mode = self.Zone.HEAT_MODE
        elif mock_mode == self.Zone.COOL_MODE:
            self.Zone.is_heat_mode = \
                (lambda *_, **__: False)
            self.Zone.is_cool_mode = \
                (lambda *_, **__: True)
            self.Zone.is_dry_mode = \
                (lambda *_, **__: False)
            self.Zone.is_auto_mode = \
                (lambda *_, **__: False)
            self.Zone.is_fan_mode = \
                (lambda *_, **__: False)
            self.Zone.is_off_mode = \
                (lambda *_, **__: False)
            self.Zone.current_mode = self.Zone.COOL_MODE
        elif mock_mode == self.Zone.DRY_MODE:
            self.Zone.is_heat_mode = \
                (lambda *_, **__: False)
            self.Zone.is_cool_mode = \
                (lambda *_, **__: False)
            self.Zone.is_dry_mode = \
                (lambda *_, **__: True)
            self.Zone.is_auto_mode = \
                (lambda *_, **__: False)
            self.Zone.is_fan_mode = \
                (lambda *_, **__: False)
            self.Zone.is_off_mode = \
                (lambda *_, **__: False)
            self.Zone.current_mode = self.Zone.DRY_MODE
        elif mock_mode == self.Zone.AUTO_MODE:
            self.Zone.is_heat_mode = \
                (lambda *_, **__: False)
            self.Zone.is_cool_mode = \
                (lambda *_, **__: False)
            self.Zone.is_dry_mode = \
                (lambda *_, **__: False)
            self.Zone.is_auto_mode = \
                (lambda *_, **__: True)
            self.Zone.is_fan_mode = \
                (lambda *_, **__: False)
            self.Zone.is_off_mode = \
                (lambda *_, **__: False)
            self.Zone.current_mode = self.Zone.AUTO_MODE
        elif mock_mode == self.Zone.FAN_MODE:
            self.Zone.is_heat_mode = \
                (lambda *_, **__: False)
            self.Zone.is_cool_mode = \
                (lambda *_, **__: False)
            self.Zone.is_dry_mode = \
                (lambda *_, **__: False)
            self.Zone.is_auto_mode = \
                (lambda *_, **__: False)
            self.Zone.is_fan_mode = \
                (lambda *_, **__: True)
            self.Zone.is_off_mode = \
                (lambda *_, **__: False)
            self.Zone.current_mode = self.Zone.FAN_MODE
        elif mock_mode == self.Zone.OFF_MODE:
            self.Zone.is_heat_mode = \
                (lambda *_, **__: False)
            self.Zone.is_cool_mode = \
                (lambda *_, **__: False)
            self.Zone.is_dry_mode = \
                (lambda *_, **__: False)
            self.Zone.is_auto_mode = \
                (lambda *_, **__: False)
            self.Zone.is_fan_mode = \
                (lambda *_, **__: False)
            self.Zone.is_off_mode = \
                (lambda *_, **__: True)
            self.Zone.current_mode = self.Zone.OFF_MODE
        else:
            self.fail("mock mode '%s' is not supported" % mock_mode)

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

    def test_DisplayBasicThermostatSummary(self):
        """Confirm print_basic_thermostat_summary() works without error."""

        # override switch position function to be determinant
        self.switch_position_backup = self.Zone.get_system_switch_position
        try:
            self.Zone.get_system_switch_position = \
                (lambda *_, **__: self.Zone.system_switch_position[
                    tc.ThermostatCommonZone.DRY_MODE])
            self.Zone.display_basic_thermostat_summary()
        finally:
            self.Zone.get_system_switch_position = self.switch_position_backup

    @unittest.skipIf(not utc.enable_sht31_tests,
                     "sht31 tests are disabled")
    def test_ThermostatBasicCheckout(self):
        """Verify thermostat_basic_checkout()."""

        # override switch position function to be determinant
        self.switch_position_backup = self.Zone.get_system_switch_position
        try:
            self.Zone.get_system_switch_position = \
                (lambda *_, **__: self.Zone.system_switch_position[
                    tc.ThermostatCommonZone.DRY_MODE])
            thermostat_type = utc.unit_test_argv[api.get_argv_position(
                "thermostat_type")]
            zone = utc.unit_test_argv[api.get_argv_position(
                "zone")]
            mod = api.load_hardware_library(thermostat_type)
            Thermostat, Zone = \
                tc.thermostat_basic_checkout(
                    api,
                    thermostat_type,
                    zone,
                    mod.ThermostatClass, mod.ThermostatZone
                    )
            print("thermotat=%s" % type(Thermostat))
            print("thermotat=%s" % type(Zone))
        finally:
            self.Zone.get_system_switch_position = self.switch_position_backup

    def test_RevertTemperatureDeviation(self):
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
            # print("current thermostat mode=%s" % self.Zone.current_mode)

            for new_setpoint in [13, 26, -4, 101]:
                # get current setpoint
                current_setpoint = self.Zone.current_setpoint

                # revert setpoint
                msg = ("reverting setpoint from %s to %s" %
                       (util.temp_value_with_units(current_setpoint),
                        util.temp_value_with_units(new_setpoint)))
                self.Zone.revert_temperature_deviation(new_setpoint, msg)

                # verify setpoint
                actual_setpoint = self.Zone.current_setpoint
                self.assertEqual(new_setpoint, actual_setpoint,
                                 "reverting setpoint failed, actual=%s, "
                                 "expected=%s" % (util.temp_value_with_units(
                                     actual_setpoint),
                                     util.temp_value_with_units(new_setpoint)))

            # verify function default behavior
            new_setpoint = self.Zone.current_setpoint = 56

            # revert setpoint
            msg = ("reverting setpoint from %s to %s" %
                   (util.temp_value_with_units(actual_setpoint),
                    util.temp_value_with_units(new_setpoint)))
            self.Zone.revert_temperature_deviation(msg=msg)

            # verify setpoint
            actual_setpoint = self.Zone.current_setpoint
            self.assertEqual(new_setpoint, actual_setpoint,
                             "reverting setpoint failed, actual=%s, "
                             "expected=%s" % (util.temp_value_with_units(
                                 actual_setpoint),
                                 util.temp_value_with_units(new_setpoint)))

        finally:
            self.restore_functions()

    def test_ReportHeatingParameters(self):
        """Verify report_heating_parameters()."""
        test_cases = [tc.ThermostatCommonZone.OFF_MODE]
        for test_case in test_cases:
            print("test_case=%s" % test_case)
            self.Zone.report_heating_parameters(switch_position=test_case)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
