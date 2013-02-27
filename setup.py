#!/usr/bin/env python

"""
distutils/setuptools install script.
"""

import os
import sys
import botocore

try:
    from setuptools import setup
    setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

packages = [
    'botocore',
]

requires = ['requests==1.1.0',
            'six>=1.1.0',
            'jmespath==0.0.1',
            'python-dateutil>=2.1']

setup(
    name='botocore',
    version=botocore.__version__,
    description='Low-level, data-driven core of boto 3.',
    long_description=open('README.md').read(),
    author='Mitch Garnaat',
    author_email='garnaat@amazon.com',
    url='https://github.com/boto/botocore',
    scripts=[],
    packages=packages,
    package_data={'botocore': ['data/*.json', 'data/aws/*.json']},
    package_dir={'botocore': 'botocore'},
    include_package_data=True,
    install_requires=requires,
    license=open("LICENSE.txt").read(),
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
    ),
)
