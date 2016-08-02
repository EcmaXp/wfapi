#!/usr/bin/env python3

import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

WFAPI_NAME = "wfapi"
WFAPI_VERSION = "0.6.0a4"
WFAPI_DESC = "Workflowy's Unoffical API for Python3."

with open("README.rst") as fp:
    WFAPI_DOC = fp.read()


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name=WFAPI_NAME,
    url="https://github.com/ecmaxp/wfapi",
    author="EcmaXp",
    author_email="wfapi@ecmaxp.net",
    version=WFAPI_VERSION,
    description=WFAPI_DOC,
    long_description="\n".join(WFAPI_DOC[1:]),  # change later.
    packages=[
        "wfapi",
        "wfapi.features"
    ],
    tests_require=[
        "pytest",
        "sphinx",
        "sphinx_rtd_theme",
    ],
    cmdclass={
        'test': PyTest,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    keywords='workflowy',
)
