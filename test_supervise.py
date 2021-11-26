"""
Unit test module for supervise.py.
"""
# built-in imports
import unittest

# local imports
import utilities as util


class Test(unittest.TestCase):
    """Test functions in supervise.py."""
    tstat = "UNITTEST"

    def setUp(self):
        pass

    def tearDown(self):
        pass


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
