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
from subprocess import Popen, PIPE


def _runcmd_posix(provider, service=None, operation=None):
    cmdline = ['rstgen', '--provider', provider]
    if service:
        cmdline.append('--service')
        cmdline.append(service)
    if operation:
        cmdline.append('--operation')
        cmdline.append(operation)
    p1 = Popen(cmdline, stdout=PIPE)
    cmdline = ['rst2man.py']
    p2 = Popen(cmdline, stdin=p1.stdout, stdout=PIPE)
    cmdline = ['groff', '-man', '-T', 'ascii']
    p3 = Popen(cmdline, stdin=p2.stdout, stdout=PIPE)
    more = os.environ.get('MORE', 'more')
    cmdline = [more]
    p4 = Popen(cmdline, stdin=p3.stdout)
    output = p4.communicate()[0]
    sys.exit(1)


def _runcmd_windows(provider, service=None, operation=None):
    cmdline = ['rstgen.cmd', '--provider', provider]
    if service:
        cmdline.append('--service')
        cmdline.append(service)
    if operation:
        cmdline.append('--operation')
        cmdline.append(operation)
    p1 = Popen(cmdline)
    output = p1.communicate()[0]
    sys.exit(1)


def runcmd(provider, service=None, operation=None):
    if True or platform.system() == 'Windows':
        _runcmd_windows(provider, service, operation)
    else:
        _runcmd_posix(provider, service, operation)

def get_provider_help(session):
    provider = session.get_variable('provider')
    runcmd(provider)


def get_service_help(session, service):
    provider = session.get_variable('provider')
    runcmd(provider, service=service.cli_name)


def get_operation_help(session, service, operation):
    provider = session.get_variable('provider')
    runcmd(provider, service=service.cli_name, operation=operation.cli_name)
