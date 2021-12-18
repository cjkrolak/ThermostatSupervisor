"""
File to automate unit test coverage.

dependencies:
pip install coverage (one time install)

to run this module:
from command prompt:  'python unit_test_coverage.py'
or from IDE: 'Run / Run As / 1. Python Run'
note: this module will not run properly as a unit test.

coverage results:
session window will contain high level coverage report
open /htmlcov/index.html to see the html report index.
"""
# built-in imports
import coverage

# local imports
import unit_test_common as utc


def code_coverage_all_tests():
    """
    Run all enabled unit tests and collect code coverage data.
    """
    # start the coverage service
    cov = coverage.Coverage()
    cov.start()

    # run all unit tests
    utc.run_all_tests()

    # stop the coverage service and generate reports
    cov.stop()
    cov.report()
    cov.html_report(directory="htmlcov")


if __name__ == "__main__":
    utc.parse_unit_test_runtime_parameters()
    code_coverage_all_tests()
