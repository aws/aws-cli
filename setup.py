#!/usr/bin/env python
import codecs
import os.path
import re
import sys

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


install_requires = [
    'botocore==1.20.44',
    'docutils>=0.10,<0.16',
    's3transfer>=0.3.0,<0.4.0',
    'PyYAML>=3.10,<5.5',
    'colorama>=0.2.5,<0.4.4',
    'rsa>=3.1.2,<=4.5.0; python_version=="2.7"',
    'rsa>=3.1.2,<4.8; python_version>"2.7"',
]


setup_options = dict(
    name='awscli',
    version=find_version("awscli", "__init__.py"),
    description='Universal Command Line Environment for AWS.',
    long_description=read('README.rst'),
    author='Amazon Web Services',
    url='http://aws.amazon.com/cli/',
    scripts=['bin/aws', 'bin/aws.cmd',
             'bin/aws_completer', 'bin/aws_zsh_completer.sh',
             'bin/aws_bash_completer'],
    packages=find_packages(exclude=['tests*']),
    package_data={'awscli': ['data/*.json', 'examples/*/*.rst',
                             'examples/*/*.txt', 'examples/*/*/*.txt',
                             'examples/*/*/*.rst', 'topics/*.rst',
                             'topics/*.json']},
    install_requires=install_requires,
    extras_require={},
    license="Apache License 2.0",
    python_requires=">= 2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)


if 'py2exe' in sys.argv:
    # This will actually give us a py2exe command.
    import py2exe
    # And we have some py2exe specific options.
    setup_options['options'] = {
        'py2exe': {
            'optimize': 0,
            'skip_archive': True,
            'dll_excludes': ['crypt32.dll'],
            'packages': ['docutils', 'urllib', 'httplib', 'HTMLParser',
                         'awscli', 'ConfigParser', 'xml.etree', 'pipes'],
        }
    }
    setup_options['console'] = ['bin/aws']


setup(**setup_options)
