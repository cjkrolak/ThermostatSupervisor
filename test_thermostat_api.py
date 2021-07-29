"""
Unit test module for thermostat_api.py.
"""
# built-in imports
import random
import unittest

# local imports
import thermostat_api as ta
import utilities as util


class Test(unittest.TestCase):
    """Test functions in utilities.py."""
    tstat = "UNITTEST"

    def setUp(self):
        ta.thermostats[self.tstat] = {}  # dummy unit test thermostat

    def tearDown(self):
        del ta.thermostats[self.tstat]

    def testSetTargetZone(self):
        """
        Confirm target zone can be set and read back.
        """
        test_cases = self.generate_random_list(10, 0, 99)
        for zone in test_cases:
            print("testing set_target_zone(%s)" % zone)
            ta.set_target_zone(self.tstat, zone)
            self.assertEqual(ta.thermostats[self.tstat]["zone"], zone)

    def testSetPollTime(self):
        """
        Confirm poll time can be set and read back.
        """
        test_cases = self.generate_random_list(10, 100, 199)
        for poll_time_sec in test_cases:
            print("testing set_poll_time(%s)" % poll_time_sec)
            ta.set_poll_time(self.tstat, poll_time_sec)
            self.assertEqual(ta.thermostats[self.tstat]["poll_time_sec"],
                             poll_time_sec)

    def testSetConnectionTime(self):
        """
        Confirm connection time can be set and read back.
        """
        test_cases = self.generate_random_list(10, 200, 299)
        for connection_time_sec in test_cases:
            print("testing set_connection_time(%s)" % connection_time_sec)
            ta.set_connection_time(self.tstat, connection_time_sec)
            self.assertEqual(ta.thermostats[self.tstat]["connection_time_sec"],
                             connection_time_sec)
    
    def generate_random_list(self, count, min_val, max_val):
        """
        Generate a list of random numbers between a range.

        inputs:
            count(int): number of values
            min_val(int): lower end of range
            max_val(int): upper end of range.
        returns:
            list
        """
        random_list = []
        for _ in range(0, count):
            n = random.randint(min_val, max_val)
            random_list.append(n)
        return random_list


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()
