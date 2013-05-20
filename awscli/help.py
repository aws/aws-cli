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
import six
from awscli import rstgen


PAGER = 'more'


def get_pager():
    pager = PAGER
    if 'MANPAGER' in os.environ:
        pager = os.environ['MANPAGER']
    elif 'PAGER' in os.environ:
        pager = os.environ['PAGER']
    return pager


def _render_docs_posix(rst_contents):
    cmdline = ['rst2man.py']
    p2 = Popen(cmdline, stdin=PIPE, stdout=PIPE)
    p2.stdin.write(rst_contents.getvalue())
    p2.stdin.close()
    cmdline = ['groff', '-man', '-T', 'ascii']
    p3 = Popen(cmdline, stdin=p2.stdout, stdout=PIPE)
    pager = get_pager()
    cmdline = [pager]
    p4 = Popen(cmdline, stdin=p3.stdout)
    output = p4.communicate()[0]
    sys.exit(1)


def _render_docs_windows(rst_contents):
    sys.stdout.write(rst_contents.getvalue())
    sys.exit(1)


def render_docs(rst_contents):
    if platform.system() == 'Windows':
        _render_docs_windows(rst_contents)
    else:
        _render_docs_posix(rst_contents)


def get_provider_help(session):
    provider = session.get_variable('provider')
    cli_data = rstgen.get_cli_data(session, provider)
    rst_contents = six.StringIO()
    rstgen.gen_man(session, provider=provider, cli_data=cli_data,
                   fp=rst_contents)
    render_docs(rst_contents)


def get_service_help(session, service):
    rst_contents = six.StringIO()
    rstgen.gen_man(session, service=service, fp=rst_contents)
    render_docs(rst_contents)


def get_operation_help(session, service, operation):
    rst_contents = six.StringIO()
    rstgen.gen_man(session, operation=operation, fp=rst_contents)
    render_docs(rst_contents)
