"""
Unit test module for sht31_flask_server.py.

Flask server tests currently do not work on Azure pipelines
because ports cannot be opened on shared pool.
"""
# built-in imports
import os
import unittest

# local imports
# thermostat_api is imported but not used to avoid a circular import
from thermostatsupervisor import environment as env
from thermostatsupervisor import thermostat_api as api  # noqa F401, pylint: disable=unused-import.
from thermostatsupervisor import sht31
from thermostatsupervisor import sht31_config
from thermostatsupervisor import sht31_flask_server as sht31_fs
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


@unittest.skipIf(not utc.ENABLE_SHT31_TESTS,
                 "sht31 tests are disabled")
@unittest.skipIf(env.is_azure_environment(),
                 "this test not supported on Azure Pipelines")
@unittest.skipIf(not utc.ENABLE_FLASK_INTEGRATION_TESTS,
                 "flask integration tests are disabled")
class IntegrationTest(utc.UnitTest):
    """Test functions in sht31_flask_server.py."""

    # sht31 flask server is automatically spawned in sht31
    # Thermostat class if unit test zone is being used.

    def test_sht31_flask_server_all_pages(self):
        """
        Confirm all pages return data from Flask server.
        """
        # do not test these pages
        no_test_list = ["i2c_recovery", "reset"]

        # loopback does not work so use local sht31 zone if testing
        # on the local net.  If not, use the DNS name.
        zone = sht31_config.get_preferred_zone()

        for test_case in sht31_config.flask_folder:
            if test_case in no_test_list:
                print(f"test_case={test_case}: bypassing this test case")
                continue

            print(f"test_case={test_case}")
            Thermostat = \
                sht31.ThermostatClass(
                    zone, path=sht31_config.flask_folder[test_case])
            print("printing thermostat meta data:")
            return_data = Thermostat.print_all_thermostat_metadata(
                zone)

            # validate dictionary was returned
            self.assertTrue(isinstance(return_data, dict),
                            "return data is not a dictionary")

            # validate key as proof of correct return page
            if test_case in ["production", "unit_test"]:
                expected_key = "measurements"
            elif test_case in ["diag", "clear_diag", "enable_heater",
                               "disable_heater", "soft_reset"]:
                expected_key = "raw_binary"
            elif test_case in ["i2c_detect", "i2c_detect_0", "i2c_detect_1"]:
                expected_key = "i2c_detect"
            elif test_case == "i2c_recovery":
                expected_key = "i2c_recovery"
            elif test_case == "reset":
                expected_key = "message"
            else:
                expected_key = "bogus"
            self.assertTrue(expected_key in return_data,
                            f"test_case '{test_case}': key '{expected_key}' "
                            f"was not found in return data: {return_data}")

    def test_sht31_flask_server(self):
        """
        Confirm Flask server returns valid data.
        """
        measurements_bckup = sht31_config.MEASUREMENTS
        try:
            for sht31_config.measurements in [1, 10, 100, 1000]:
                msg = ['measurement', 'measurements'][
                    sht31_config.MEASUREMENTS > 1]
                print(f"\ntesting SHT31 flask server with "
                      f"{sht31_config.MEASUREMENTS} {msg}...")
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
        Thermostat.print_all_thermostat_metadata(sht31_config.UNIT_TEST_ZONE)

        # create mock runtime args
        api.uip = api.UserInputs(utc.unit_test_sht31)

        # create Zone object
        Zone = sht31.ThermostatZone(Thermostat)

        # update runtime overrides
        Zone.update_runtime_parameters()

        print("current thermostat settings...")
        print(f"switch position: {Zone.get_system_switch_position()}")
        print(f"heat mode={Zone.is_heat_mode()}")
        print(f"cool mode={Zone.is_cool_mode()}")
        print(f"temporary hold minutes={Zone.get_temporary_hold_until_time()}")
        meta_data = Thermostat.get_all_metadata(sht31_config.UNIT_TEST_ZONE)
        print(f"thermostat meta data={meta_data}")
        print(f"thermostat display temp="
              f"{util.temp_value_with_units(Zone.get_display_temp())}")

        # verify measurements
        self.assertEqual(meta_data["measurements"],
                         sht31_config.MEASUREMENTS,
                         f"measurements: actual={meta_data['measurements']}, "
                         f"expected={sht31_config.MEASUREMENTS}")

        # verify metadata
        test_cases = {
            "get_display_temp": {"min_val": 80, "max_val": 120},
            "get_is_humidity_supported": {"min_val": True, "max_val": True},
            "get_display_humidity": {"min_val": 49, "max_val": 51},
        }
        for param, limits in test_cases.items():
            return_val = getattr(Zone, param)()
            print(f"'{param}'={return_val}")
            min_val = limits["min_val"]
            max_val = limits["max_val"]
            self.assertTrue(min_val <= return_val <= max_val,
                            f"'{param}'={return_val}, not between {min_val} "
                            f"and {max_val}")
        # cleanup
        del Zone
        del Thermostat


class RuntimeParameterTest(utc.RuntimeParameterTest):
    """sht31 flask server Runtime parameter tests."""

    mod = sht31_fs  # module to test
    script = os.path.realpath(__file__)
    debug = False

    # fields for testing, mapped to class variables.
    # (value, field name)
    test_fields = [
        (script, os.path.realpath(__file__)),
        (debug, sht31_fs.input_flds.debug_fld),
    ]


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
