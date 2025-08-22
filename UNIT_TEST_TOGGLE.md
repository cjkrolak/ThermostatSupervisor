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

### Disable GitHub Actions Unit Tests (Default)

- Either don't set the `USE_GITHUB_UNIT_TESTS` variable, or
- Set the `USE_GITHUB_UNIT_TESTS` variable to any value other than `true`

When GitHub Actions unit tests are disabled, Azure Pipelines will handle unit testing.

## Unit Test Workflows

### GitHub Actions Workflow
- **File**: `.github/workflows/github-unit-tests.yml`
- **Trigger**: Pull requests to `develop` branch (when enabled)
- **Features**:
  - Python 3.13 testing
  - Flake8 linting
  - Unit test execution with coverage
  - Coverage artifact upload
  - SonarQube integration
  - Environment variable support for integration tests

### Azure DevOps Pipeline
- **File**: `.github/azure-pipelines.yml`
- **Trigger**: Pull requests to `develop` branch (when GitHub Actions disabled)
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
   - If `USE_GITHUB_UNIT_TESTS` is not `true`: Azure Pipeline will run

Only one workflow should execute unit tests for any given PR.