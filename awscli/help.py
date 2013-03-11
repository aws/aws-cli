# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import sys
import os
import platform


def get_text_path():
    textpath = os.path.split(__file__)[0]
    textpath = os.path.join(textpath, 'doc')
    textpath = os.path.join(textpath, 'text')
    textpath = os.path.join(textpath, 'reference')
    return textpath

def do_text_provider(provider):
    textpath = get_text_path()
    textpath = os.path.join(textpath, 'index.txt')
    fp = open(textpath, 'r')
    sys.stdout.write(fp.read())
    sys.stdout.write('\n')
    fp.close()


def do_text_service(service):
    textpath = get_text_path()
    textpath = os.path.join(textpath, service.cli_name)
    textpath = os.path.join(textpath, 'index.txt')
    fp = open(textpath, 'r')
    sys.stdout.write(fp.read())
    sys.stdout.write('\n')
    fp.close()


def do_text_operation(operation):
    textpath = get_text_path()
    textpath = os.path.join(textpath, operation.service.cli_name)
    textpath = os.path.join(textpath, operation.cli_name + '.txt')
    fp = open(textpath, 'r')
    sys.stdout.write(fp.read())
    sys.stdout.write('\n')
    fp.close()


def do_man(man_page):
    manpath = os.path.split(__file__)[0]
    manpath = os.path.join(manpath, 'doc')
    manpath = os.path.join(manpath, 'man')
    args = ['man', '-M', manpath, man_page]
    sys.stdout.flush()
    sys.stderr.flush()
    os.execvp('man', args)


def get_provider_help(provider='aws'):
    if platform.system() == 'Windows':
        do_text_provider(provider)
    else:
        do_man(provider)


def get_service_help(service):
    if platform.system() == 'Windows':
        do_text_service(service)
    else:
        do_man(service.cli_name)


def get_operation_help(operation):
    if platform.system() == 'Windows':
        do_text_operation(operation)
    else:
        do_man(operation.service.cli_name + '-' + operation.cli_name)
