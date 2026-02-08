# Automatic Version Increment Feature

## Overview

The ThermostatSupervisor repository now includes an automatic version increment feature that ensures unique version numbers when merging pull requests into the main branch. This prevents PyPI build failures caused by duplicate version numbers.

## How It Works

When a pull request is opened targeting the main branch, the system:

1. **Compares versions** between the main branch and the PR source branch
2. **Automatically increments** the patch version if they are identical
3. **Commits the change** back to the PR branch
4. **Continues with normal** PR review and merge process

## Files Added

### `.github/workflows/auto-version-increment.yml`
GitHub Actions workflow that triggers on pull requests to main branch and orchestrates the version checking process.

### `.github/scripts/version_increment.py` 
Python script that handles the core logic:
- Version extraction from `src/__init__.py`
- Comparison with main branch version
- Semantic version increment (patch level)
- File updating and git operations

### `tests/test_version_increment.py`
Comprehensive unit tests covering all aspects of the version increment functionality.

## Usage

The feature works automatically - no manual intervention required. However, the script can be run manually for testing:

```bash
# Dry run to see what would happen
python .github/scripts/version_increment.py --dry-run

# Actually increment version if needed
python .github/scripts/version_increment.py --commit
```

## Version Increment Rules

- **Patch increment only**: Currently increments the patch version (X.Y.Z → X.Y.Z+1)
- **Triggered when**: Source branch version equals main branch version
- **Semantic versioning**: Follows standard semantic versioning practices
- **Preserves format**: Maintains original quote style and formatting

## Examples

| Main Branch | PR Branch | Action | Result |
|-------------|-----------|--------|---------|
| 1.0.9 | 1.0.9 | Increment | 1.0.10 |
| 1.0.9 | 1.0.12 | None | 1.0.12 |
| 1.0.9 | 1.0.8 | Warning | 1.0.8 (with warning) |

## Error Handling

The system gracefully handles:
- Missing main branch references
- Invalid version formats
- File access issues
- Git operation failures
- Network connectivity problems

## Testing

Run the comprehensive test suite:

```bash
python -m unittest tests.test_version_increment -v
```

The tests cover:
- Version extraction and parsing
- File operations
- Error conditions
- Integration scenarios

## Integration with Existing Workflow

This feature integrates seamlessly with the existing GitFlow process:

1. Developer creates feature branch
2. Opens PR to main branch
3. **Auto-increment runs** (if needed)
4. Normal CI/CD checks continue
5. PR gets reviewed and merged
6. Release process continues as usual

## Troubleshooting

### Common Issues

**Script fails to fetch main branch:**
- Ensure git repository has origin remote configured
- Check network connectivity
- Verify GitHub permissions

**Version not being incremented:**
- Check that versions are actually identical
- Ensure script has write permissions
- Verify file path is correct

**Linting failures:**
- Run `flake8 --config=setup.cfg .github/scripts/version_increment.py`
- Run `yamllint --config-file .yamllint .github/workflows/auto-version-increment.yml`

### Manual Override

If manual version control is needed, simply update the version in your PR branch before opening the PR, ensuring it's different from the main branch version.

## Benefits

- **Prevents build failures** from duplicate versions
- **Maintains release pipeline** integrity  
- **Reduces manual errors** in version management
- **Supports semantic versioning** best practices
- **Fully automated** - no developer intervention needed
- **Well tested** with comprehensive test coverage