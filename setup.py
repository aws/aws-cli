#!/usr/bin/env python

"""
distutils/setuptools install script.
"""

import os
import sys
import awscli
import glob

try:
    from setuptools import setup
    setup
except ImportError:
    from distutils.core import setup

def build_package_data():
    text_files = _get_text_files()
    package_data = {
        'awscli': ['data/*.json', 'doc/man/man1/*.1'] + text_files
    }
    return package_data


def _get_text_files():
    filenames = []
    for root, dirs, files in os.walk('awscli/doc/text'):
        for filename in files:
            # Strip off the 'awscli/'
            filenames.append(os.path.join(root, filename)[7:])
    return filenames


packages = [
    'awscli',
]

requires = ['botocore>=0.8.2',
            'six>=1.1.0',
            'colorama==0.2.5',
            'argparse>=1.1']


setup(
    name='awscli',
    version=awscli.__version__,
    description='Universal Command Line Environment for AWS.',
    long_description=open('README.md').read(),
    author='Mitch Garnaat',
    author_email='garnaat@amazon.com',
    url='http://aws.amazon.com/cli/',
    scripts=['bin/aws', 'bin/aws.cmd',
             'bin/aws_completer', 'bin/aws_zsh_completer.sh'],
    packages=packages,
    package_data=build_package_data(),
    package_dir={'awscli': 'awscli'},
    include_package_data=True,
    install_requires=requires,
    license=open("LICENSE.txt").read(),
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
    ),
)
