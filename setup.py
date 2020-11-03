"""Script for creating package."""

from setuptools import setup, find_packages
from dfetch import __version__

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
    install_requires=[
        "PyYAML==5.3.1",
        "coloredlogs==14.0",
        "pykwalify==1.7.0",
        "colorama==0.4.4",
        "typing-extensions==3.7.4.3",
    ],
    entry_points={
        "console_scripts": ["dfetch = dfetch.__main__:main"],
    },
    classifiers=[
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python",
    ],
)
