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


class EnvironmentTests(utc.UnitTest):
    """Test functions related to environment and env variables."""

    def setUp(self):
        self.print_test_name()
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        self.print_test_result()

    def test_is_interactive_environment(self):
        """
        Verify is_interactive_environment().
        """
        return_val = util.is_interactive_environment()
        self.assertTrue(isinstance(return_val, bool))

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

    def test_IsHostOnLocalNet(self):
        """
        Verify is_host_on_local_net() runs as expected.

        Test cases need to be site-agnostic or require some type
        of filtering to ensure they pass regardless of which LAN
        this test is running from.

        util.is_host_on_local_net is not reliable when passing
        in an IP address so most test cases are for hostname only.
        """
        test_cases = [
            # [host_name, ip_address, expected_result]
            ['testwifi.here', None,
             not util.is_azure_environment()],  # Google wifi router
            ['bogus_host', '192.168.86.145', False],  # bogus host
            ['bogus_host', None, False],  # bogus host without IP
            ['dns.google', '8.8.8.8', True],  # should pass everywhere
            ]

        for test_case in test_cases:
            print("testing for '%s' at %s, expect %s" %
                  (test_case[0], test_case[1], test_case[2]))
            result, ip_address = util.is_host_on_local_net(test_case[0],
                                                           test_case[1])
            # verify IP length returned
            if result:
                ip_length_symbol = ">="
                ip_length_min = 7
                self.assertTrue(len(ip_address) >= ip_length_min,
                                "ip_address returned (%s) did not meet length "
                                "expectations (%s)" %
                                (ip_address,
                                 (ip_length_symbol + str(ip_length_min))))
            else:
                self.assertTrue(ip_address is None,
                                "ip_address returned (%s) is not None" %
                                ip_address)

            # verify expected result
            self.assertEqual(result, test_case[2],
                             "test_case=%s, expected=%s, actual=%s" %
                             (test_case[0], test_case[2], result))

    def test_GetPythonVersion(self):
        """Verify get_python_version()."""
        major_version, minor_version = util.get_python_version()

        # verify major version
        min_major = int(util.MIN_PYTHON_VERSION)
        self.assertTrue(major_version >= min_major,
                        "python major version (%s) is not gte min required "
                        "value (%s)" % (major_version, min_major))

        # verify minor version
        min_minor = int(str(util.MIN_PYTHON_VERSION)[
            str(util.MIN_PYTHON_VERSION).find(".") + 1:])
        self.assertTrue(minor_version >= min_minor,
                        "python minor version (%s) is not gte min required "
                        "value (%s)" % (minor_version, min_minor))

        # error checking invalid input parmeter
        with self.assertRaises(TypeError):
            print("attempting to invalid input parameter type, "
                  "expect exception...")
            util.get_python_version("3.7")

        # no decimal point
        util.get_python_version(3)

        # min value exception
        with self.assertRaises(EnvironmentError):
            print("attempting to verify version gte 99.99, "
                  "expect exception...")
            util.get_python_version(99.99)

        print("test passed all checks")


class FileAndLoggingTests(utc.UnitTest):
    """Test functions related to logging functions."""

    def setUp(self):
        self.print_test_name()
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        self.print_test_result()

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


class MetricsTests(utc.UnitTest):
    """Test functions related temperature/humidity metrics."""

    def setUp(self):
        self.print_test_name()
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        self.print_test_result()

    def test_TempValueWithUnits(self):
        """Verify function attaches units as expected."""

        for test_case in [44, -1, 101, 2, "13", "-13", None]:
            for precision in [0, 1, 2]:
                for disp_unit in ['F', 'c']:
                    print("test case: value=%s, precision=%s, units=%s" %
                          (test_case, precision, disp_unit))
                    if test_case is None:
                        formatted = "None"
                    else:
                        if isinstance(test_case, str):
                            formatted = "%.*f" % (precision, float(test_case))
                        else:
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

        for test_case in [44, -1, 101, 2, "13", "-13", None]:
            for precision in [0, 1, 2]:
                for disp_unit in ['RH']:
                    print("test case: value=%s, precision=%s, units=%s" %
                          (test_case, precision, disp_unit))
                    if test_case is None:
                        formatted = "None"
                    else:
                        if isinstance(test_case, str):
                            formatted = "%.*f" % (precision, float(test_case))
                        else:
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

    def test_CtoF(self):
        """Verify C to F calculations."""

        # int and float cases
        for tempc in [0, -19, 34, 101, -44.1, None]:
            tempf = util.c_to_f(tempc)
            if tempc is None:
                expected_tempf = None  # pass-thru
            else:
                expected_tempf = tempc * 9.0 / 5 + 32
            self.assertEqual(expected_tempf, tempf, "test case %s: "
                             "expected=%s, actual=%s" %
                             (tempc, expected_tempf, tempf))

        # verify exception cases
        for tempc in ['0', "", "*"]:
            with self.assertRaises(TypeError):
                tempf = util.c_to_f(tempc)
            # expected_tempf = tempc
            # self.assertEqual(expected_tempf, tempf, "test case %s: "
            #                  "expected=%s, actual=%s" %
            #                  (tempc, expected_tempf, tempf))

    def test_FtoC(self):
        """Verify F to C calculations."""

        # int and float cases
        for tempf in [0, -19, 34, 101, -44.1, None]:
            tempc = util.f_to_c(tempf)
            if tempf is None:
                expected_tempc = None  # pass-thru
            else:
                expected_tempc = (tempf - 32) * 5 / 9.0
            self.assertEqual(expected_tempc, tempc, "test case %s: "
                             "expected=%s, actual=%s" %
                             (tempf, expected_tempc, tempc))

        # verify exception case
        for tempf in ['0', "", "*"]:
            with self.assertRaises(TypeError):
                tempc = util.f_to_c(tempf)
            # expected_tempc = tempf  # pass-thru
            # self.assertEqual(expected_tempc, tempc, "test case %s: "
            #                  "expected=%s, actual=%s" %
            #                  (tempf, expected_tempc, tempc))


class MiscTests(utc.UnitTest):
    """Miscellaneous util tests."""

    def setUp(self):
        self.print_test_name()
        util.log_msg.file_name = "unit_test.txt"

    def tearDown(self):
        self.print_test_result()

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
