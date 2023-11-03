"""
Sample setup.py file
"""

# built-in libraries
import codecs
import os

# third party libraries
from setuptools import setup

# local imports

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\\n" + fh.read()


def read(rel_path):
    """
    Open and read file.

    inputs:
        rel_path(str): path to file containing version str.
    returns:
        (file pointer): pointer to open file.
    """
    print(f"base path={here}")
    print(f"relative path={rel_path}")
    dir_list = os.listdir(here)
    print(f"files in base path: {dir_list}")
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    """
    Get package version from specified file.

    inputs:
        rel_path(str): path to file containing version str.
    returns:
        (str): version string.
    """
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")


setup(
    version=get_version("thermostatsupervisor/__init__.py"),
)
