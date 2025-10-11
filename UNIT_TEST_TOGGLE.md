# Unit Test Action Toggle

This repository supports two unit testing methods:
1. **Azure Pipelines** (default)
2. **GitHub Actions** (native GitHub resources)

Only one method should be active at a time.

## Toggle Configuration

### Enable GitHub Actions Unit Tests

1. Go to your repository settings
2. Navigate to **Secrets and variables** → **Actions** → **Variables**
3. Add a new repository variable:
   - **Name**: `USE_GITHUB_UNIT_TESTS`
   - **Value**: `true`

When this variable is set to `true`, the GitHub Actions workflow will run unit tests.

### Enable Azure DevOps (ADO) Unit Tests

1. Go to your repository settings
2. Navigate to **Secrets and variables** → **Actions** → **Variables**
3. Add a new repository variable:
   - **Name**: `USE_ADO_UNIT_TESTS`
   - **Value**: `true`
4. Navigate to **Secrets and variables** → **Actions** → **Secrets**
5. Add a new secret:
   - **Name**: `AZURE_DEVOPS_PAT`
   - **Value**: Azure DevOps Personal Access Token with 'Build (Read &
     Execute)' scope

When this variable is set to `true`, the ADO trigger workflow will start the
Azure DevOps pipeline.

### Disable Unit Tests (Default)

- Either don't set the `USE_GITHUB_UNIT_TESTS` or `USE_ADO_UNIT_TESTS`
  variables, or
- Set both variables to any value other than `true`

When both variables are disabled or not set, no unit tests will run
automatically.

## Unit Test Workflows

### GitHub Actions Workflow
- **File**: `.github/workflows/github-unit-tests.yml`
- **Trigger**: Pull requests to `develop` branch (when
  `USE_GITHUB_UNIT_TESTS=true`)
- **Features**:
  - Python 3.13 testing
  - Flake8 linting
  - Unit test execution with coverage
  - Coverage artifact upload
  - SonarQube integration
  - Environment variable support for integration tests

### Azure DevOps Pipeline Trigger Workflow
- **File**: `.github/workflows/trigger-ado-tests.yml`
- **Trigger**: Pull requests to `develop` branch (checks
  `USE_ADO_UNIT_TESTS` variable)
- **Purpose**: Checks if ADO tests should run BEFORE starting the ADO
  pipeline, preventing account limit failures
- **Features**:
  - Checks `USE_ADO_UNIT_TESTS` repository variable
  - Triggers ADO pipeline via Azure DevOps API if enabled
  - Prevents ADO pipeline from auto-starting and failing due to account
    limits

### Azure DevOps Pipeline
- **File**: `.github/azure-pipelines.yml`
- **Trigger**: Triggered by `.github/workflows/trigger-ado-tests.yml` when
  `USE_ADO_UNIT_TESTS=true`
- **Features**:
  - Python 3.13 testing
  - Flake8 linting
  - Unit test execution with coverage
  - Coverage reporting
  - SonarQube integration
  - Environment variable support for integration tests

## Environment Variables

Both workflows support the same environment variables for integration tests:
- `GMAIL_USERNAME`
- `GMAIL_PASSWORD`
- `TCC_USERNAME`
- `TCC_PASSWORD`
- `SHT31_REMOTE_IP_ADDRESS_1`
- `KUMO_USERNAME`
- `KUMO_PASSWORD`
- `BLINK_USERNAME`
- `BLINK_PASSWORD`
- `BLINK_2FA`

## Testing Locally

To run unit tests locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run linting
flake8 --config=setup.cfg .

# Run unit tests with coverage
python -m tests.unit_test_coverage
```

## Verification

To verify which testing method is active:

1. Create a pull request to the `develop` branch
2. Check the workflow runs:
   - If `USE_GITHUB_UNIT_TESTS=true`: GitHub Actions workflow will run
   - If `USE_ADO_UNIT_TESTS=true`: ADO trigger workflow will start the
     Azure Pipeline
   - If both are not `true`: No unit tests will run automatically

Only one workflow should execute unit tests for any given PR.

## Benefits of ADO Trigger Workflow

The new `.github/workflows/trigger-ado-tests.yml` workflow solves a critical
issue where the Azure Pipelines action could start and fail before the
`USE_ADO_UNIT_TESTS` environment variable could be checked. This happened
when ADO account limits were reached. By checking the variable in a GitHub
Action FIRST, we prevent unnecessary ADO pipeline starts and potential
failures.