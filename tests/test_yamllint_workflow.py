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
        self.workflow_file = (
            self.repo_root / ".github" / "workflows" / "yamllint.yml"
        )

    def test_yamllint_config_exists(self):
        """Test that yamllint configuration file exists."""
        self.assertTrue(
            self.yamllint_config.exists(),
            "yamllint configuration file should exist"
        )

    def test_yamllint_workflow_exists(self):
        """Test that yamllint workflow file exists."""
        self.assertTrue(
            self.workflow_file.exists(),
            "yamllint workflow file should exist"
        )

    def test_yamllint_config_is_valid(self):
        """Test that yamllint configuration is valid YAML."""
        result = subprocess.run(
            ["yamllint", "--config-file", str(self.yamllint_config),
             str(self.yamllint_config)],
            cwd=self.repo_root,
            capture_output=True,
            text=True
        )
        self.assertEqual(
            result.returncode, 0,
            f"yamllint config should be valid: {result.stderr}"
        )

    def test_yamllint_workflow_is_valid(self):
        """Test that yamllint workflow file passes its own linting."""
        result = subprocess.run(
            ["yamllint", "--config-file", str(self.yamllint_config),
             str(self.workflow_file)],
            cwd=self.repo_root,
            capture_output=True,
            text=True
        )
        self.assertEqual(
            result.returncode, 0,
            f"yamllint workflow should pass linting: {result.stderr}"
        )

    def test_yamllint_catches_common_issues(self):
        """Test that yamllint catches common formatting issues."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml',
                                         delete=False) as f:
            # Create a YAML file with intentional issues
            f.write("key: value with trailing spaces   \n")
            f.write("another_key: very long line that exceeds the maximum "
                    "line length configured in yamllint config which "
                    "should trigger an error\n")
            f.write("missing_newline_at_end: true")
            temp_file = f.name

        try:
            result = subprocess.run(
                ["yamllint", "--config-file", str(self.yamllint_config),
                 temp_file],
                capture_output=True,
                text=True
            )
            # Should fail due to issues
            self.assertNotEqual(
                result.returncode, 0,
                "yamllint should catch formatting issues"
            )
            # Should report specific issues
            self.assertIn("trailing-spaces", result.stdout)
            self.assertIn("line-length", result.stdout)
            self.assertIn("new-line-at-end-of-file", result.stdout)
        finally:
            os.unlink(temp_file)

    def test_yamllint_command_available(self):
        """Test that yamllint command is available."""
        result = subprocess.run(
            ["yamllint", "--version"],
            capture_output=True,
            text=True
        )
        self.assertEqual(
            result.returncode, 0,
            "yamllint command should be available"
        )


if __name__ == "__main__":
    unittest.main()
