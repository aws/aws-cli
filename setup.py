#!/usr/bin/env python
import os
import sys

from setuptools import setup, find_packages

import awscli


requires = ['botocore>=0.16.0,<0.17.0',
            'bcdoc>=0.8.0,<0.9.0',
            'six>=1.1.0',
            'colorama==0.2.5',
            'argparse>=1.1',
            'docutils>=0.10',
            'rsa==3.1.1']


setup_options = dict(
    name='awscli',
    version=awscli.__version__,
    description='Universal Command Line Environment for AWS.',
    long_description=open('README.rst').read(),
    author='Mitch Garnaat',
    author_email='garnaat@amazon.com',
    url='http://aws.amazon.com/cli/',
    scripts=['bin/aws', 'bin/aws.cmd',
             'bin/aws_completer', 'bin/aws_zsh_completer.sh'],
    packages=find_packages('.', exclude=['tests*']),
    package_dir={'awscli': 'awscli'},
    package_data={'awscli': ['data/*.json', 'examples/*/*']},
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
        'Programming Language :: Python :: 3.3',
    ),
)

if 'py2exe' in sys.argv:
    # This will actually give us a py2exe command.
    import py2exe
    # And we have some py2exe specific options.
    setup_options['options'] = {
        'py2exe': {
            'optimize': 0,
            'skip_archive': True,
            'includes': ['ConfigParser', 'urllib', 'httplib',
                         'docutils.readers.standalone',
                         'docutils.parsers.rst',
                         'docutils.languages.en',
                         'xml.etree.ElementTree', 'HTMLParser',
                         'awscli.handlers'],
        }
    }
    setup_options['console'] = ['bin/aws']


setup(**setup_options)
