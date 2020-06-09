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


requires = [
    'botocore==2.0.0dev24',
    'colorama>=0.2.5,<0.4.4',
    'docutils>=0.10,<0.16',
    'cryptography>=2.8.0,<=2.9.0',
    's3transfer>=0.3.0,<0.4.0',
    'ruamel.yaml>=0.15.0,<0.16.0',
    # wcwidth 0.2.0 and up do not get copied into
    # the pyinstaller executable.
    'wcwidth<0.2.0',
    'prompt-toolkit>=2.0.0,<3.0.0',
]


setup_options = dict(
    name='awscli',
    version=find_version("awscli", "__init__.py"),
    description='Universal Command Line Environment for AWS.',
    long_description=read('README.rst'),
    author='Amazon Web Services',
    url='http://aws.amazon.com/cli/',
    scripts=['bin/aws', 'bin/aws.cmd', 'bin/aws_legacy_completer',
             'bin/aws_completer', 'bin/aws_zsh_completer.sh',
             'bin/aws_bash_completer'],
    packages=find_packages(exclude=['tests*']),
    install_requires=requires,
    package_data={'awscli': [
        'customizations/wizard/wizards/*/*.yml',
        'data/*.json',
        'data/ac.index',
        'examples/*/*.rst',
        'examples/*/*.txt',
        'examples/*/*/*.txt',
        'examples/*/*/*.rst',
        'topics/*.rst',
        'topics/*.json',
    ]},
    license="Apache License 2.0",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
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
