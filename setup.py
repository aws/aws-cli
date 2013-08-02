#!/usr/bin/env python

"""
distutils/setuptools install script.
"""

import os
import awscli

try:
    from setuptools import setup
    setup
except ImportError:
    from distutils.core import setup


def _get_example_files():
    filenames = []
    for root, dirs, files in os.walk('doc/source/examples'):
        for filename in files:
            filenames.append(os.path.join(root, filename))
    return filenames


def get_data_files():
    return [('awscli/examples', _get_example_files())]

packages = [
    'awscli',
    'awscli.customizations',
    'awscli.customizations.S3Plugin'
]

requires = ['botocore>=0.14.0,<0.15.0',
            'bcdoc>=0.6.0,<0.7.0',
            'six>=1.1.0',
            'colorama==0.2.5',
            'argparse>=1.1',
            'docutils>=0.10',
            'rsa==3.1.1']


setup(
    name='awscli',
    version=awscli.__version__,
    description='Universal Command Line Environment for AWS.',
    long_description=open('README.rst').read(),
    author='Mitch Garnaat',
    author_email='garnaat@amazon.com',
    url='http://aws.amazon.com/cli/',
    scripts=['bin/aws', 'bin/aws.cmd',
             'bin/aws_completer', 'bin/aws_zsh_completer.sh'],
    packages=packages,
    package_dir={'awscli': 'awscli'},
    package_data={'awscli': ['data/*.json']},
    data_files=get_data_files(),
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
