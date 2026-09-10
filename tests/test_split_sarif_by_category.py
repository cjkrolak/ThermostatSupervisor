#!/usr/bin/env python3
"""Unit tests for the SARIF split helper script."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src import utilities as util
from tests import unit_test_common as utc


def _load_split_sarif_module():
    """Load the split SARIF helper script as a Python module."""
    script_path = (
        Path(__file__).resolve().parent.parent
        / ".github"
        / "scripts"
        / "split-sarif-by-category.py"
    )
    spec = importlib.util.spec_from_file_location(
        "split_sarif_by_category_script", script_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load script from {script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


split_sarif_by_category = _load_split_sarif_module()


class TestSplitSarifByCategory(utc.UnitTest):
    """Test GitHub Actions output handling for the SARIF split helper."""

    def test_write_github_output_uses_environment_file(self):
        """Test that GitHub step outputs are appended to GITHUB_OUTPUT."""
        with tempfile.NamedTemporaryFile(mode="r+", delete=False) as output_file:
            output_path = output_file.name

        try:
            with patch.dict(os.environ, {"GITHUB_OUTPUT": output_path}, clear=False):
                split_sarif_by_category.write_github_output(
                    "sarif_files", '["results-semgrep.sarif"]'
                )

            with open(output_path, "r", encoding="utf-8") as saved_output:
                self.assertEqual(
                    saved_output.read(),
                    'sarif_files=["results-semgrep.sarif"]\n',
                )
        finally:
            os.unlink(output_path)

    def test_main_avoids_deprecated_set_output_command(self):
        """Test that the script writes outputs without emitting set-output."""
        sarif_data = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "semgrep"}},
                    "results": [{"ruleId": "demo-rule"}],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            sarif_path = Path(temp_dir) / "results.sarif"
            output_path = Path(temp_dir) / "github_output.txt"
            sarif_path.write_text(json.dumps(sarif_data), encoding="utf-8")

            stdout_buffer = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "split-sarif-by-category.py",
                        str(sarif_path),
                        str(Path(temp_dir) / "sarif-output"),
                    ],
                ),
                patch.dict(
                    os.environ, {"GITHUB_OUTPUT": str(output_path)}, clear=False
                ),
                redirect_stdout(stdout_buffer),
            ):
                split_sarif_by_category.main()

            self.assertNotIn("::set-output", stdout_buffer.getvalue())
            self.assertIn(
                "sarif_files=",
                output_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    util.log_msg.debug = True  # type: ignore[attr-defined]
    unittest.main(verbosity=2)
