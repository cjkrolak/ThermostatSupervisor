"""
File to automate unit test coverage.

To run all unit tests and compute code coverage:
pip install coverage (one time install)
python unit_test_coverage.py
session window will contain high level coverage report
open /htmlcov/index.html to see the html report.
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
