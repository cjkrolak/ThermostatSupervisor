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
            print(
                f"env${env_key}="
                f"{[buff['value'], '(hidden)']['PASSWORD' in env_key]}"
            )
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
        self.assertTrue(
            isinstance(return_val, str),
            "get_local_ip() returned '%s' which is not a string",
        )
        self.assertTrue(
            7 <= len(return_val) <= 15,
            "get_local_ip() returned '%s' which is not between 7 and 15 chars",
        )

    def test_is_azure_environment(self):
        """
        Test is_azure_environment.
        """
        result = env.is_azure_environment()
        print(f"env.is_azure_environment()={result}")
        self.assertTrue(
            isinstance(result, bool),
            "env.is_azure_environment() returned type " f"{type(result)} expected bool",
        )

    def test_is_windows_environment(self):
        """
        Verify is_windows_environment() returns a bool.
        """
        return_val = env.is_windows_environment()
        self.assertTrue(isinstance(return_val, bool))

    def test_is_raspberrypi_environment(self):
        """
        Test is_raspberrypi_environment.
        """
        result = env.is_raspberrypi_environment()
        print(f"env.is_raspberrypi_environment()={result}")
        self.assertTrue(
            isinstance(result, bool),
            "env.is_raspberrypi_environment() returned type "
            f"{type(result)} expected bool",
        )

    def test_get_python_version(self):
        """Verify get_python_version()."""
        major_version, minor_version = env.get_python_version()

        # verify major version
        min_major = int(env.MIN_PYTHON_MAJOR_VERSION)
        self.assertTrue(
            major_version >= min_major,
            f"python major version ({major_version}) is not gte "
            f"min required value ({min_major})",
        )

        # verify minor version
        min_minor = int(
            str(env.MIN_PYTHON_MAJOR_VERSION)[
                str(env.MIN_PYTHON_MAJOR_VERSION).find(".") + 1 :
            ]
        )
        self.assertTrue(
            minor_version >= min_minor,
            f"python minor version ({minor_version}) is not gte "
            f"min required value ({min_minor})",
        )

        # error checking invalid input parameter
        with self.assertRaises(TypeError):
            print("attempting to invalid input parameter type, expect exception...")
            env.get_python_version("3", 7)

        # no decimal point
        env.get_python_version(3, None)

        # min value exception
        with self.assertRaises(EnvironmentError):
            print("attempting to verify version gte 99.99, expect exception...")
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
        self.assertTrue(
            isinstance(pkg, object),
            f"dynamic_module_import() returned type({type(pkg)}),"
            f" expected an object",
        )
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
        self.assertTrue(
            isinstance(return_val, str),
            "get_parent_path() returned '%s' which is not a string",
        )

    def test_get_package_version(self):
        """
        Verify get_package_version().
        """
        pkg = thermostatsupervisor
        return_type = tuple
        return_val = env.get_package_version(pkg)
        self.assertTrue(
            isinstance(return_val, return_type),
            f"return_val = {return_val}, expected type "
            f"{return_type}, actual_type {type(return_val)}",
        )

        # check individual elements
        elements = [
            "major",
            "minor",
            "patch",
        ]
        return_type = int
        for element in elements:
            return_val = env.get_package_version(pkg, element)
            self.assertTrue(
                isinstance(return_val, return_type),
                f"element='{element}', return_val = {return_val},"
                " expected type "
                f"{return_type}, actual_type {type(return_val)}",
            )

    def test_show_package_version(self):
        """Verify show_package_version()."""
        env.show_package_version(thermostatsupervisor)

    def test_get_package_path(self):
        """Verify get_package_path()."""
        pkg = thermostatsupervisor
        return_val = env.get_package_path(pkg)
        self.assertTrue(
            isinstance(return_val, str),
            f"get_package_path() returned '{return_val}' which is not a string",
        )
        self.assertTrue(
            os.path.exists(return_val),
            f"get_package_path() returned '{return_val}' which does not exist",
        )
        self.assertTrue(
            return_val.endswith(".py"),
            f"get_package_path() returned '{return_val}' which is not a .py file",
        )

    def test_convert_to_absolute_path(self):
        """Verify convert_to_absolute_path()."""
        # Test with a valid relative path
        relative_path = "some/relative/path"
        absolute_path = env.convert_to_absolute_path(relative_path)
        self.assertTrue(
            os.path.isabs(absolute_path),
            f"convert_to_absolute_path() returned '{absolute_path}' which is not an "
            "absolute path",)

        # Test with an empty string
        relative_path = ""
        absolute_path = env.convert_to_absolute_path(relative_path)
        self.assertTrue(
            os.path.isabs(absolute_path),
            f"convert_to_absolute_path() returned '{absolute_path}' which is not an "
            "absolute path",)

        # Test with a None input
        with self.assertRaises(TypeError):
            env.convert_to_absolute_path(None)

        # Test with a non-string input
        with self.assertRaises(TypeError):
            env.convert_to_absolute_path(123)


if __name__ == "__main__":
    util.log_msg.debug = True
    unittest.main(verbosity=2)
