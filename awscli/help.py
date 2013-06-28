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
from argprocess import ParamShorthand
from bcdoc.clidocs import ReSTDocument
from bcdoc.clidocs import ProviderDocumentEventHandler
from bcdoc.clidocs import ServiceDocumentEventHandler
from bcdoc.clidocs import OperationDocumentEventHandler
import bcdoc.clidocevents
from bcdoc.textwriter import TextWriter
from docutils.core import publish_string

class HelpRenderer(object):

    def render(self, contents):
        pass

class PosixHelpRenderer(HelpRenderer):

    PAGER = 'more'

    def get_pager(self):
        pager = self.PAGER
        if 'MANPAGER' in os.environ:
            pager = os.environ['MANPAGER']
        elif 'PAGER' in os.environ:
            pager = os.environ['PAGER']
        return pager

    def render(self, contents):
        cmdline = ['rst2man.py']
        p2 = Popen(cmdline, stdin=PIPE, stdout=PIPE)
        p2.stdin.write(contents)
        p2.stdin.close()
        cmdline = ['groff', '-man', '-T', 'ascii']
        p3 = Popen(cmdline, stdin=p2.stdout, stdout=PIPE)
        pager = self.get_pager()
        cmdline = [pager]
        p4 = Popen(cmdline, stdin=p3.stdout)
        output = p4.communicate()[0]
        sys.exit(1)


class WindowsHelpRenderer(HelpRenderer):
    
    def render(self, contents):
        text_output = publish_string(contents,
                                     writer=TextWriter())
        sys.stdout.write(text_output.decode('utf-8'))
        sys.exit(1)


def get_renderer():
    if platform.system() == 'Windows':
        return WindowsHelpRenderer()
    else:
        return PosixHelpRenderer()

    
class HelpCommand(object):
    """
    A HelpCommand is created to provide a way to pass state from
    the CLI to any document handlers that may get called to generate
    documentation.

    The HelpCommand contains a ``session`` object, a ``command_table``,
    an ``arg_table``, and it also creates the necessary document
    object to hold the generated documentation.
    """
    
    def __init__(self, session, command_table, arg_table):
        self.session = session
        self.command_table = command_table
        self.arg_table = arg_table
        self.renderer = get_renderer()
        self.doc = ReSTDocument(target='man')

    def __call__(self, args, parsed_globals):
        pass

class ProviderHelpCommand(HelpCommand):
    """Implements top level help command.

    This is what is called when ``aws help`` is run.

    """

    def __init__(self, session, command_table, arg_table,
                 description, synopsis, usage):
        HelpCommand.__init__(self, session, command_table, arg_table)
        self.description = description
        self.synopsis = synopsis
        self.help_usage = usage
        self.provider = self.session.provider

    def __call__(self, args, parsed_globals):
        # Create an event handler for a Provider Document
        event_handler = ProviderDocumentEventHandler()
        # Initialize the handler, which registers all event handlers
        event_handler.initialize(self.session)
        # Now generate all of the events for a Provider document.
        # We pass ourselves along so that we can, in turn, get passed
        # to all event handlers.
        bcdoc.clidocevents.register_events(self.session)
        bcdoc.clidocevents.document_provider(self.session,
                                             help_command=self)
        self.renderer.render(self.doc.fp.getvalue().encode('utf-8'))


class ServiceHelpCommand(HelpCommand):
    """Implements service level help.

    This is the object invoked whenever a service command
    help is implemented, e.g. ``aws ec2 help``.

    """

    def __init__(self, session, service, command_table, arg_table=None):
        """

        :type session: ``botocore.session.Session``
        :param session: A botocore session.

        :type service: ``botocore.service.Service``
        :param service: A botocore service object representing the
            particular service.

        """
        HelpCommand.__init__(self, session, command_table, arg_table)
        self.service = service

    def __call__(self, args, parsed_globals):
        handler = ServiceDocumentEventHandler()
        handler.initialize(self.session)
        bcdoc.clidocevents.register_events(self.session)
        bcdoc.clidocevents.service_document(self.session,
                                            help_command=self)
        self.renderer.render(self.doc.fp.getvalue().encode('utf-8'))


class OperationHelpCommand(HelpCommand):
    """Implements operation level help.

    This is the object invoked whenever help for a service is requested,
    e.g. ``aws ec2 describe-instances help``.

    """

    def __init__(self, session, service, operation, arg_table):
        HelpCommand.__init__(self, session, None, arg_table)
        self.service = service
        self.operation = operation
        self.param_shorthand = ParamShorthand()

    def __call__(self, args, parsed_globals):
        handler = OperationDocumentEventHandler()
        handler.initialize(self.session)
        bcdoc.clidocevents.register_events(self.session)
        bcdoc.clidocevents.document_operation(self.session,
                                              help_command=self)
        self.renderer.render(self.doc.fp.getvalue().encode('utf-8'))


