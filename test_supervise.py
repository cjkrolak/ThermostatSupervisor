"""
Unit test module for supervise.py.
"""
# built-in imports
import unittest

# local imports
import unit_test_common as utc
import utilities as util


class Test(utc.UnitTestCommon):
    """Test functions in supervise.py."""
    tstat = "UNITTEST"

    def setUp(self):
        self.print_test_name()

    def tearDown(self):
        self.print_test_result()


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
