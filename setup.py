# This file is required for tox and setuptools-scm<6.2.
from setuptools import setup


setup(
    use_scm_version={"write_to": "pytest_snapshot/_version.py"},
)
