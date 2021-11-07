"""
Unit test module for sht31_flask_server.py.
"""
# built-in imports
import threading
import unittest

# local imports
# thermostat_api is imported but not used to avoid a circular import
import thermostat_api as api  # pylint: disable=unused-import.
import sht31
import sht31_flask_server as sht31_fs
import unit_test_common as utc
import utilities as util


class Test(unittest.TestCase):
    """Test functions in utilities.py."""

    app = sht31_fs.create_app()

    def setUp(self):
        sht31_fs.debug = False
        sht31_fs.measurements = 10
        sht31_fs.unit_test_mode = True
        util.log_msg.file_name = "unit_test.txt"
        print("starting sht31 server thread...")
        self.fs = threading.Thread(target=sht31_fs.app.run,
                                   args=('0.0.0.0', 5000, False))
        self.fs.daemon = True  # make thread daemonic
        self.fs.start()
        print("thread alive status=%s" % self.fs.is_alive())
        print("Flask server setup is complete")

    def tearDown(self):
        print("thread alive status=%s" % self.fs.is_alive())
        if self.fs.daemon:
            print("flask server is daemon thread, "
                  "thread will terminate when main thread terminates")
        else:
            print("WARNING: flask server is not daemon thread, "
                  "thread may still be active")

    def test_FlaskServer(self):
        """
        Confirm Flask server returns valid data.
        """
        utc.print_test_name()
        print("creating thermostat object...")
        Thermostat = sht31.ThermostatClass(sht31.UNITTEST_SHT31)
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
        print("thermostat meta data=%s" % Thermostat.get_all_metadata())
        print("thermostat display tempF=%s" % Zone.get_display_temp())

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


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()
