from setuptools import setup
from dfetch import __version__

setup(
    name="dfetch",
    version=__version__,
    author="Ben Spoor",
    author_email="dfetch@spoor.cc",
    description="Dependency fetcher",
    keywords="dfetch",
    url="https://github.com/dfetch-org/dfetch",
    packages=['dfetch'],
    package_data={'dfetch':['resources/*.png']},
    install_requires=['pyyaml', 'appdirs', 'coloredlogs', 'pykwalify', 'colorama', 'typing-extensions'],
    entry_points={ 'console_scripts': ['dfetch = dfetch.main:main' ] }
)
