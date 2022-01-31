"""Script for creating package."""

# read the contents of your README file
from os import path

from setuptools import find_packages, setup

from dfetch import __version__

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="dfetch",
    version=__version__,
    author="Ben Spoor",
    author_email="dfetch@spoor.cc",
    description="Dependency fetcher",
    license="MIT",
    keywords="dfetch",
    url="https://github.com/dfetch-org/dfetch",
    packages=find_packages(include=["dfetch", "dfetch.*"]),
    package_data={"dfetch": ["resources/*.yaml"]},
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "PyYAML==6.0",
        "coloredlogs==15.0.1",
        "pykwalify==1.8.0",
        "halo==0.0.31",
        "colorama==0.4.4",
        "typing-extensions==4.0.1; python_version > '3.7'",
        "typing-extensions<4.0,>=3.10; python_version <= '3.7'",
        "sarif-om==1.0.4",
        "semver==2.13.0",
        "patch-ng==1.17.4",
        "importlib-resources==5.4.0; python_version <= '3.7.0'",
        "cyclonedx-python-lib==1.3.0",
        "infer-license==0.0.7",
    ],
    entry_points={
        "console_scripts": ["dfetch = dfetch.__main__:main"],
    },
    classifiers=[
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python",
    ],
)
