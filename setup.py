#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='pytest-snapshot',
    author='Joseph Roitman',
    author_email='joseph.roitman@gmail.com',
    maintainer='Joseph Roitman',
    maintainer_email='joseph.roitman@gmail.com',
    license='MIT',
    url='https://github.com/joseph-roitman/pytest-snapshot',
    description='A plugin to enable snapshot testing with pytest.',
    long_description=read('README.rst'),
    packages=['pytest_snapshot'],
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    install_requires=[
        'packaging',
        'pytest>=3.0.0',
        'typing',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'pytest11': [
            'snapshot = pytest_snapshot.plugin',
        ],
    },
    use_scm_version={"write_to": "pytest_snapshot/_version.py"},
    setup_requires=["setuptools-scm", "setuptools>=40.0", "wheel"],
)
