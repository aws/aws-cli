#!/usr/bin/env python

"""
distutils/setuptools install script.
"""

import sys
import botocore

try:
    from setuptools import setup
    setup
except ImportError:
    from distutils.core import setup

packages = [
    'botocore',
]

requires = ['requests==1.2.3',
            'six>=1.1.0',
            'jmespath==0.0.2',
            'python-dateutil>=2.1']

if sys.version_info[:2] == (2, 6):
    # For python2.6 we have a few other dependencies.
    # First we need an ordered dictionary so we use the
    # 2.6 backport.
    requires.append('ordereddict==1.1')
    # Then we need simplejson.  This is because we need
    # a json version that allows us to specify we want to
    # use an ordereddict instead of a normal dict for the
    # JSON objects.  The 2.7 json module has this.  For 2.6
    # we need simplejson.
    requires.append('simplejson==3.3.0')


setup(
    name='botocore',
    version=botocore.__version__,
    description='Low-level, data-driven core of boto 3.',
    long_description=open('README.rst').read(),
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
        'Programming Language :: Python :: 3.3',
    ),
)
