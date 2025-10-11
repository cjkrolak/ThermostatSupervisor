# Azure DevOps Trigger Workflow

## Overview

The `.github/workflows/trigger-ado-tests.yml` workflow solves a critical issue
where the Azure Pipelines action could start and fail before the
`USE_ADO_UNIT_TESTS` environment variable could be checked. This happened when
Azure DevOps account limits were reached.

## Problem Statement

Previously, the `azure-pipelines.yml` file was configured to trigger
automatically on pull requests to the `develop` branch. However, if ADO
account limits were reached, the pipeline would start and fail immediately,
before any code could check whether ADO tests should actually run.

## Solution

A new GitHub Actions workflow checks the `USE_ADO_UNIT_TESTS` repository
variable BEFORE triggering the Azure DevOps pipeline. This prevents
unnecessary pipeline starts and account limit failures.

### Workflow Architecture

```
GitHub PR → trigger-ado-tests.yml → Check USE_ADO_UNIT_TESTS
                                    ↓
                                    If true → Trigger ADO Pipeline via API
                                    ↓
                                    azure-pipelines.yml executes
```

## Configuration

### GitHub Repository Variables

Set in: **Settings** → **Secrets and variables** → **Actions** →
**Variables**

- **Variable Name**: `USE_ADO_UNIT_TESTS`
- **Value**: `true` (to enable) or any other value (to disable)

### GitHub Repository Secrets

Set in: **Settings** → **Secrets and variables** → **Actions** → **Secrets**

- **Secret Name**: `ADO_PAT`
- **Value**: Azure DevOps Personal Access Token
- **Required Scope**: `Build (Read & Execute)`

### Creating an Azure DevOps PAT

1. Go to Azure DevOps → User Settings → Personal Access Tokens
2. Click "New Token"
3. Set appropriate expiration date
4. Select scope: `Build (Read & Execute)`
5. Copy the generated token
6. Add it to GitHub as secret `ADO_PAT`

## Files Modified

### `.github/workflows/trigger-ado-tests.yml` (New)

- Checks `USE_ADO_UNIT_TESTS` variable
- Triggers ADO pipeline via REST API if enabled
- Runs on PR to `develop` branch
- Can be manually triggered via workflow_dispatch

### `.github/azure-pipelines.yml` (Modified)

- Disabled automatic PR triggers (`pr: none`)
- Now only runs when triggered by GitHub workflow
- Updated comments to reflect new trigger mechanism

### `UNIT_TEST_TOGGLE.md` (Updated)

- Added documentation for ADO trigger workflow
- Explained the new `USE_ADO_UNIT_TESTS` variable
- Updated verification instructions

## Benefits

1. **Prevents Account Limit Failures**: Checks configuration before starting
   ADO pipeline
2. **Centralized Control**: All unit test toggles managed in one place
   (GitHub repository variables)
3. **Consistent Pattern**: Matches the approach used in other repositories
   (e.g., fish_recognition)
4. **Better Error Messages**: GitHub workflow provides clear setup
   instructions if configuration is missing

## Testing

Run the unit tests to verify the workflow configuration:

```bash
python -m unittest tests.test_yamllint_workflow -v
```

The tests verify that:
- The workflow file exists
- The workflow passes yamllint validation
- The YAML syntax is correct

## Troubleshooting

### ADO Pipeline Not Triggering

1. Check that `USE_ADO_UNIT_TESTS` is set to `true` in repository variables
2. Verify `ADO_PAT` secret is configured with valid token
3. Check ADO PAT has `Build (Read & Execute)` scope
4. Ensure ADO PAT has not expired

### Authentication Errors

If you see authentication errors in the workflow logs:

1. Verify the `ADO_PAT` secret is set correctly
2. Check that the token has appropriate permissions
3. Ensure the token belongs to a user with access to the ADO project
4. Regenerate the token if it has expired

### Workflow Not Running

1. Check that PR targets the `develop` branch
2. Verify PR includes Python file changes (`.py` files)
3. Check workflow file syntax with yamllint

## References

- Main documentation: `UNIT_TEST_TOGGLE.md`
- Test file: `tests/test_yamllint_workflow.py`
- Similar implementation: github.com/cjkrolak/fish_recognition/pull/1759
