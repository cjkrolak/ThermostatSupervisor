"""
Unit test module for utilities.py.
"""
# built-in imports
import os
import shutil
import sys
import unittest

# local imports
from thermostatsupervisor import emulator_config
from thermostatsupervisor import utilities as util
from tests import unit_test_common as utc


class EnvironmentTests(utc.UnitTest):
    """Test functions related to environment and env variables."""

    def setUp(self):
        super().setUp()
        util.log_msg.file_name = "unit_test.txt"

    def test_is_interactive_environment(self):
        """
        Verify is_interactive_environment().
        """
        return_val = util.is_interactive_environment()
        self.assertTrue(isinstance(return_val, bool))

    def test_get_env_variable(self):
        """
        Confirm get_env_variable() can retrieve values.
        """
        for env_key in ["GMAIL_USERNAME", "GMAIL_PASSWORD"]:
            buff = util.get_env_variable(env_key)
            print(f"env${env_key}="
                  f"{[buff['value'], '(hidden)']['PASSWORD' in env_key]}")
            self.assertEqual(buff["status"], util.NO_ERROR)
            self.assertGreater(len(buff["value"]), 0)

    def test_load_all_env_variables(self):
        """
        Confirm all env variables can be loaded.
        """
        util.load_all_env_variables()
        print(f"env var dict={util.env_variables}")

    def test_get_local_ip(self):
        """
        Verify get_local_ip().
        """
        return_val = util.get_local_ip()
        self.assertTrue(isinstance(return_val, str),
                        "get_local_ip() returned '%s' which is not a string")
        self.assertTrue(7 <= len(return_val) <= 15,
                        "get_local_ip() returned '%s' which is not "
                        "between 7 and 15 chars")

    def test_is_host_on_local_net(self):
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
            print(f"testing for '{test_case[0]}' at {test_case[1]}, expect "
                  f"{test_case[2]}")
            result, ip_address = util.is_host_on_local_net(test_case[0],
                                                           test_case[1])
            # verify IP length returned
            if result:
                ip_length_symbol = ">="
                ip_length_min = 7
                self.assertTrue(len(ip_address) >= ip_length_min,
                                f"ip_address returned ({ip_address}) did not "
                                f"meet length expectations ("
                                f"{ip_length_symbol + str(ip_length_min)})")
            else:
                self.assertTrue(ip_address is None,
                                f"ip_address returned ({ip_address}) "
                                f"is not None")

            # verify expected result
            self.assertEqual(result, test_case[2],
                             f"test_case={test_case[0]}, expected="
                             f"{test_case[2]}, actual={result}")

    def test_get_python_version(self):
        """Verify get_python_version()."""
        major_version, minor_version = util.get_python_version()

        # verify major version
        min_major = int(util.MIN_PYTHON_MAJOR_VERSION)
        self.assertTrue(major_version >= min_major,
                        f"python major version ({major_version}) is not gte "
                        f"min required value ({min_major})")

        # verify minor version
        min_minor = int(str(util.MIN_PYTHON_MAJOR_VERSION)[
            str(util.MIN_PYTHON_MAJOR_VERSION).find(".") + 1:])
        self.assertTrue(minor_version >= min_minor,
                        f"python minor version ({minor_version}) is not gte "
                        f"min required value ({min_minor})")

        # error checking invalid input parmeter
        with self.assertRaises(TypeError):
            print("attempting to invalid input parameter type, "
                  "expect exception...")
            util.get_python_version("3", 7)

        # no decimal point
        util.get_python_version(3, None)

        # min value exception
        with self.assertRaises(EnvironmentError):
            print("attempting to verify version gte 99.99, "
                  "expect exception...")
            util.get_python_version(99, 99)

        print("test passed all checks")

    def test_dynamic_module_import(self):
        """
        Verify dynamic_module_import() runs without error

        TODO: this module results in a resourcewarning within unittest:
        sys:1: ResourceWarning: unclosed <socket.socket fd=628,
        family=AddressFamily.AF_INET, type=SocketKind.SOCK_DGRAM, proto=0,
        laddr=('0.0.0.0', 64963)>
        """

        # test successful case
        package_name = util.PACKAGE_NAME + "." + emulator_config.ALIAS
        pkg = util.dynamic_module_import(package_name)
        print(f"default thermostat returned package type {type(pkg)}")
        self.assertTrue(isinstance(pkg, object),
                        f"dynamic_module_import() returned type({type(pkg)}),"
                        f" expected an object")
        del sys.modules[package_name]
        del pkg

        # test failing case
        with self.assertRaises(ImportError):
            print("attempting to open bogus package name, expect exception...")
            pkg = util.dynamic_module_import(util.PACKAGE_NAME + "." + "bogus")
            print(f"'bogus' module returned package type {type(pkg)}")
        print("test passed")


class FileAndLoggingTests(utc.UnitTest):
    """Test functions related to logging functions."""

    def setUp(self):
        super().setUp()
        util.log_msg.file_name = "unit_test.txt"

    def test_log_msg_create_folder(self):
        """
        Confirm log_msg() will create folder if needed
        """
        # override data file path
        path_backup = util.FILE_PATH
        util.FILE_PATH = ".//unittest_data"

        file_name = "unit_test.txt"
        full_path = util.get_full_file_path(file_name)
        try:
            # remove directory if it already exists
            if os.path.exists(util.FILE_PATH):
                shutil.rmtree(util.FILE_PATH)

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
            shutil.rmtree(util.FILE_PATH)
            # restore original data file name
            util.FILE_PATH = path_backup

    def test_log_msg_write(self):
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

    def test_get_file_size_bytes(self):
        """
        Confirm get_file_size_bytes() works as expected.
        """
        full_path = __file__  # this file

        # assuming file exists, should return non-zero value
        result = util.get_file_size_bytes(full_path)
        self.assertTrue(result > 0,
                        f"file size for existing file is {result}, "
                        f"expected > 0")

        # bogus file, should return zero value
        result = util.get_file_size_bytes("bogus.123")
        self.assertTrue(result == 0,
                        f"file size for bogus file is {result}, expected == 0")

    def test_log_rotate_file(self):
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
                         f"log_rotate_file under max limit, file size should "
                         f"not change, expected size={file_size_bytes}, actual"
                         f" size={file_size_bytes_same}")

        # check while above max limit, should rotate file and return 0
        file_size_bytes_new = util.log_rotate_file(full_path, file_size_bytes,
                                                   file_size_bytes - 1)
        expected_size = 0
        self.assertEqual(expected_size, file_size_bytes_new,
                         f"log_rotate_file above max limit, file size should "
                         f"be reset to 0, expected size={expected_size}, "
                         f"actual size={file_size_bytes_new}")

    def test_write_to_file(self):
        """
        Verify write_to_file() function.
        """
        file_name = "unit_test.txt"
        full_path = util.get_full_file_path(file_name)

        # delete unit test file if it exists
        self.delete_test_file(full_path)

        # test message
        msg = "unit test bogus message"
        print(f"test message={util.utf8len(msg)} bytes")

        # write to non-existing file, bytes written + EOF == bytes read
        bytes_written = util.write_to_file(full_path, 0, msg)
        bytes_expected = bytes_written + [0, 1][util.is_windows_environment()]
        bytes_present = util.get_file_size_bytes(full_path)
        self.assertEqual(bytes_expected, bytes_present,
                         f"writing to non-existent file, bytes written="
                         f"{bytes_expected}, file size={bytes_present}")

        # write to existing file with reset, bytes written == bytes read
        bytes_written = util.write_to_file(full_path, 0, msg)
        bytes_expected = bytes_written + [0, 1][util.is_windows_environment()]
        bytes_present = util.get_file_size_bytes(full_path)
        self.assertEqual(bytes_expected, bytes_present,
                         f"writing to existing file with override option, "
                         f"bytes written={bytes_expected}, "
                         f"file size={bytes_present}")

        # write to existing file, bytes written < bytes read
        file_size_bytes = util.get_file_size_bytes(full_path)
        bytes_written = util.write_to_file(full_path, file_size_bytes, msg)
        bytes_expected = (bytes_written + file_size_bytes +
                          [0, 1][util.is_windows_environment()])
        bytes_present = util.get_file_size_bytes(full_path)
        self.assertEqual(bytes_expected, bytes_present,
                         f"writing to existent file, bytes "
                         f"expected={bytes_expected}, "
                         f"file size={bytes_present}")

    def test_get_full_file_path(self):
        """
        Verify get_full_file_path() function.
        """
        file_name = "dummy.txt"
        full_path = util.get_full_file_path(file_name)
        expected_value = util.FILE_PATH + "//" + file_name
        print(f"full path={full_path}")
        self.assertEqual(expected_value, full_path,
                         f"expected={expected_value}, actual={full_path}")

    def delete_test_file(self, full_path):
        """Delete the test file.

        inputs:
            full_path(str): full file path
        returns:
            (bool): True if file was deleted, False if it did not exist.
        """
        try:
            os.remove(full_path)
            print(f"unit test file '{full_path}' deleted.")
            return True
        except FileNotFoundError:
            print(f"unit test file '{full_path}' did not exist.")
            return False


class MetricsTests(utc.UnitTest):
    """Test functions related temperature/humidity metrics."""

    def setUp(self):
        super().setUp()
        util.log_msg.file_name = "unit_test.txt"

    def test_temp_value_with_units(self):
        """Verify function attaches units as expected."""

        for test_case in [44, -1, 101, 2, "13", "-13", None]:
            for precision in [0, 1, 2]:
                for disp_unit in ['F', 'c']:
                    print(f"test case: value={test_case}, precision="
                          f"{precision}, units={disp_unit}")
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
                                     f"test case: {test_case}, expected_val="
                                     f"{expected_val}, actual_val="
                                     f"{actual_val}")

        # test failing case
        with self.assertRaises(ValueError):
            util.temp_value_with_units(-13, "bogus", 1)

    def test_humidity_value_with_units(self):
        """Verify function attaches units as expected."""

        for test_case in [44, -1, 101, 2, "13", "-13", None]:
            for precision in [0, 1, 2]:
                for disp_unit in ['RH']:
                    print(f"test case: value={test_case}, precision="
                          f"{precision}, units={disp_unit}")
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
                                     f"test case: {test_case}, expected_val="
                                     f"{expected_val}, actual_val="
                                     f"{actual_val}")

        # test failing case
        with self.assertRaises(ValueError):
            util.humidity_value_with_units(-13, "bogus", 1)

    def test_c_to_f(self):
        """Verify C to F calculations."""

        # int and float cases
        for tempc in [0, -19, 34, 101, -44.1, None]:
            tempf = util.c_to_f(tempc)
            if tempc is None:
                expected_tempf = None  # pass-thru
            else:
                expected_tempf = tempc * 9.0 / 5 + 32
            self.assertEqual(expected_tempf, tempf, f"test case {tempc}: "
                             f"expected={expected_tempf}, actual={tempf}")

        # verify exception cases
        for tempc in ['0', "", "*"]:
            with self.assertRaises(TypeError):
                tempf = util.c_to_f(tempc)
            # expected_tempf = tempc
            # self.assertEqual(expected_tempf, tempf, "test case %s: "
            #                  "expected=%s, actual=%s" %
            #                  (tempc, expected_tempf, tempf))

    def test_f_to_c(self):
        """Verify F to C calculations."""

        # int and float cases
        for tempf in [0, -19, 34, 101, -44.1, None]:
            tempc = util.f_to_c(tempf)
            if tempf is None:
                expected_tempc = None  # pass-thru
            else:
                expected_tempc = (tempf - 32) * 5 / 9.0
            self.assertEqual(expected_tempc, tempc, f"test case {tempf}: "
                             f"expected={expected_tempc}, actual={tempc}")

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
        super().setUp()
        util.log_msg.file_name = "unit_test.txt"

    def test_get_function_name(self):
        """
        Confirm get_function_name works as expected.
        """
        for test in range(1, 4):
            print(f"get_function_name({test})={util.get_function_name(test)}")

        # default
        test = "<default>"
        print(f"testing util.get_function_name({test})")
        ev_1 = "test_get_function_name"
        result_1 = util.get_function_name()
        print(f"get_function_name({test})={result_1}")
        self.assertEqual(ev_1, result_1, f"expected={ev_1}, actual={result_1}")

        # test 1
        test = 1
        print(f"testing util.get_function_name({test})")
        ev_1 = "test_get_function_name"
        result_1 = util.get_function_name(test)
        print(f"get_function_name({test})={result_1}")
        self.assertEqual(ev_1, result_1, f"test{test}: expected={ev_1}, "
                         f"actual={result_1}")

        # test 2
        test = 2
        print(f"testing util.get_function_name({test})")
        ev_1 = ["patched",  # mock patch decorator
                ]
        result_1 = util.get_function_name(test)
        print(f"get_function_name({test})={result_1}")
        self.assertTrue(result_1 in ev_1, f"test{test}: expected values={ev_1}"
                        f", actual={result_1}")

        # test 3
        test = 3
        print(f"testing util.get_function_name({test})")
        ev_1 = ["run",  # Linux
                "_callTestMethod",  # windows
                ]
        result_1 = util.get_function_name(test)
        print(f"get_function_name({test})={result_1}")
        self.assertTrue(result_1 in ev_1, f"test{test}: expected values={ev_1}"
                        f", actual={result_1}")

    def test_utf8len(self):
        """
        Verify utf8len().
        """
        for test_case in ["A", "BB", "ccc", "dd_d"]:
            print(f"testing util.utf8len({test_case})")
            expected_value = 1 * len(test_case)
            actual_value = util.utf8len(test_case)
            self.assertEqual(expected_value, actual_value,
                             f"expected={expected_value}, "
                             f"actual={actual_value}")

    def test_get_key_from_value(self):
        """Verify get_key_from_value()."""
        test_dict = {'A': 1, 'B': 2, 'C': 1}

        # test keys with distinctvalue, determinant case
        test_case = 2
        expected_val = ['B']
        actual_val = util.get_key_from_value(test_dict, test_case)
        self.assertTrue(actual_val in expected_val,
                        f"test case: {test_case}, expected_val={expected_val},"
                        f" actual_val={actual_val}")

        # test keys with same value, indeterminant case
        test_case = 1
        expected_val = ['A', 'C']
        actual_val = util.get_key_from_value(test_dict, test_case)
        self.assertTrue(actual_val in expected_val,
                        f"test case: {test_case}, expected_val={expected_val},"
                        f" actual_val={actual_val}")

        # test key not found
        with self.assertRaises(KeyError):
            print("attempting to input bad dictionary key, "
                  "expect exception...")
            actual_val = util.get_key_from_value(test_dict, "bogus_value")


class RuntimeParameterTest(utc.RuntimeParameterTest):
    """Generic runtime parameter tests."""

    mod = utc  # module to test
    script = os.path.realpath(__file__)
    bool_val = False
    int_val = 9
    float_val = 8.8
    str_val = "test str"

    # fields for testing, mapped to class variables.
    # (value, field name)
    test_fields = [
        (script, os.path.realpath(__file__)),
        (bool_val, utc.BOOL_FLD),
        (int_val, utc.INT_FLD),
        (float_val, utc.FLOAT_FLD),
        (str_val, utc.STR_FLD),
    ]


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
