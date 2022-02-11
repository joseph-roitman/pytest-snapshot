# This file is required for tox and setuptools-scm<6.2.
from setuptools import setup


setup(
    name='pytest-snapshot',  # This line is only needed to make the Github dependency graph work
    packages=['pytest_snapshot'],  # This line is only needed to make the Github dependency graph work
    use_scm_version={"write_to": "pytest_snapshot/_version.py"},
)
