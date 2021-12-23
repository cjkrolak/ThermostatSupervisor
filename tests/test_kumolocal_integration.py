"""
Integration test module for kumolocal.py.

This test requires connection to kumolocal thermostat.
"""
# built-in imports
import unittest

# local imports
from .. import azure_context  # noqa F401, pylint: disable=unused-import.
import kumolocal
import kumolocal_config
import unit_test_common as utc
import utilities as util


@unittest.skipIf(not utc.enable_integration_tests,
                 "integration tests are disabled")
@unittest.skipIf(not utc.enable_kumolocal_tests,
                 "kumolocal tests are disabled")
class IntegrationTest(utc.IntegrationTest):
    """
    Test functions in kumolocal.py.

    Tests are named to ensure basic checkout is executed first
    and supervise loop is executed last.
    """
    def setUp(self):
        self.print_test_name()

        # argv list must be valid settings
        self.unit_test_argv = [
            "supervise.py",  # module
            "kumolocal",  # thermostat
            "0",  # zone
            "30",  # poll time in sec
            "1000",  # reconnect time in sec
            "2",  # tolerance
            "",  # thermostat mode, no target
            "3",  # number of measurements
            ]
        self.mod = kumolocal
        self.mod_config = kumolocal_config


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
