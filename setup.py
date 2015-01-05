# https://docs.python.org/3.4/distributing/index.html
# https://packaging.python.org/en/latest/distributing.html

from distutils.core import setup
import wfapi

setup(
    name='wfapi',
    version=wfapi.__version__,
    description=wfapi.__doc__.splitlines()[0],
    py_modules=['wfapi'],
)