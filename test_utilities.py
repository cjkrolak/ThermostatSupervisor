"""
Unit test module for utilities.py.
"""
# built-in imports
import os
import shutil
import unittest

# local imports
import unit_test_common as utc
import utilities as util


class Test(unittest.TestCase):
    """Test functions in utilities.py."""

    def setUp(self):
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        pass

    def test_GetEnvVariable(self):
        """
        Confirm get_env_variable() can retrieve values.
        """
        utc.print_test_name()
        for env_key in ["GMAIL_USERNAME", "GMAIL_PASSWORD",
                        "TCC_USERNAME", "TCC_PASSWORD"]:
            buff = util.get_env_variable(env_key)
            print("env$%s=%s" % (env_key,
                                 [buff["value"],
                                  "(hidden)"]['PASSWORD' in env_key]))
            self.assertEqual(buff["status"], util.NO_ERROR)
            self.assertGreater(len(buff["value"]), 0)

    def test_LoadAllEnvVariables(self):
        """
        Confirm all env variables can be loaded.
        """
        utc.print_test_name()
        util.load_all_env_variables()
        print("env var dict=%s" % util.env_variables)

    def test_GetFunctionName(self):
        """
        Confirm get_function_name works as expected.
        """
        utc.print_test_name()
        # default
        test = "<default>"
        print("testing util.get_function_name(%s)" % test)
        ev_1 = "test_GetFunctionName"
        result_1 = util.get_function_name()
        self.assertEqual(ev_1, result_1, "expected=%s, actual=%s" %
                         (ev_1, result_1))

        # test 1
        test = 1
        print("testing util.get_function_name(%s)" % test)
        ev_1 = "test_GetFunctionName"
        result_1 = util.get_function_name(test)
        self.assertEqual(ev_1, result_1, "test%s: expected=%s, actual=%s" %
                         (test, ev_1, result_1))

        # test 2
        test = 2
        print("testing util.get_function_name(%s)" % test)
        ev_1 = ["run",  # Linux
                "_callTestMethod",  # windows
                ]
        result_1 = util.get_function_name(test)
        self.assertTrue(result_1 in ev_1, "test%s: expected values=%s, "
                        "actual=%s" % (test, ev_1, result_1))

    def test_LogMsgCreateFolder(self):
        """
        Confirm log_msg() will create folder if needed
        """
        utc.print_test_name()
        # override data file path
        path_backup = util.file_path
        util.file_path = ".//unittest_data"

        file_name = "unit_test.txt"
        full_path = util.get_full_file_path(file_name)
        try:
            # remove directory if it already exists
            if os.path.exists(util.file_path):
                shutil.rmtree(util.file_path)

            # write to file and path that does not exist
            test_msg1 = "first test message from unit test"
            # test_msg1_length = util.utf8len(test_msg1 + "\n") + 1
            return_buffer = util.log_msg(test_msg1, mode=util.BOTH_LOG,
                                         file_name=file_name)
            self.assertEqual(return_buffer["status"], util.NO_ERROR)

            # confirm file exists
            file_size_bytes = os.path.getsize(full_path)
            # self.assertEqual(file_size_bytes, test_msg1_length)
            self.assertGreater(file_size_bytes, 30)
        finally:
            # remove the directory
            shutil.rmtree(util.file_path)
            # restore original data file name
            util.file_path = path_backup

    def test_LogMsgRotate(self):
        """
        Verify log rotates at max_log_size_bytes.
        """
        utc.print_test_name()
        print("WARNING: test is aborting early, unfinished code.")
        return  # test is not yet ready
        # override rotate size
        size_backup = util.max_log_size_bytes
        util.file_path = ".//unittest_data"

        file_name = "unit_test.txt"
        full_path = util.get_full_file_path(file_name)
        try:
            # remove directory if it already exists
            if os.path.exists(util.file_path):
                os.removedirs(util.file_path)

            # write to file and path that does not exist
            test_msg1 = "first test message from unit test"
            # test_msg1_length = util.utf8len(test_msg1 + "\n") + 1
            return_buffer = util.log_msg(test_msg1, mode=util.BOTH_LOG,
                                         file_name=file_name)
            self.assertEqual(return_buffer["status"], util.NO_ERROR)

            # confirm file exists
            file_size_bytes = os.path.getsize(full_path)
            # self.assertEqual(file_size_bytes, test_msg1_length)
            self.assertGreater(file_size_bytes, 30)
        finally:
            # restore original log max size
            util.max_log_size_bytes = size_backup

    def test_LogMsgWrite(self):
        """
        Confirm log_msg() can write and append to file.
        """
        utc.print_test_name()
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

    def test_GetFullFilePath(self):
        """
        Verify get_full_file_path() function.
        """
        utc.print_test_name()
        file_name = "dummy.txt"
        full_path = util.get_full_file_path(file_name)
        expected_value = util.file_path + "//" + file_name
        print("full path=%s" % full_path)
        self.assertEqual(expected_value, full_path,
                         "expected=%s, actual=%s" %
                         (expected_value, full_path))

    def test_utf8len(self):
        """
        Verify utf8len().
        """
        utc.print_test_name()
        for test_case in ["A", "BB", "ccc", "dd_d"]:
            print("testing util.utf8len(%s)" % test_case)
            expected_value = 1 * len(test_case)
            actual_value = util.utf8len(test_case)
            self.assertEqual(expected_value, actual_value,
                             "expected=%s, actual=%s" %
                             (expected_value, actual_value))

    def test_GetLocalIP(self):
        """
        Verify get_local_ip().
        """
        return_val = util.get_local_ip()
        self.assertTrue(isinstance(return_val, str),
                        "get_local_ip() returned '%s' which is not a string")
        self.assertTrue(7 <= len(return_val) <= 15,
                        "get_local_ip() returned '%s' which is not "
                        "between 7 and 15 chars")

    def test_is_interactive_environment(self):
        """
        Verify is_interactive_environment().
        """
        return_val = util.is_interactive_environment()
        self.assertTrue(isinstance(return_val, bool))

    def test_TempValueWithUnits(self):
        """Verify function attaches units as expected."""
        disp_unit = 'F'

        for test_case in [44, -1, 101, 2]:
            expected_val = f'{test_case}°{disp_unit}'
            actual_val = util.temp_value_with_units(test_case)
            self.assertEqual(expected_val, actual_val,
                             "test case: %s, expected_val=%s, actual_val=%s" %
                             (test_case, expected_val, actual_val))

    def test_GetKeyFromValue(self):
        """Verify get_key_from_value()."""
        test_dict = {'A': 1, 'B': 2, 'C': 1}

        # test keys with distinctvalue, determinant case
        test_case = 2
        expected_val = ['B']
        actual_val = util.get_key_from_value(test_dict, test_case)
        self.assertTrue(actual_val in expected_val,
                        "test case: %s, expected_val=%s, actual_val=%s" %
                        (test_case, expected_val, actual_val))

        # test keys with same value, indeterminant case
        test_case = 1
        expected_val = ['A', 'C']
        actual_val = util.get_key_from_value(test_dict, test_case)
        self.assertTrue(actual_val in expected_val,
                        "test case: %s, expected_val=%s, actual_val=%s" %
                        (test_case, expected_val, actual_val))

        # test key not found
        with self.assertRaises(KeyError):
            print("attempting to input bad dictionary key, "
                  "expect exception...")
            actual_val = util.get_key_from_value(test_dict, "bogus_value")


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
