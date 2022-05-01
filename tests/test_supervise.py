"""
Unit test module for supervise.py.
"""
# built-in imports
import unittest

# local imports
from thermostatsupervisor import emulator_config
from thermostatsupervisor import environment as env
from thermostatsupervisor import supervise as sup
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class Test(utc.UnitTest):
    """Test functions in supervise.py."""

    def setUp(self):
        super().setUp()
        self.setup_mock_thermostat_zone()

    def tearDown(self):
        self.teardown_mock_thermostat_zone()
        super().tearDown()

    @unittest.skipIf(env.is_azure_environment(),
                     "this test not supported on Azure Pipelines")
    def test_supervisor(self):
        """Verify main supervisor loop."""
        sup.supervisor(emulator_config.ALIAS,
                       emulator_config.supported_configs["zones"][0])


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
