"""
Unit test module for thermostat_api.py.
"""
# built-in imports
import random
import unittest

# local imports
import thermostat_api as api
import unit_test_common as utc
import utilities as util


class Test(unittest.TestCase):
    """Test functions in utilities.py."""
    tstat = "UNITTEST"

    def setUp(self):
        api.thermostats[self.tstat] = {  # dummy unit test thermostat
            "required_env_variables": {
                "GMAIL_USERNAME": None,
                "GMAIL_PASSWORD": None,
                },
            }

    def tearDown(self):
        del api.thermostats[self.tstat]

    # def testSetTargetZone(self):
    #     """
    #     Confirm target zone can be set and read back.
    #     """
    #     utc.print_test_name()
    #     test_cases = self.generate_random_list(10, 0, 99)
    #     for zone in test_cases:
    #         print("testing set_target_zone(%s)" % zone)
    #         api.set_target_zone(self.tstat, zone)
    #         self.assertEqual(api.thermostats[self.tstat]["zone"], zone)

    def testVerifyRequiredEnvVariables(self):
        """
        Verify test verify_required_env_variables() passes in nominal
        condition and fails with missing key.
        """
        missing_key = "agrfg"  # bogus key should be missing
        utc.print_test_name()
        # nominal condition, should pass
        print("testing nominal condition, will pass if gmail keys are present")
        self.assertTrue(api.verify_required_env_variables(self.tstat, "0"),
                        "test failed because one or more gmail keys "
                        "are missing")

        # missing key, should raise exception
        print("testing for with missing key 'unit_test', should fail")
        api.thermostats[self.tstat][
            "required_env_variables"][missing_key] = "bogus_value"
        try:
            self.assertFalse(api.verify_required_env_variables(
                self.tstat, "0"),
                             "test passed with missing key '%s',"
                             " should have failed" % missing_key)
        except KeyError:
            print("KeyError raised as expected for missing key")
        else:
            self.fail("expected KeyError but exception did not occur")
        finally:
            api.thermostats[self.tstat][
                "required_env_variables"].pop(missing_key)

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
