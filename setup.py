from setuptools import setup

WFAPI_NAME = "wfapi"
WFAPI_VERSION = "0.8.1"
WFAPI_DESC = "Workflowy's Unoffical API for Python 3.6"

with open("README.md") as fp:
    WFAPI_DOC = fp.read()

setup(
    name=WFAPI_NAME,
    url="https://github.com/ecmaxp/wfapi",
    author="EcmaXp",
    author_email="wfapi@ecmaxp.net",
    version=WFAPI_VERSION,
    description=WFAPI_DESC,
    python_requires=">=3.6",
    packages=[
        "wfapi",
    ],
    setup_requires=[
        "pytest-runner",
        "sphinx",
        "sphinx_rtd_theme",
    ],
    tests_require=[
        "pytest",
    ],
    require=[
        "requests",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    keywords='workflowy',
)
