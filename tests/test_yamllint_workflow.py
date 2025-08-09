#!/usr/bin/env python3
"""
Unit test for YAML linting CI workflow validation.
Tests that yamllint configuration works and catches common YAML issues.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestYamlLintWorkflow(unittest.TestCase):
    """Test YAML linting workflow functionality."""

    def setUp(self):
        """Set up test environment."""
        self.repo_root = Path(__file__).parent.parent
        self.yamllint_config = self.repo_root / ".yamllint"
        self.yamllint_workflow = (
            self.repo_root / ".github" / "workflows" / "yamllint.yml"
        )
        self.yaml_formatter_workflow = (
            self.repo_root / ".github" / "workflows" / "yaml-formatter.yml"
        )

    def test_yamllint_config_exists(self):
        """Test that yamllint configuration file exists."""
        self.assertTrue(
            self.yamllint_config.exists(), "yamllint configuration file should exist"
        )

    def test_yamllint_workflow_exists(self):
        """Test that yamllint workflow file exists."""
        self.assertTrue(
            self.yamllint_workflow.exists(), "yamllint workflow file should exist"
        )

    def test_yaml_formatter_workflow_exists(self):
        """Test that yaml-formatter workflow file exists."""
        self.assertTrue(
            self.yaml_formatter_workflow.exists(),
            "yaml-formatter workflow file should exist",
        )

    def test_yamllint_config_is_valid(self):
        """Test that yamllint configuration is valid YAML."""
        result = subprocess.run(
            [
                "yamllint",
                "--config-file",
                str(self.yamllint_config),
                str(self.yamllint_config),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, f"yamllint config should be valid: {result.stderr}"
        )

    def test_yamllint_workflow_is_valid(self):
        """Test that yamllint workflow file passes its own linting."""
        result = subprocess.run(
            [
                "yamllint",
                "--config-file",
                str(self.yamllint_config),
                str(self.yamllint_workflow),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"yamllint workflow should pass linting: {result.stderr}",
        )

    def test_yaml_formatter_workflow_is_valid(self):
        """Test that yaml-formatter workflow file passes its own linting."""
        result = subprocess.run(
            [
                "yamllint",
                "--config-file",
                str(self.yamllint_config),
                str(self.yaml_formatter_workflow),
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"yaml-formatter workflow should pass linting: {result.stderr}",
        )

    def test_yamllint_catches_common_issues(self):
        """Test that yamllint catches common formatting issues."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            # Create a YAML file with intentional issues
            f.write("key: value with trailing spaces   \n")
            f.write(
                "another_key: very long line that exceeds the maximum "
                "line length configured in yamllint config which "
                "should trigger an error\n"
            )
            f.write("missing_newline_at_end: true")
            temp_file = f.name

        try:
            result = subprocess.run(
                ["yamllint", "--config-file", str(self.yamllint_config), temp_file],
                capture_output=True,
                text=True,
            )
            # Should fail due to issues
            self.assertNotEqual(
                result.returncode, 0, "yamllint should catch formatting issues"
            )
            # Should report specific issues
            self.assertIn("trailing-spaces", result.stdout)
            self.assertIn("line-length", result.stdout)
            self.assertIn("new-line-at-end-of-file", result.stdout)
        finally:
            os.unlink(temp_file)

    def test_yamlfix_command_available(self):
        """Test that yamlfix command is available."""
        result = subprocess.run(
            ["yamlfix", "--version"], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, "yamlfix command should be available")

    def test_yamlfix_can_fix_issues(self):
        """Test that yamlfix can fix common YAML formatting issues."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            # Create a YAML file with issues that yamlfix can fix
            f.write("version: 2\n")
            f.write("jobs:\n")
            f.write("  build:\n")
            f.write("    runs-on: ubuntu-latest")  # missing newline
            temp_file = f.name

        try:
            # Check that yamlfix detects issues
            check_result = subprocess.run(
                ["yamlfix", "--check", temp_file], capture_output=True, text=True
            )
            self.assertNotEqual(
                check_result.returncode, 0, "yamlfix should detect formatting issues"
            )

            # Apply fixes
            fix_result = subprocess.run(
                ["yamlfix", temp_file], capture_output=True, text=True
            )
            self.assertEqual(
                fix_result.returncode,
                0,
                f"yamlfix should fix issues: {fix_result.stderr}",
            )

            # Verify file was fixed
            verify_result = subprocess.run(
                ["yamlfix", "--check", temp_file], capture_output=True, text=True
            )
            self.assertEqual(
                verify_result.returncode,
                0,
                "yamlfix should report no issues after fixing",
            )
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    unittest.main()
