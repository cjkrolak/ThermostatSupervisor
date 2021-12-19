"""
Unit test module for supervise.py.
"""
# built-in imports
import unittest

# thermostat config files
import sht31_config

# local imports
import supervise as sup
import unit_test_common as utc
import utilities as util


class Test(utc.UnitTest):
    """Test functions in supervise.py."""

    def setUp(self):
        self.print_test_name()
        self.setUp_mock_thermostat_zone()

    def tearDown(self):
        self.tearDown_mock_thermostat_zone()
        self.print_test_result()

    def test_DisplaySessionSettings(self):
        """
        Verify display_session_settings() with all permutations.
        """
        for revert_setting in [False, True]:
            for revert_all_setting in [False, True]:
                print("%s" % ("-" * 60))
                print("testing revert=%s, revert all=%s" %
                      (revert_setting, revert_all_setting))
                sup.display_session_settings(self.thermostat_type,
                                             self.zone,
                                             revert_setting,
                                             revert_all_setting)

    def test_DisplayRuntimeSettings(self):
        """Verify display_runtime_settings()."""
        sup.display_runtime_settings(self.Zone)

    @unittest.skipIf(utc.is_azure_environment(),
                     "this test not supported on Azure Pipelines")
    def test_Supervisor(self):
        """Verify main supervisor loop."""
        sup.supervisor(sht31_config.ALIAS, sht31_config.UNIT_TEST_ZONE)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
