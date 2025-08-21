#!/usr/bin/env python3
"""
Unit test for Azure DevOps usage reduction changes.
Tests that workflow configurations are properly set up.
"""

import unittest
import yaml
from pathlib import Path


class TestADOReduction(unittest.TestCase):
    """Test Azure DevOps usage reduction implementation."""

    def setUp(self):
        """Set up test environment."""
        self.repo_root = Path(__file__).parent.parent
        self.sonarqube_workflow = (
            self.repo_root / ".github" / "workflows" / "sonarqube.yml"
        )
        self.azure_pipeline = self.repo_root / ".github" / "azure-pipelines.yml"

    def test_sonarqube_workflow_exists(self):
        """Test that SonarQube workflow file exists."""
        self.assertTrue(
            self.sonarqube_workflow.exists(),
            "SonarQube workflow file should exist",
        )

    def test_azure_pipeline_exists(self):
        """Test that Azure pipeline file exists."""
        self.assertTrue(
            self.azure_pipeline.exists(),
            "Azure pipeline file should exist",
        )

    def test_sonarqube_workflow_supports_pr_trigger(self):
        """Test that SonarQube workflow can be triggered by PRs to develop."""
        with open(self.sonarqube_workflow, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        # Check that on section exists (might be under True key due to comments)
        on_section = content.get("on") or content.get(True)
        self.assertIsNotNone(on_section, "Workflow should have 'on' section")

        # Check that pull_request trigger exists
        self.assertIn(
            "pull_request", on_section, "Workflow should support pull_request"
        )

        # Check that develop branch is included
        pr_config = on_section["pull_request"]
        if isinstance(pr_config, dict) and "branches" in pr_config:
            self.assertIn(
                "develop",
                pr_config["branches"],
                "PR trigger should include develop branch",
            )
        elif isinstance(pr_config, list):
            self.assertIn(
                "develop", pr_config, "PR trigger should include develop branch"
            )

    def test_sonarqube_workflow_maintains_other_triggers(self):
        """Test that SonarQube workflow still supports other triggers."""
        with open(self.sonarqube_workflow, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        # Get the on section (might be under True key due to comments)
        on_section = content.get("on") or content.get(True)
        self.assertIsNotNone(on_section, "Workflow should have 'on' section")

        # Should still support repository_dispatch for Azure DevOps
        self.assertIn(
            "repository_dispatch",
            on_section,
            "Workflow should still support repository_dispatch",
        )

        # Should still support workflow_dispatch for manual triggering
        self.assertIn(
            "workflow_dispatch",
            on_section,
            "Workflow should still support workflow_dispatch",
        )

    def test_azure_pipeline_has_github_actions_check(self):
        """Test that Azure pipeline includes GitHub Actions status check."""
        with open(self.azure_pipeline, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for key phrases that indicate GitHub Actions checking
        self.assertIn(
            "Check GitHub Actions Status",
            content,
            "Pipeline should check GitHub Actions status",
        )
        self.assertIn(
            "THERMOSTATSUPERVISOR_PR",
            content,
            "Pipeline should use GitHub token for checks",
        )
        self.assertIn("check-runs", content, "Pipeline should check GitHub check runs")

    def test_azure_pipeline_has_proper_pr_comment(self):
        """Test that Azure pipeline has updated comments about the changes."""
        with open(self.azure_pipeline, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for updated comment
        self.assertIn(
            "Pipeline will check that GitHub Actions pass",
            content,
            "Pipeline should have comment about checking GitHub Actions",
        )


if __name__ == "__main__":
    unittest.main()
