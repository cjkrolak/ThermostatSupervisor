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


class Test(utc.UnitTestCommon):
    """Test functions in utilities.py."""

    def setUp(self):
        self.print_test_name()
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        self.print_test_result()

    def test_GetEnvVariable(self):
        """
        Confirm get_env_variable() can retrieve values.
        """
        for env_key in ["GMAIL_USERNAME", "GMAIL_PASSWORD"]:
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
        util.load_all_env_variables()
        print("env var dict=%s" % util.env_variables)

    def test_GetFunctionName(self):
        """
        Confirm get_function_name works as expected.
        """
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

    def test_LogMsgWrite(self):
        """
        Confirm log_msg() can write and append to file.
        """
        file_name = "unit_test.txt"
        full_path = util.get_full_file_path(file_name)

        # delete unit test file if it exists
        self.delete_test_file(full_path)

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

    def test_GetFileSizeBytes(self):
        """
        Confirm get_file_size_bytes() works as expected.
        """
        full_path = __file__  # this file

        # assuming file exists, should return non-zero value
        result = util.get_file_size_bytes(full_path)
        self.assertTrue(result > 0,
                        "file size for existing file is %s, expected > 0" %
                        result)

        # bogus file, should return zero value
        result = util.get_file_size_bytes("bogus.123")
        self.assertTrue(result == 0,
                        "file size for bogus file is %s, expected == 0" %
                        result)

    def test_LogRotateFile(self):
        """
        Confirm log_rotate_file() works as expected.
        """
        file_name = "unit_test.txt"
        full_path = util.get_full_file_path(file_name)
        file_size_bytes = util.get_file_size_bytes(full_path)

        # check while under max limit, should not rotate file
        file_size_bytes_same = util.log_rotate_file(full_path, file_size_bytes,
                                                    file_size_bytes + 1)
        self.assertEqual(file_size_bytes, file_size_bytes_same,
                         "log_rotate_file under max limit, file size should "
                         "not change, expected size=%s, actual size=%s" %
                         (file_size_bytes, file_size_bytes_same))

        # check while above max limit, should rotate file and return 0
        file_size_bytes_new = util.log_rotate_file(full_path, file_size_bytes,
                                                   file_size_bytes - 1)
        expected_size = 0
        self.assertEqual(expected_size, file_size_bytes_new,
                         "log_rotate_file above max limit, file size should "
                         "be reset to 0, expected size=%s, actual size=%s" %
                         (expected_size, file_size_bytes_new))

    def test_WriteToFile(self):
        """
        Verify write_to_file() function.
        """
        file_name = "unit_test.txt"
        full_path = util.get_full_file_path(file_name)

        # delete unit test file if it exists
        self.delete_test_file(full_path)

        # test message
        msg = "unit test bogus message"
        print("test message=%s bytes" % util.utf8len(msg))

        # write to non-existing file, bytes written + EOF == bytes read
        bytes_written = util.write_to_file(full_path, 0, msg)
        bytes_expected = bytes_written + [0, 1][util.is_windows_environment()]
        bytes_present = util.get_file_size_bytes(full_path)
        self.assertEqual(bytes_expected, bytes_present,
                         "writing to non-existent file, bytes written=%s, "
                         "file size=%s" % (bytes_expected, bytes_present))

        # write to existing file with reset, bytes written == bytes read
        bytes_written = util.write_to_file(full_path, 0, msg)
        bytes_expected = bytes_written + [0, 1][util.is_windows_environment()]
        bytes_present = util.get_file_size_bytes(full_path)
        self.assertEqual(bytes_expected, bytes_present,
                         "writing to existing file with override option, "
                         "bytes written=%s, "
                         "file size=%s" % (bytes_expected, bytes_present))

        # write to existing file, bytes written < bytes read
        file_size_bytes = util.get_file_size_bytes(full_path)
        bytes_written = util.write_to_file(full_path, file_size_bytes, msg)
        bytes_expected = (bytes_written + file_size_bytes +
                          [0, 1][util.is_windows_environment()])
        bytes_present = util.get_file_size_bytes(full_path)
        self.assertEqual(bytes_expected, bytes_present,
                         "writing to existent file, bytes expected=%s, "
                         "file size=%s" % (bytes_expected, bytes_present))

    def test_GetFullFilePath(self):
        """
        Verify get_full_file_path() function.
        """
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

        for test_case in [44, -1, 101, 2]:
            for precision in [0, 1, 2]:
                for disp_unit in ['F', 'c']:
                    formatted = "%.*f" % (precision, test_case)
                    expected_val = f'{formatted}°{disp_unit}'
                    actual_val = util.temp_value_with_units(test_case,
                                                            disp_unit,
                                                            precision)
                    self.assertEqual(expected_val, actual_val,
                                     "test case: %s, expected_val=%s, "
                                     "actual_val=%s" %
                                     (test_case, expected_val, actual_val))

        # test failing case
        with self.assertRaises(ValueError):
            util.temp_value_with_units(-13, "bogus", 1)

    def test_HumidityValueWithUnits(self):
        """Verify function attaches units as expected."""

        for test_case in [44, -1, 101, 2]:
            for precision in [0, 1, 2]:
                for disp_unit in ['RH']:
                    formatted = "%.*f" % (precision, test_case)
                    expected_val = f'{formatted}%{disp_unit}'
                    actual_val = util.humidity_value_with_units(test_case,
                                                                disp_unit,
                                                                precision)
                    self.assertEqual(expected_val, actual_val,
                                     "test case: %s, expected_val=%s, "
                                     "actual_val=%s" %
                                     (test_case, expected_val, actual_val))

        # test failing case
        with self.assertRaises(ValueError):
            util.humidity_value_with_units(-13, "bogus", 1)

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

    def test_CtoF(self):
        """Verify C to F calculations."""

        # int and float cases
        for tempc in [0, -19, 34, 101, -44.1]:
            tempf = util.c_to_f(tempc)
            expected_tempf = tempc * 9.0 / 5 + 32
            self.assertEqual(expected_tempf, tempf, "test case %s: "
                             "expected=%s, actual=%s" %
                             (tempc, expected_tempf, tempf))

        # verify exception cases
        for tempc in ['0', None, "", "*"]:
            with self.assertRaises(TypeError):
                tempf = util.c_to_f(tempc)
            # expected_tempf = tempc
            # self.assertEqual(expected_tempf, tempf, "test case %s: "
            #                  "expected=%s, actual=%s" %
            #                  (tempc, expected_tempf, tempf))

    def test_FtoC(self):
        """Verify F to C calculations."""

        # int and float cases
        for tempf in [0, -19, 34, 101, -44.1]:
            tempc = util.f_to_c(tempf)
            expected_tempc = (tempf - 32) * 5 / 9.0
            self.assertEqual(expected_tempc, tempc, "test case %s: "
                             "expected=%s, actual=%s" %
                             (tempf, expected_tempc, tempc))

        # verify exception case
        for tempf in ['0', None, "", "*"]:
            with self.assertRaises(TypeError):
                tempc = util.f_to_c(tempf)
            # expected_tempc = tempf  # pass-thru
            # self.assertEqual(expected_tempc, tempc, "test case %s: "
            #                  "expected=%s, actual=%s" %
            #                  (tempf, expected_tempc, tempc))

    def delete_test_file(self, full_path):
        """Delete the test file.

        inputs:
            full_path(str): full file path
        returns:
            (bool): True if file was deleted, False if it did not exist.
        """
        try:
            os.remove(full_path)
            print("unit test file '%s' deleted." % full_path)
            return True
        except FileNotFoundError:
            print("unit test file '%s' did not exist." % full_path)
            return False


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
