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
- Follow the existing flake8 configuration in `setup.cfg` which includes black compatibility settings.
- Pay special attention to:
  - W293: blank line contains whitespace (ensure blank lines are completely empty)
  - W291: trailing whitespace (remove all trailing spaces)
  - E128: continuation line under-indented for visual indent (align with opening parenthesis)
  - E501: line too long (respect max-line-length = 88 from setup.cfg)
- Use `pylint $(git ls-files '*.py')` for additional code quality checks.
- Run flake8 on the entire codebase (`flake8 --config=setup.cfg .`) not just modified files.

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
```