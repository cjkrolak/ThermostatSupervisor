"""
Unit test module for sht31_flask_server.py.

Flask server tests currently do not work on Azure pipelines
because ports cannot be opened on shared pool.
"""
# built-in imports
import unittest

# local imports
# thermostat_api is imported but not used to avoid a circular import
import thermostat_api as api  # pylint: disable=unused-import.
import sht31
import sht31_config
import unit_test_common as utc
import utilities as util


class Test(utc.UnitTestCommon):
    """Test functions in sht31_flask_server.py."""

    # app = sht31_fs.create_app()

    def setUp(self):
        # sht31 flask server is automatically spawned in sht31
        # Thermostat class if unit test zone is being used.
        self.print_test_name()

    def tearDown(self):
        self.print_test_result()

    @unittest.skipIf(utc.is_azure_environment(),
                     "this test not supported on Azure Pipelines")
    def test_SHT31_FlaskServer(self):
        """
        Confirm Flask server returns valid data.
        """
        measurements_bckup = sht31_config.measurements
        try:
            for sht31_config.measurements in [1, 10, 100, 1000]:
                print("\ntesting SHT31 flask server with %s %s..." %
                      (sht31_config.measurements,
                       ["measurement", "measurements"][
                           sht31_config.measurements > 1]))
                self.validate_flask_server()
        finally:
            sht31_config.measurements = measurements_bckup

    def validate_flask_server(self):
        """
        Launch SHT31 Flask server and validate data.
        """
        print("creating thermostat object...")
        Thermostat = sht31.ThermostatClass(sht31_config.UNIT_TEST_ZONE)
        print("printing thermostat meta data:")
        Thermostat.print_all_thermostat_metadata()

        # create Zone object
        Zone = sht31.ThermostatZone(Thermostat)

        # update runtime overrides
        Zone.update_runtime_parameters(api.user_inputs)

        print("current thermostat settings...")
        print("switch position: %s" % Zone.get_system_switch_position())
        print("heat mode=%s" % Zone.get_heat_mode())
        print("cool mode=%s" % Zone.get_cool_mode())
        print("temporary hold minutes=%s" %
              Zone.get_temporary_hold_until_time())
        meta_data = Thermostat.get_all_metadata()
        print("thermostat meta data=%s" % meta_data)
        print("thermostat display tempF=%s" % Zone.get_display_temp())

        # verify measurements
        self.assertEqual(meta_data["measurements"],
                         sht31_config.measurements,
                         "measurements: actual=%s, expected=%s" %
                         (meta_data["measurements"],
                          sht31_config.measurements))

        # verify metadata
        test_cases = {
            "get_display_temp": {"min_val": 80, "max_val": 120},
            "get_is_humidity_supported": {"min_val": True, "max_val": True},
            "get_display_humidity": {"min_val": 49, "max_val": 51},
            }
        for param, limits in test_cases.items():
            return_val = getattr(Zone, param)()
            print("'%s'=%s" % (param, return_val))
            min_val = limits["min_val"]
            max_val = limits["max_val"]
            self.assertTrue(min_val <= return_val <= max_val,
                            "'%s'=%s, not between %s and %s" %
                            (param, return_val, min_val, max_val))
        # cleanup
        del Zone
        del Thermostat


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
