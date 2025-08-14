```markdown
### Python Instructions
- Write clear and concise comments for each function.
- Ensure functions have descriptive names and include type hints.
- Provide docstrings following [PEP 257](https://peps.python.org/pep-0257/) conventions.
- Use the `typing` module for type annotations (e.g., `List[str]`, `Dict[str, int]`).
- Break down complex functions into smaller, more manageable functions.

### General Instructions
- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Write code with good maintainability practices, including comments on why certain design decisions were made.
- Handle edge cases and write clear exception handling.
- For libraries or external dependencies, mention their usage and purpose in comments.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.

### Code Style and Formatting
- Follow the [PEP 8](https://peps.python.org/pep-0008/) style guide for Python.
- Maintain proper indentation (use 4 spaces for each level of indentation).
- **Ensure lines do not exceed 88 characters** (as configured in setup.cfg for black compatibility).
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where appropriate.
- **Ensure blank lines are completely empty** - no trailing whitespace or spaces.
- **Remove all trailing whitespace** from the end of lines.
- **Properly align continuation lines** with the opening parenthesis or bracket.

### Edge Cases and Testing
- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.

### Linting and Code Quality
- **MANDATORY**: All code changes MUST pass flake8 linting before committing.
- **ALWAYS run** `flake8 --config=setup.cfg .` to verify code style compliance before any commit.
- **ZERO linting errors policy**: Address ALL linting issues before committing code - no exceptions.
- **MANDATORY**: Linting MUST pass before any GitHub Actions workflows are triggered.
- Follow the existing flake8 configuration in `setup.cfg` which includes black compatibility settings.
- Pay special attention to:
  - W293: blank line contains whitespace (ensure blank lines are completely empty)
  - W291: trailing whitespace (remove all trailing spaces)
  - E128: continuation line under-indented for visual indent (align with opening parenthesis)
  - E501: line too long (respect max-line-length = 88 from setup.cfg)
  - F401: imported but unused (remove unused imports)
  - E402: module level import not at top of file (use `# noqa: E402` only when necessary for proper module initialization)
- Use `pylint $(git ls-files '*.py')` for additional code quality checks.
- Run flake8 on the entire codebase (`flake8 --config=setup.cfg .`) not just modified files.
- **Pre-commit validation**: Always validate code style before any automated processes:
  1. Run `flake8 --config=setup.cfg .` on all modified files
  2. Fix ALL linting errors before proceeding with commits
  3. Ensure 100% linting compliance before GitHub Actions execution

### YAML Linting and Formatting Requirements
- **MANDATORY**: All YAML changes MUST pass yamllint before committing.
- **ALWAYS run** `yamllint --config-file .yamllint .github/` to verify YAML compliance before any commit.
- **ZERO yamllint errors policy**: Address ALL yamllint errors before committing - no exceptions.
- **MANDATORY**: YAML linting MUST pass before any other testing or GitHub Actions workflows are started.
- Follow the existing yamllint configuration in `.yamllint` which includes:
  - Line length limit of 88 characters (aligned with Python formatting)
  - No document-start markers (`---`) at the beginning of files
  - Consistent 2-space indentation for YAML structures
  - No trailing whitespace
  - Proper comment indentation aligned with content
- Pay special attention to:
  - Line length: Split long lines using YAML multiline syntax (`>-` or `|`)
  - Comment indentation: Ensure comments are indented to match their content level
  - Trailing spaces: Remove all trailing whitespace from lines
  - Document structure: Do not use `---` document start markers
- **Pre-commit validation for YAML**: Always validate YAML style before any automated processes:
  1. Run `yamllint --config-file .yamllint .github/` on all modified YAML files
  2. Fix ALL yamllint errors and warnings before proceeding with commits
  3. Ensure 100% YAML compliance before any other testing begins

### Code Coverage Requirements
- Add unit and integration test code coverage on all new code.
- Verify code coverage on existing code where code changes are being made.
- Use `python -m tests.unit_test_coverage` to run tests and generate coverage reports.
- Review coverage reports in `htmlcov/index.html` to identify areas needing more tests.
- Update or enhance test code if coverage is insufficient for modified areas.
- Strive to maintain or improve overall project coverage with each change.

### Unit Test Requirements and Failure Handling
- **MANDATORY**: All unit tests MUST pass before committing code changes.
- **ALWAYS run unit tests** using `python -m unittest <test_module>` or `python -m tests.unit_test_coverage` to verify functionality.
- **AUTOMATIC FAILURE ANALYSIS**: When unit tests fail, automatically analyze and fix test failures:
  - Examine the test failure output to understand the root cause
  - Identify whether the issue is in the implementation code or test setup
  - Fix implementation bugs that cause legitimate test failures
  - Update or fix test mocking/setup issues (e.g., import errors, missing dependencies)
  - Handle environment-specific issues (e.g., missing hardware libraries in test environments)
  - Ensure proper test isolation and cleanup
- **Test Environment Compatibility**: Account for differences between production and test environments:
  - Handle missing hardware-specific libraries (e.g., RPi.GPIO, smbus) gracefully in tests
  - Use proper mocking strategies to simulate hardware behavior
  - Ensure tests can run in CI/CD environments without physical hardware dependencies
- **Zero test failures policy**: Address ALL test failures before committing - no exceptions.
- Run a focused test suite on modified code areas before running the full test suite.

### Documentation and Comments Enhancement
- Verify docstrings and comments on existing code where code changes are being made.
- Update or enhance docstrings and comments if they are outdated or insufficient.
- Ensure all modified functions have proper docstrings following PEP 257 conventions.
- Add explanatory comments for complex logic or algorithmic decisions in modified code.
- Document any changes to function signatures, parameters, or return values.
- Maintain consistency with existing documentation style throughout the codebase.

### Git Workflow and Rebasing Instructions
- **Default Rebasing Strategy**: When rebasing feature branches, always rebase from the original base branch that the feature branch was created from.
- **GitFlow Integration**: Following the project's GitFlow process, most feature branches are created from `develop`, so rebasing should typically be done from the latest `develop` branch.
- **Base Branch Identification**: Before rebasing, identify the original base branch (usually `develop` for feature branches, `main` for hotfixes).
- **Override Option**: If the user explicitly specifies a source branch in the rebase request, use that branch instead of the default base branch.
- **Example Commands**:
  - For a feature branch created from `develop`: `git rebase develop` or `git rebase origin/develop`
  - For a hotfix branch created from `main`: `git rebase main` or `git rebase origin/main`
- **Best Practices**:
  - Always fetch the latest changes before rebasing: `git fetch origin`
  - Ensure the target base branch is up to date before rebasing
  - Handle merge conflicts carefully during interactive rebasing
  - Verify that rebased code still passes all tests and linting checks

### Sphinx API Documentation System
- The project uses Sphinx for comprehensive API documentation deployed to GitHub Pages at https://cjkrolak.github.io/ThermostatSupervisor/
- When making changes to API classes or methods, ensure corresponding documentation is updated:
  - Update docstrings in source code to maintain autodoc compatibility
  - Review and update relevant .rst files in the `api/` directory if structural changes are made
  - Ensure new classes or modules are included in the appropriate documentation sections
- Key documentation files that may need updates:
  - `api/thermostat_api.rst` - Main API module documentation
  - `api/thermostat_classes.rst` - Thermostat class specifications and required methods
  - `api/zone_classes.rst` - Zone class methods and functionality
  - `api/overview.rst` - High-level API overview and supported thermostats
  - `index.rst` - Main documentation index and table of contents
- Test documentation builds locally using `make html` before committing changes
- The GitHub Actions workflow `.github/workflows/sphinx.yml` automatically builds and deploys documentation on main branch pushes
- Follow Napoleon extension conventions for Google/NumPy style docstrings to ensure proper parsing
- Maintain intersphinx cross-references to Python and Flask documentation where applicable
```