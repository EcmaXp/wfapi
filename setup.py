#!/usr/bin/env python3
# https://docs.python.org/3.4/distributing/index.html
# https://packaging.python.org/en/latest/distributing.html

from distutils.core import setup
import wfapi

wfapi_doc = wfapi.__doc__.splitlines()

setup(
    name='wfapi',
    url="https://github.com/sigsrv/wfapi",
    author="sigsrv",
    author_email="sigsrv@sigsrv.net",
    version=wfapi.__version__,
    description=wfapi_doc[0],
    long_description="\n".join(wfapi_doc[1:]), # change later.
    py_modules=['wfapi'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.4",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries",
    ],
    keywords='workflowy',
)