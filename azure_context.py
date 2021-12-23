"""
Test environment settings.

This file should be imported by all test modules so that local imports
in the parent directory can be found.
"""
# built-in imports
import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
testdir = currentdir + "\tests"
print(testdir)
sys.path.insert(0, testdir)
