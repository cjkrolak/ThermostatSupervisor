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
- Ensure lines do not exceed 79 characters.
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where appropriate.

### Edge Cases and Testing
- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.

### Linting and Code Quality
- Ensure linting is passing on each commit before submitting changes.
- Run `flake8 --config=setup.cfg .` to verify code style compliance.
- Address all linting issues before committing code.
- Follow the existing flake8 configuration in `setup.cfg` which includes black compatibility settings.
- Use `pylint $(git ls-files '*.py')` for additional code quality checks.

### Code Coverage Requirements
- Add unit and integration test code coverage on all new code.
- Verify code coverage on existing code where code changes are being made.
- Use `python -m tests.unit_test_coverage` to run tests and generate coverage reports.
- Review coverage reports in `htmlcov/index.html` to identify areas needing more tests.
- Update or enhance test code if coverage is insufficient for modified areas.
- Strive to maintain or improve overall project coverage with each change.

### Documentation and Comments Enhancement
- Verify docstrings and comments on existing code where code changes are being made.
- Update or enhance docstrings and comments if they are outdated or insufficient.
- Ensure all modified functions have proper docstrings following PEP 257 conventions.
- Add explanatory comments for complex logic or algorithmic decisions in modified code.
- Document any changes to function signatures, parameters, or return values.
- Maintain consistency with existing documentation style throughout the codebase.

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