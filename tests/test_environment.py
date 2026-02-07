"""
Unit test module for environment.py.
"""

# built-in imports
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

# third-party imports

# local imports
import src
from src import emulator_config
from src import environment as env
from src import utilities as util
from tests import unit_test_common as utc


class EnvironmentTests(utc.UnitTest):
    """Test functions related to environment and env variables."""

    def setUp(self):
        super().setUp()
        util.log_msg.file_name = "unit_test.txt"  # type: ignore[attr-defined]

    def test_is_interactive_environment(self):
        """
        Verify is_interactive_environment().
        """
        return_val = env.is_interactive_environment()
        self.assertIsInstance(return_val, bool, "return value is not a boolean")

    def test_get_env_variable_with_default(self):
        """
        Test get_env_variable() with default value parameter.
        """
        # Test with missing variable and default value
        result = env.get_env_variable("NONEXISTENT_VAR", default="default_value")
        self.assertEqual(result["status"], util.NO_ERROR)
        self.assertEqual(result["value"], "default_value")
        self.assertEqual(result["key"], "NONEXISTENT_VAR")

        # Test with missing variable and no default (should fail as before)
        result = env.get_env_variable("NONEXISTENT_VAR")
        self.assertEqual(result["status"], util.ENVIRONMENT_ERROR)
        self.assertIsNone(result["value"])

        # Test with missing password variable and default value
        result = env.get_env_variable("MISSING_PASSWORD", default="secret123")
        self.assertEqual(result["status"], util.NO_ERROR)
        self.assertEqual(result["value"], "secret123")

        # Test with existing environment variable (default should be ignored)
        os.environ["TEST_EXISTING"] = "existing_value"
        try:
            result = env.get_env_variable("TEST_EXISTING", default="default_value")
            self.assertEqual(result["status"], util.NO_ERROR)
            self.assertEqual(result["value"], "existing_value")
        finally:
            del os.environ["TEST_EXISTING"]

    def test_get_flask_limiter_storage_uri(self):
        """
        Test get_flask_limiter_storage_uri() with and without environment variable.
        """
        # Test with no environment variable (should use default)
        result = env.get_flask_limiter_storage_uri()
        self.assertEqual(result, "memory://")

        # Test with environment variable set
        os.environ["FLASK_LIMITER_STORAGE_URI"] = "redis://localhost:6379"
        try:
            result = env.get_flask_limiter_storage_uri()
            self.assertEqual(result, "redis://localhost:6379")
        finally:
            del os.environ["FLASK_LIMITER_STORAGE_URI"]

    def test_get_env_variable_source_tracking(self):
        """
        Test that get_env_variable() properly tracks the source of variables.
        """
        # Test environment variable source
        os.environ["TEST_SOURCE_VAR"] = "from_env"
        try:
            result = env.get_env_variable("TEST_SOURCE_VAR")
            self.assertEqual(result["status"], util.NO_ERROR)
            self.assertEqual(result["value"], "from_env")
            self.assertEqual(result["source"], "environment_variable")
        finally:
            del os.environ["TEST_SOURCE_VAR"]

        # Test default value source
        result = env.get_env_variable("MISSING_VAR", default="default_val")
        self.assertEqual(result["status"], util.NO_ERROR)
        self.assertEqual(result["value"], "default_val")
        self.assertEqual(result["source"], "default")

    def test_get_env_variable_2fa_masking(self):
        """
        Test that 2FA keys are properly masked in get_env_variable().
        """
        # Test that 2FA keys are masked in logs
        os.environ["TEST_2FA"] = "123456"
        try:
            result = env.get_env_variable("TEST_2FA")
            self.assertEqual(result["status"], util.NO_ERROR)
            self.assertEqual(result["value"], "123456")
            # The actual masking is done in logging, not in the return value
        finally:
            del os.environ["TEST_2FA"]

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

    def test_get_env_variable_from_file(self):
        """
        Test get_env_variable() with supervisor-env.txt file.
        """
        # Create temporary directory
        test_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()

        try:
            # Change to test directory
            os.chdir(test_dir)

            # Create supervisor-env.txt file
            env_content = """# Test environment file
TEST_KEY1=test_value1
TEST_KEY2=test_value2
# Comment line
TEST_PASSWORD=secret123

EMPTY_LINE_ABOVE=yes
"""
            with open("supervisor-env.txt", "w", encoding="utf-8") as f:
                f.write(env_content)

            # Test reading from file
            result = env.get_env_variable("TEST_KEY1")
            self.assertEqual(result["status"], util.NO_ERROR)
            self.assertEqual(result["value"], "test_value1")

            result = env.get_env_variable("TEST_KEY2")
            self.assertEqual(result["status"], util.NO_ERROR)
            self.assertEqual(result["value"], "test_value2")

            result = env.get_env_variable("TEST_PASSWORD")
            self.assertEqual(result["status"], util.NO_ERROR)
            self.assertEqual(result["value"], "secret123")

            # Test fallback to environment variable
            os.environ["FALLBACK_TEST"] = "fallback_value"
            result = env.get_env_variable("FALLBACK_TEST")
            self.assertEqual(result["status"], util.NO_ERROR)
            self.assertEqual(result["value"], "fallback_value")

            # Test missing variable
            result = env.get_env_variable("MISSING_VAR")
            self.assertEqual(result["status"], util.ENVIRONMENT_ERROR)

        finally:
            # Cleanup
            os.chdir(original_cwd)
            if "FALLBACK_TEST" in os.environ:
                del os.environ["FALLBACK_TEST"]
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_read_supervisor_env_file_function(self):
        """
        Test the _read_supervisor_env_file() function directly.
        """
        # Create temporary directory
        test_dir = tempfile.mkdtemp()
        original_cwd = os.getcwd()

        try:
            # Change to test directory
            os.chdir(test_dir)

            # Test with no file
            result = env._read_supervisor_env_file()  # type: ignore[attr-defined]
            self.assertEqual(result, {})

            # Test with valid file
            env_content = """# Comment
KEY1=value1
KEY2=value with spaces
# Another comment

KEY3=value3
INVALID_LINE_NO_EQUALS
KEY4=value4=with=equals
"""
            with open("supervisor-env.txt", "w", encoding="utf-8") as f:
                f.write(env_content)

            result = env._read_supervisor_env_file()  # type: ignore[attr-defined]
            expected = {
                "KEY1": "value1",
                "KEY2": "value with spaces",
                "KEY3": "value3",
                "KEY4": "value4=with=equals",
            }
            self.assertEqual(result, expected)

        finally:
            # Cleanup
            os.chdir(original_cwd)
            shutil.rmtree(test_dir, ignore_errors=True)

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
            f"env.is_azure_environment() returned type {type(result)} expected bool",
        )

    def test_is_windows_environment(self):
        """
        Verify is_windows_environment() returns a bool.
        """
        return_val = env.is_windows_environment()
        self.assertIsInstance(return_val, bool, "return value is not a boolean")

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
            env.get_python_version("3", 7)  # type: ignore[arg-type]

        # no decimal point
        env.get_python_version(3, 0)

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
        pkg = src
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
        env.show_package_version(src)

    def test_get_package_path(self):
        """Verify get_package_path()."""
        pkg = src
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

    def test_dynamic_module_import_no_reimport(self):
        """
        Verify dynamic_module_import() doesn't re-import local modules.
        """
        # Create a temporary module for testing
        test_dir = tempfile.mkdtemp()
        test_module_path = os.path.join(test_dir, "test_reuse_module.py")

        try:
            # Create a test module file
            with open(test_module_path, "w", encoding="utf-8") as f:
                f.write(
                    '''"""Test module for import reuse."""
__version__ = "1.0.0"
import_count = 0

def get_import_count():
    global import_count
    import_count += 1
    return import_count
'''
                )

            # First import should print warning
            mod1 = env.dynamic_module_import("test_reuse_module", path=test_dir)
            self.assertIsNotNone(mod1)
            self.assertTrue(hasattr(mod1, "get_import_count"))

            # Check that module is in sys.modules
            self.assertModuleIn("test_reuse_module")

            # Second import should NOT print warning
            initial_path_count = sys.path.count(test_dir)
            mod2 = env.dynamic_module_import("test_reuse_module", path=test_dir)
            final_path_count = sys.path.count(test_dir)

            # Verify the path wasn't added again
            self.assertEqual(
                initial_path_count,
                final_path_count,
                "Path was added to sys.path again during second import",
            )

            # Verify both imports return the same module object
            self.assertIs(mod1, mod2, "Second import returned different module object")

        finally:
            # Clean up
            if "test_reuse_module" in sys.modules:
                del sys.modules["test_reuse_module"]
            while test_dir in sys.path:
                sys.path.remove(test_dir)
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_convert_to_absolute_path(self):
        """Verify convert_to_absolute_path()."""
        # Test with a valid relative path
        relative_path = "some/relative/path"
        absolute_path = env.convert_to_absolute_path(relative_path)
        self.assertTrue(
            os.path.isabs(absolute_path),
            f"convert_to_absolute_path() returned '{absolute_path}' which is not an "
            "absolute path",
        )

        # Test with an empty string
        relative_path = ""
        absolute_path = env.convert_to_absolute_path(relative_path)
        self.assertTrue(
            os.path.isabs(absolute_path),
            f"convert_to_absolute_path() returned '{absolute_path}' which is not an "
            "absolute path",
        )

        # Test with a None input
        with self.assertRaises(TypeError):
            env.convert_to_absolute_path(None)

        # Test with a non-string input
        with self.assertRaises(TypeError):
            env.convert_to_absolute_path(123)

    def test_set_env_variable(self):
        """Test set_env_variable() function."""
        # Test valid cases
        test_key = "TEST_SET_ENV_VAR"
        test_value = "test_value"

        try:
            env.set_env_variable(test_key, test_value)
            self.assertEqual(os.environ[test_key], test_value)

            # Test with integer value
            env.set_env_variable(test_key, 123)
            self.assertEqual(os.environ[test_key], "123")

            # Test with boolean value
            env.set_env_variable(test_key, True)
            self.assertEqual(os.environ[test_key], "True")

        finally:
            if test_key in os.environ:
                del os.environ[test_key]

        # Test error cases
        with self.assertRaises(AttributeError):
            env.set_env_variable(None, "value")

        with self.assertRaises(AttributeError):
            env.set_env_variable("key", None)

        with self.assertRaises(AttributeError):
            env.set_env_variable(123, "value")

    def test_add_package_to_path(self):
        """Test _add_package_to_path() function."""
        # Store original sys.path
        original_path = sys.path.copy()

        try:
            # Test with None package (should do nothing)
            env._add_package_to_path(None)  # type: ignore[attr-defined]
            self.assertEqual(sys.path, original_path)

            # Test with valid package name
            test_pkg = "test_package"
            expected_path = env.get_parent_path(os.getcwd()) + "//" + test_pkg

            with unittest.mock.patch("builtins.print") as mock_print:
                env._add_package_to_path(test_pkg)  # type: ignore[attr-defined]

                # Verify package path was added to front of sys.path
                self.assertEqual(sys.path[0], expected_path)
                mock_print.assert_called_with(
                    f"adding package '{expected_path}' to path..."
                )

            # Test with verbose=True
            with unittest.mock.patch("builtins.print") as mock_print:
                # type: ignore on next line for protected member access
                env._add_package_to_path(  # type: ignore[attr-defined]
                    test_pkg, verbose=True
                )

                # Should print twice - the adding message and the sys.path
                self.assertEqual(mock_print.call_count, 2)

        finally:
            # Restore original sys.path
            sys.path[:] = original_path


if __name__ == "__main__":
    util.log_msg.debug = True  # type: ignore[attr-defined]
    unittest.main(verbosity=2)
