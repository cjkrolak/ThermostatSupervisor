"""
Unit test module for utilities.py.
"""
# built-in imports
import os
import unittest

# local imports
import utilities as util


class Test(unittest.TestCase):
    """Test functions in utilities.py."""

    def setUp(self):
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        pass

    def testLogMsgWrite(self):
        """
        Confirm log_msg() can write and append to file.
        """
        file_name = "unit_test.txt"
        full_path = util.get_full_file_path(file_name)

        # delete unit test file if it exists
        try:
            os.remove(full_path)
            print("unit test file '%s' deleted." % full_path)
        except FileNotFoundError:
            print("unit test file '%s' did not exist." % full_path)

        # write to file that does not exist
        test_msg1 = "first test message from unit test"
        # test_msg1_length = util.utf8len(test_msg1 + "\n") + 1
        return_buffer = util.log_msg(test_msg1, mode=util.BOTH_LOG,
                                     file_name=file_name)
        self.assertEqual(return_buffer["status"], util.NO_ERROR)

        # confirm file exists
        file_size_bytes = os.path.getsize(full_path)
        # self.assertEqual(file_size_bytes, test_msg1_length)
        self.assertGreater(file_size_bytes, 30)

        # append to file that does exist
        test_msg2 = "second test message from unit test"
        # test_msg2_length = util.utf8len(test_msg2 + "\n") + 1
        return_buffer = util.log_msg(test_msg2, mode=util.BOTH_LOG,
                                     file_name=file_name)
        self.assertEqual(return_buffer["status"], util.NO_ERROR)

        # confirm file exists
        file_size_bytes = os.path.getsize(full_path)
        # file size estimate differs per platform, need to refine
        # self.assertEqual(file_size_bytes,
        #                 test_msg1_length + test_msg2_length)
        self.assertGreater(file_size_bytes, 60)

    def testGetEnvVariable(self):
        """
        Confirm get_env_variable() can retrieve values.
        """
        for env_key in ["GMAIL_USERNAME", "GMAIL_PASSWORD",
                        "GMAIL_TO_USERNAME", "TCC_USERNAME",
                        "TCC_PASSWORD"]:
            buff = util.get_env_variable(env_key)
            print("env$%s=%s" % (env_key, buff["value"]))
            self.assertEqual(buff["status"], util.NO_ERROR)
            self.assertGreater(len(buff["value"]), 0)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main()
