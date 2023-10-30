"""
Sample setup.py file
"""

# built-in libraries
import codecs
import os

# third party libraries
from setuptools import setup, find_packages


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
    name="Thermostatsupervisor",
    version=get_version("thermostatsupervisor/__init__.py"),
    author="Christopher Krolak",
    author_email="cjkrolak@mail.com",
    description="supervisor to detect and correct thermostat deviations",
    url="https://github.com/cjkrolak/Thermostatsupervisor",
    long_description_content_type="text/markdown",
    long_description=long_description,
    license="MIT",
    packages=find_packages(),
    python_requires='>=3',
    install_requires=["dnspython", "munch", "psutil"],
    keywords=["thermostat", "automation", "supervise"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Environment :: Console",
        "Framework :: Flask",
        "Framework :: IDLE",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Home Automation",
    ]
)
