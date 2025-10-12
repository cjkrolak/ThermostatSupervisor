### Python Instructions
- Write clear and concise comments for each function.
- Ensure functions have descriptive names and include type hints.
- Provide docstrings following <a href="https://peps.python.org/pep-0257/">PEP 257</a> conventions.
- Use the `typing` module for type annotations (e.g., `List[str]`, `Dict[str, int]`).
- Break down complex functions into smaller, more manageable functions.

### General Instructions
- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Write code with good maintainability practices, including comments on why 
  certain design decisions were made.
- Handle edge cases and write clear exception handling.
- For libraries or external dependencies, mention their usage and purpose in comments.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.

### Code Style and Formatting
- Follow the <a href="https://peps.python.org/pep-0008/">PEP 8</a> style guide for Python.
- Maintain proper indentation (use 4 spaces for each level of indentation).
- **Ensure lines do not exceed 88 characters** (as configured in setup.cfg for 
  black compatibility).
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where appropriate.
- **Ensure blank lines are completely empty** - no trailing whitespace or spaces.
- **Remove all trailing whitespace** from the end of lines.
- **Properly align continuation lines** with the opening parenthesis or bracket.

### Edge Cases and Testing
- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and 
  large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining 
  the test cases.

### Pre-Commit Testing and Validation Requirements
- **MANDATORY**: All changes MUST be thoroughly tested before committing.
- **ZERO tolerance for untested code**: Every change must be validated before commit.
- **Test workflows and scripts locally**: 
  - For shell scripts: Run in a test shell to verify syntax and logic
  - For YAML workflows: Test bash scripts extracted from workflow files
  - For Python code: Run unit tests and verify imports work correctly
- **Iterative testing approach**: Test after each small change, not just at the end
- **Validation checklist before ANY commit**:
  1. Syntax validation (bash -n for scripts, yamllint for YAML, flake8 for Python)
  2. Local execution test (run the actual code/script in isolation)
  3. Integration test (verify it works in context)
  4. Lint verification (flake8, yamllint, etc.)
  5. Review git diff to confirm only intended changes
- **For GitHub Actions workflows specifically**:
  - Extract bash scripts from YAML and test them independently
  - Test with sample environment variables
  - Verify all quotes, escapes, and substitutions work correctly
  - Test JSON payload construction and validate with `python -m json.tool`
- **STOP and test immediately if**:
  - You're modifying shell scripts with complex quoting
  - You're working with JSON construction in bash
  - You're using command substitution `$(...)` or variable expansion
  - You're making changes to GitHub Actions workflows
- **Multiple iterations on same issue = process failure**: If requiring more than 
  2-3 commits to fix an issue, STOP and reassess approach before continuing

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

### Security and Dependency Management Requirements
- **MANDATORY**: All dependency changes MUST pass security scanning before 
  committing.
- **ALWAYS run** security scans using `safety check` to verify no known 
  vulnerabilities in dependencies.
- **ZERO security vulnerabilities policy**: Address ALL security issues before 
  committing - no exceptions.
- **MANDATORY**: Security scanning MUST pass before any GitHub Actions workflows 
  proceed.
- Follow the existing security workflows:
  - `.github/workflows/safety-scan.yml` - Dependency vulnerability scanning
  - `.github/workflows/dependency-review.yml` - Dependency review for PRs
  - `.github/workflows/codacy-analysis.yml` - Code security analysis
  - `.github/workflows/codeql-analysis.yml` - Advanced code security scanning
- Pay special attention to:
  - Never commit secrets, API keys, or credentials to source code
  - Use environment variables for sensitive configuration
  - Regularly update dependencies to address security vulnerabilities
  - Review dependency licenses for compliance requirements
- **Pre-commit security validation**: Always validate security before any 
  automated processes:
  1. Run `safety check` on all dependencies
  2. Verify no secrets are being committed using `git diff`
  3. Ensure environment variables are properly documented in 
     `supervisor-env.txt.example`

### Docker and Containerization Best Practices
- **MANDATORY**: All Docker changes MUST follow security best practices defined 
  in `DOCKER_SECURITY.md`.
- **ALWAYS run** `security_test.sh` to validate Docker security configurations 
  before committing.
- Follow the existing secure Docker configurations:
  - Use `Dockerfile.secure` for production deployments with non-root user
  - Implement health checks for container monitoring
  - Minimize container attack surface by using minimal base images
  - Keep container dependencies up to date for security patches
- Pay special attention to:
  - Never run containers as root user in production
  - Implement proper secrets management for container deployments
  - Use multi-stage builds to reduce final image size
  - Scan container images for vulnerabilities before deployment
- **Pre-commit Docker validation**: Always validate Docker configurations before 
  committing:
  1. Run `security_test.sh` to verify security configurations
  2. Test container builds locally with both standard and secure Dockerfiles
  3. Verify health check endpoints are functional

### Error Handling and Logging Standards
- **Implement consistent error handling patterns** across all modules:
  - Use try-catch blocks for external API calls and file operations
  - Log errors with appropriate severity levels (DEBUG, INFO, WARNING, ERROR, 
    CRITICAL)
  - Include context information in error messages for debugging
  - Handle network timeouts and connection failures gracefully
- **Follow logging best practices**:
  - Use structured logging with consistent format across modules
  - Log to files in `./data/` directory as configured in existing modules
  - Include timestamps, module names, and function names in log entries
  - Avoid logging sensitive information (passwords, API keys, personal data)
- **Exception handling requirements**:
  - Never use bare `except:` clauses - always specify exception types
  - Re-raise exceptions after logging when appropriate
  - Provide meaningful error messages to users while logging technical details
  - Implement circuit breaker patterns for external service dependencies

### Pre-commit Hooks and Automation
- **RECOMMENDED**: Set up pre-commit hooks to automate code quality checks:
  - Install pre-commit: `pip install pre-commit`
  - Configure hooks for flake8, yamllint, safety, and black formatting
  - Run `pre-commit install` to enable automatic checks on commits
- **Automated formatting**: Use black formatter for consistent code style:
  - Configure with `max-line-length = 88` to match project settings
  - Run `.github/workflows/black-reformatter.yml` for automated formatting
- **Git commit message standards**:
  - Use descriptive commit messages that explain the "why" not just the "what"
  - Reference issue numbers when applicable (e.g., "Fix #123: Update API 
    timeout handling")
  - Use conventional commit format when possible (feat:, fix:, docs:, test:, 
    refactor:)

<tool_calling>
You have the capability to call multiple tools in a single response. For maximum efficiency, whenever you need to perform multiple independent operations, ALWAYS invoke all relevant tools simultaneously rather than sequentially. Especially when exploring repository, reading files, viewing directories, validating changes or replying to comments.
</tool_calling>
