# Build and Release Process

This document outlines the complete process for building and releasing new versions of ThermostatSupervisor.

## Overview

ThermostatSupervisor follows GitFlow branching strategy with automated CI/CD pipelines. The project uses semantic versioning and publishes to both PyPI and Docker Hub.

**New Feature**: The repository now includes **automatic version increment** functionality that prevents version conflicts when merging to main. See [Auto Version Increment Documentation](docs/auto-version-increment.md) for details.

## Prerequisites

- Git access to the repository with push permissions to `develop` and `main` branches
- Python 3.9+ with required dependencies installed
- Access to create GitHub releases
- Familiarity with the project's GitFlow workflow

## Version Management

### Version Storage
The project version is stored in a single location:
- **File**: `thermostatsupervisor/__init__.py`
- **Format**: `__version__ = "X.Y.Z"`
- **Current Version**: Check the file for the latest version

### Version Increment Guidelines
Follow semantic versioning (SemVer):
- **Patch (X.Y.Z+1)**: Bug fixes, documentation updates, minor improvements
- **Minor (X.Y+1.0)**: New features, backwards-compatible API changes
- **Major (X+1.0.0)**: Breaking changes, major architectural updates

## Pre-Release Quality Checks

Before incrementing the version and creating a release, ensure all quality gates pass:

### 1. Code Linting
```bash
# Run flake8 linting (must pass with zero errors)
flake8 --config=setup.cfg .

# Run YAML linting on GitHub workflows
yamllint --config-file .yamllint .github/
```

### 2. Unit and Integration Tests
```bash
# Run comprehensive test suite with coverage
python -m tests.unit_test_coverage

# Verify minimum coverage thresholds are met
# Review coverage report in htmlcov/index.html
```

### 3. Build Verification
```bash
# Verify package builds correctly
python -m build

# Check that setup.py correctly reads version
python setup.py --version
```

### 4. Security Scans
Ensure all GitHub Actions security workflows pass:
- CodeQL Analysis
- Dependency Review
- OSSAR Analysis
- Codacy Security Scan
- Safety Scan

## Release Process

### Step 1: Prepare Release on Develop Branch

1. **Create a feature branch for version increment** (if needed):
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b increment-version-X.Y.Z
   ```

2. **Update the version number**:
   - Edit `thermostatsupervisor/__init__.py`
   - Change `__version__ = "X.Y.Z"` to the new version
   - Example: `__version__ = "1.0.11"`

3. **Run quality checks**:
   ```bash
   # Linting
   flake8 --config=setup.cfg .
   yamllint --config-file .yamllint .github/
   
   # Testing
   python -m tests.unit_test_coverage
   
   # Build verification
   python -m build
   ```

4. **Commit and merge to develop**:
   ```bash
   git add thermostatsupervisor/__init__.py
   git commit -m "increment version to X.Y.Z"
   git push origin increment-version-X.Y.Z
   # Create PR to develop branch and merge
   ```

### Step 2: Merge Develop to Main

1. **Create PR from develop to main**:
   - Ensure all CI/CD checks pass on develop branch
   - Create pull request: `develop` → `main`
   - Include release notes in PR description
   - **Automatic version increment**: If the develop branch version matches main branch version, the system will automatically increment the patch version
   - Wait for all automated checks to pass
   - Merge the PR (use merge commit, not squash)

2. **Verify main branch state**:
   ```bash
   git checkout main
   git pull origin main
   # Verify version in __init__.py is correct
   cat thermostatsupervisor/__init__.py | grep __version__
   ```

### Step 3: Create GitHub Release

1. **Navigate to GitHub Releases**:
   - Go to: https://github.com/cjkrolak/ThermostatSupervisor/releases
   - Click "Create a new release"

2. **Configure Release**:
   - **Tag version**: `vX.Y.Z` (e.g., `v1.0.11`)
   - **Target**: `main` branch
   - **Release title**: `Release vX.Y.Z`
   - **Description**: Include:
     - Summary of changes
     - New features
     - Bug fixes
     - Breaking changes (if any)
     - Migration notes (if applicable)

3. **Publish Release**:
   - Click "Publish release"
   - This triggers the automated CI/CD pipeline

## Automated CI/CD Pipeline

When a GitHub release is published, the following automated processes are triggered:

### Python Package Publishing
- **Workflow**: `.github/workflows/python-publish.yml`
- **Actions**:
  1. Sets up Python environment
  2. Installs dependencies
  3. Builds package using `python -m build`
  4. Publishes to PyPI using stored API token
- **Result**: Package available at https://pypi.org/project/Thermostatsupervisor/

### Docker Image Building
- **Workflow**: `.github/workflows/docker-image.yml`
- **Actions**:
  1. Builds Docker image with version tag
  2. Publishes to Docker Hub
- **Result**: Image available for deployment

### Quality Assurance
All standard CI workflows continue to run:
- Pylint code analysis
- Security scans
- Documentation builds
- Integration tests

## Post-Release Steps

### 1. Verify Release Artifacts

- **PyPI Package**: Check https://pypi.org/project/Thermostatsupervisor/
- **Docker Image**: Verify new version tag is available
- **GitHub Release**: Confirm release is properly tagged and documented

### 2. Update Documentation

- **API Documentation**: Sphinx docs automatically rebuild and deploy
- **README**: Update if new features require documentation changes
- **CHANGELOG**: Consider maintaining a changelog for complex releases

### 3. Communication

- Notify stakeholders of the new release
- Update any deployment documentation if changes affect production systems
- Monitor for issues in the first 24-48 hours post-release

## Troubleshooting

### Common Issues

1. **Version Mismatch**: Ensure `__init__.py` version matches the Git tag
2. **CI/CD Failures**: Check GitHub Actions logs for specific error messages
3. **PyPI Upload Failures**: Verify API token permissions and package metadata
4. **Build Failures**: Ensure all dependencies are properly specified

### Rollback Process

If a release has critical issues:

1. **Immediate**: Create hotfix branch from previous stable release
2. **Fix**: Apply minimal fix and test thoroughly
3. **Release**: Follow expedited release process for patch version
4. **Communicate**: Notify all stakeholders of the issue and resolution

## Development Workflow Integration

### Branch Protection
- `main` branch requires PR with reviews
- All CI checks must pass before merge
- Direct commits to `main` are restricted

### Continuous Integration
Every commit triggers automated:
- Linting (flake8, yamllint)
- Security scanning
- Unit and integration tests
- Code coverage analysis

### Release Schedule
- **Patch releases**: As needed for critical fixes
- **Minor releases**: Monthly or as features are completed
- **Major releases**: Quarterly or for significant architectural changes

## Support and Maintenance

For questions about the release process:
1. Check this documentation
2. Review GitHub Issues for similar questions
3. Create new issue with `release` label if needed

Remember: The release process is designed to maintain high quality and reliability. Never skip quality checks to expedite a release.