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
import coverage
import unittest


def main():
    # start the coverage service
    cov = coverage.Coverage()
    cov.start()

    # discover all unit test files in current directory
    print("discovering tests...")
    suite = unittest.TestLoader().discover('.', pattern="test_*.py")

    # run all unit tests
    unittest.TextTestRunner(verbosity=2).run(suite)

    # stop the coverage service and generate reports
    cov.stop()
    cov.report()
    cov.html_report(directory="htmlcov")


if __name__ == "__main__":
    main()
