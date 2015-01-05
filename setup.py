#!/usr/bin/env python3
# https://docs.python.org/3.4/distributing/index.html
# https://packaging.python.org/en/latest/distributing.html

from distutils.core import setup
import wfapi

setup(
    name='wfapi',
    url="https://github.com/sigsrv/wfapi",
    author="sigsrv",
    author_email="sigsrv@sigsrv.net",
    version=wfapi.__version__,
    description=wfapi.__doc__.splitlines()[0],
    long_description=wfapi.__doc__, # change later.
    py_modules=['wfapi'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    keywords='workflowy',
)