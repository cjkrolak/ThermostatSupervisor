"""
Unit test module for supervise.py.
"""
# built-in imports
import unittest

# local imports
import supervise as sup
import thermostat_api as api
import unit_test_common as utc
import utilities as util


class Test(unittest.TestCase):
    """Test functions in utilities.py."""
    tstat = "UNITTEST"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testParseRuntimeParameter(self):
        """
        Verify test verify_required_env_variables() passes in nominal
        condition and fails with missing key.
        """
        utc.print_test_name()
        input_list = ["supervise.py", "honeywell", "0", "9", "90", "3"]

        # parse thermostat type parameter (argv[1] if present):
        tstat_type = sup.parse_runtime_parameter("thermostat_type", 1, str,
                                                 api.HONEYWELL,
                                                 api.SUPPORTED_THERMOSTATS,
                                                 input_list)
        self.assertEqual(tstat_type, api.HONEYWELL, "actual=%s, expected=%s" %
                         (tstat_type, api.HONEYWELL))

        # parse zone number parameter (argv[2] if present):
        zone_input = \
            sup.parse_runtime_parameter("zone", 2, int, 0,
                                        api.SUPPORTED_THERMOSTATS[
                                            tstat_type]["zones"],
                                        input_list)
        self.assertEqual(zone_input, 0, "actual=%s, expected=%s" %
                         (zone_input, 0))

        # parse the poll time override (argv[3] if present):
        poll_time_input = sup.parse_runtime_parameter("poll_time_sec", 3, int,
                                                      10 * 60,
                                                      range(0, 24 * 60 * 60),
                                                      input_list)
        self.assertEqual(poll_time_input, 9, "actual=%s, expected=%s" %
                         (poll_time_input, 9))

        # parse the connection time override (argv[4] if present):
        connection_time_input = \
            sup.parse_runtime_parameter("connection_time_sec", 4,
                                        int, 8 * 60 * 60,
                                        range(0, 24 * 60 * 60), input_list)
        self.assertEqual(connection_time_input, 90, "actual=%s, expected=%s" %
                         (connection_time_input, 90))

        # parse the tolerance override (argv[5] if present):
        tolerance_degrees_input = \
            sup.parse_runtime_parameter("tolerance_degrees", 5,
                                        int, 2, range(0, 10), input_list)
        self.assertEqual(tolerance_degrees_input, 3, "actual=%s, expected=%s" %
                         (tolerance_degrees_input, 3))


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()
