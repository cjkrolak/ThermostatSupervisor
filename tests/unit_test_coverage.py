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


def code_coverage_all_tests():
    """
    Run all enabled unit tests and collect code coverage data.
    """
    # start the coverage service
    cov = coverage.Coverage()
    cov.start()

    # run all unit tests
    # defer imports until after coverage service
    # starts so that all imports are included in
    # coverage metric.
    # pylint: disable=import-outside-toplevel
    from tests import unit_test_common as utc  # noqa E402
    try:
        utc.parse_unit_test_runtime_parameters()
        utc.run_all_tests()
    finally:
        # stop the coverage service and generate reports
        cov.stop()
        cov.report()
        cov.html_report(directory="htmlcov")


if __name__ == "__main__":
    code_coverage_all_tests()
