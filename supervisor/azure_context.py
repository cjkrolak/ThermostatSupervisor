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

# add test subfolder to path
testdir = currentdir + "\\test"
sys.path.insert(0, testdir)

# add supervisor subfolder to path
srcdir = currentdir + "\\supervisor"
sys.path.insert(0, srcdir)
