"""
Unit test module for environment.py.
"""
# built-in imports
import os
import sys
import unittest

# local imports
import thermostatsupervisor
from thermostatsupervisor import emulator_config
from thermostatsupervisor import environment as env
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
        return_val = env.is_interactive_environment()
        self.assertTrue(isinstance(return_val, bool))

    def test_get_env_variable(self):
        """
        Confirm get_env_variable() can retrieve values.
        """
        for env_key in ["GMAIL_USERNAME", "GMAIL_PASSWORD"]:
            buff = env.get_env_variable(env_key)
            print(f"env${env_key}="
                  f"{[buff['value'], '(hidden)']['PASSWORD' in env_key]}")
            self.assertEqual(buff["status"], util.NO_ERROR)
            self.assertGreater(len(buff["value"]), 0)

    def test_load_all_env_variables(self):
        """
        Confirm all env variables can be loaded.
        """
        env.load_all_env_variables()
        print(f"env var dict={env.env_variables}")

    def test_get_local_ip(self):
        """
        Verify get_local_ip().
        """
        return_val = env.get_local_ip()
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
             not env.is_azure_environment()],  # Google wifi router
            ['bogus_host', '192.168.86.145', False],  # bogus host
            ['bogus_host', None, False],  # bogus host without IP
            ['dns.google', '8.8.8.8', True],  # should pass everywhere
        ]

        for test_case in test_cases:
            print(f"testing for '{test_case[0]}' at {test_case[1]}, expect "
                  f"{test_case[2]}")
            result, ip_address = util.is_host_on_local_net(test_case[0],
                                                           test_case[1],
                                                           True)
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
        major_version, minor_version = env.get_python_version()

        # verify major version
        min_major = int(env.MIN_PYTHON_MAJOR_VERSION)
        self.assertTrue(major_version >= min_major,
                        f"python major version ({major_version}) is not gte "
                        f"min required value ({min_major})")

        # verify minor version
        min_minor = int(str(env.MIN_PYTHON_MAJOR_VERSION)[
            str(env.MIN_PYTHON_MAJOR_VERSION).find(".") + 1:])
        self.assertTrue(minor_version >= min_minor,
                        f"python minor version ({minor_version}) is not gte "
                        f"min required value ({min_minor})")

        # error checking invalid input parmeter
        with self.assertRaises(TypeError):
            print("attempting to invalid input parameter type, "
                  "expect exception...")
            env.get_python_version("3", 7)

        # no decimal point
        env.get_python_version(3, None)

        # min value exception
        with self.assertRaises(EnvironmentError):
            print("attempting to verify version gte 99.99, "
                  "expect exception...")
            env.get_python_version(99, 99)

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
        pkg = env.dynamic_module_import(package_name)
        print(f"default thermostat returned package type {type(pkg)}")
        self.assertTrue(isinstance(pkg, object),
                        f"dynamic_module_import() returned type({type(pkg)}),"
                        f" expected an object")
        del sys.modules[package_name]
        del pkg

        # test failing case
        with self.assertRaises(ImportError):
            print("attempting to open bogus package name, expect exception...")
            pkg = env.dynamic_module_import(util.PACKAGE_NAME + "." + "bogus")
            print(f"'bogus' module returned package type {type(pkg)}")
        print("test passed")

    def test_get_parent_path(self):
        """
        Verify get_parent_path().
        """
        return_val = env.get_parent_path(os.getcwd())
        self.assertTrue(isinstance(return_val, str),
                        "get_parent_path() returned '%s' which is not a string")

    def test_get_package_version(self):
        """
        Verify get_package_version().
        """
        pkg = thermostatsupervisor
        return_type = tuple
        return_val = env.get_package_version(pkg)
        self.assertTrue(isinstance(return_val, return_type),
                        f"return_val = {return_val}, expected type "
                        f"{return_type}, actual_type {type(return_val)}")

        # check individual elements
        elements = [
            "major",
            "minor",
            "patch",
            ]
        return_type = int
        for element in elements:
            return_val = env.get_package_version(pkg, element)
            self.assertTrue(isinstance(return_val, return_type),
                            f"element='{element}', return_val = {return_val},"
                            " expected type "
                            f"{return_type}, actual_type {type(return_val)}")


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
