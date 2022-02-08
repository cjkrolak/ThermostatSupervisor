"""
Unit test module for supervise.py.
"""
# built-in imports
import unittest

# local imports
from thermostatsupervisor import sht31_config
from thermostatsupervisor import supervise as sup
from tests import unit_test_common as utc
from thermostatsupervisor import utilities as util


class Test(utc.UnitTest):
    """Test functions in supervise.py."""

    def setUp(self):
        self.print_test_name()
        self.setup_mock_thermostat_zone()

    def tearDown(self):
        self.teardown_mock_thermostat_zone()
        self.print_test_result()

    def test_display_session_settings(self):
        """
        Verify display_session_settings() with all permutations.
        """
        for revert_setting in [False, True]:
            for revert_all_setting in [False, True]:
                print(f"{'-' * 60}")
                print(f"testing revert={revert_setting}, "
                      f"revert all={revert_all_setting}")
                sup.display_session_settings(self.thermostat_type,
                                             self.zone,
                                             revert_setting,
                                             revert_all_setting)

    def test_display_runtime_settings(self):
        """Verify display_runtime_settings()."""
        sup.display_runtime_settings(self.Zone)

    @unittest.skipIf(util.is_azure_environment(),
                     "this test not supported on Azure Pipelines")
    def test_supervisor(self):
        """Verify main supervisor loop."""
        sup.supervisor(sht31_config.ALIAS, sht31_config.UNIT_TEST_ZONE)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
