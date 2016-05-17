# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import os
import platform
import shlex
from subprocess import Popen, PIPE

from docutils.core import publish_string
from docutils.writers import manpage

from botocore.docs.bcdoc import docevents
from botocore.docs.bcdoc.restdoc import ReSTDocument
from botocore.docs.bcdoc.textwriter import TextWriter

from awscli.clidocs import ProviderDocumentEventHandler
from awscli.clidocs import ServiceDocumentEventHandler
from awscli.clidocs import OperationDocumentEventHandler
from awscli.clidocs import TopicListerDocumentEventHandler
from awscli.clidocs import TopicDocumentEventHandler
from awscli.argprocess import ParamShorthandParser
from awscli.argparser import ArgTableArgParser
from awscli.topictags import TopicTagDB
from awscli.utils import ignore_ctrl_c


LOG = logging.getLogger('awscli.help')


class ExecutableNotFoundError(Exception):
    def __init__(self, executable_name):
        super(ExecutableNotFoundError, self).__init__(
            'Could not find executable named "%s"' % executable_name)


def get_renderer():
    """
    Return the appropriate HelpRenderer implementation for the
    current platform.
    """
    if platform.system() == 'Windows':
        return WindowsHelpRenderer()
    else:
        return PosixHelpRenderer()


class PagingHelpRenderer(object):
    """
    Interface for a help renderer.

    The renderer is responsible for displaying the help content on
    a particular platform.

    """

    PAGER = None

    def get_pager_cmdline(self):
        pager = self.PAGER
        if 'MANPAGER' in os.environ:
            pager = os.environ['MANPAGER']
        elif 'PAGER' in os.environ:
            pager = os.environ['PAGER']
        return shlex.split(pager)

    def render(self, contents):
        """
        Each implementation of HelpRenderer must implement this
        render method.
        """
        converted_content = self._convert_doc_content(contents)
        self._send_output_to_pager(converted_content)

    def _send_output_to_pager(self, output):
        cmdline = self.get_pager_cmdline()
        LOG.debug("Running command: %s", cmdline)
        p = self._popen(cmdline, stdin=PIPE)
        p.communicate(input=output)

    def _popen(self, *args, **kwargs):
        return Popen(*args, **kwargs)

    def _convert_doc_content(self, contents):
        return contents


class PosixHelpRenderer(PagingHelpRenderer):
    """
    Render help content on a Posix-like system.  This includes
    Linux and MacOS X.
    """

    PAGER = 'less -R'

    def _convert_doc_content(self, contents):
        man_contents = publish_string(contents, writer=manpage.Writer())
        if not self._exists_on_path('groff'):
            raise ExecutableNotFoundError('groff')
        cmdline = ['groff', '-m', 'man', '-T', 'ascii']
        LOG.debug("Running command: %s", cmdline)
        p3 = self._popen(cmdline, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        groff_output = p3.communicate(input=man_contents)[0]
        return groff_output

    def _send_output_to_pager(self, output):
        cmdline = self.get_pager_cmdline()
        LOG.debug("Running command: %s", cmdline)
        with ignore_ctrl_c():
            # We can't rely on the KeyboardInterrupt from
            # the CLIDriver being caught because when we
            # send the output to a pager it will use various
            # control characters that need to be cleaned
            # up gracefully.  Otherwise if we simply catch
            # the Ctrl-C and exit, it will likely leave the
            # users terminals in a bad state and they'll need
            # to manually run ``reset`` to fix this issue.
            # Ignoring Ctrl-C solves this issue.  It's also
            # the default behavior of less (you can't ctrl-c
            # out of a manpage).
            p = self._popen(cmdline, stdin=PIPE)
            p.communicate(input=output)

    def _exists_on_path(self, name):
        # Since we're only dealing with POSIX systems, we can
        # ignore things like PATHEXT.
        return any([os.path.exists(os.path.join(p, name))
                    for p in os.environ.get('PATH', '').split(os.pathsep)])


class WindowsHelpRenderer(PagingHelpRenderer):
    """Render help content on a Windows platform."""

    PAGER = 'more'

    def _convert_doc_content(self, contents):
        text_output = publish_string(contents,
                                     writer=TextWriter())
        return text_output

    def _popen(self, *args, **kwargs):
        # Also set the shell value to True.  To get any of the
        # piping to a pager to work, we need to use shell=True.
        kwargs['shell'] = True
        return Popen(*args, **kwargs)


class HelpCommand(object):
    """
    HelpCommand Interface
    ---------------------
    A HelpCommand object acts as the interface between objects in the
    CLI (e.g. Providers, Services, Operations, etc.) and the documentation
    system (bcdoc).

    A HelpCommand object wraps the object from the CLI space and provides
    a consistent interface to critical information needed by the
    documentation pipeline such as the object's name, description, etc.

    The HelpCommand object is passed to the component of the
    documentation pipeline that fires documentation events.  It is
    then passed on to each document event handler that has registered
    for the events.

    All HelpCommand objects contain the following attributes:

        + ``session`` - A ``botocore`` ``Session`` object.
        + ``obj`` - The object that is being documented.
        + ``command_table`` - A dict mapping command names to
              callable objects.
        + ``arg_table`` - A dict mapping argument names to callable objects.
        + ``doc`` - A ``Document`` object that is used to collect the
              generated documentation.

    In addition, please note the `properties` defined below which are
    required to allow the object to be used in the document pipeline.

    Implementations of HelpCommand are provided here for Provider,
    Service and Operation objects.  Other implementations for other
    types of objects might be needed for customization in plugins.
    As long as the implementations conform to this basic interface
    it should be possible to pass them to the documentation system
    and generate interactive and static help files.
    """

    EventHandlerClass = None
    """
    Each subclass should define this class variable to point to the
    EventHandler class used by this HelpCommand.
    """

    def __init__(self, session, obj, command_table, arg_table):
        self.session = session
        self.obj = obj
        if command_table is None:
            command_table = {}
        self.command_table = command_table
        if arg_table is None:
            arg_table = {}
        self.arg_table = arg_table
        self._subcommand_table = {}
        self._related_items = []
        self.renderer = get_renderer()
        self.doc = ReSTDocument(target='man')

    @property
    def event_class(self):
        """
        Return the ``event_class`` for this object.

        The ``event_class`` is used by the documentation pipeline
        when generating documentation events.  For the event below::

            doc-title.<event_class>.<name>

        The document pipeline would use this property to determine
        the ``event_class`` value.
        """
        pass

    @property
    def name(self):
        """
        Return the name of the wrapped object.

        This would be called by the document pipeline to determine
        the ``name`` to be inserted into the event, as shown above.
        """
        pass

    @property
    def subcommand_table(self):
        """These are the commands that may follow after the help command"""
        return self._subcommand_table

    @property
    def related_items(self):
        """This is list of items that are related to the help command"""
        return self._related_items

    def __call__(self, args, parsed_globals):
        if args:
            subcommand_parser = ArgTableArgParser({}, self.subcommand_table)
            parsed, remaining = subcommand_parser.parse_known_args(args)
            if getattr(parsed, 'subcommand', None) is not None:
                return self.subcommand_table[parsed.subcommand](remaining,
                                                                parsed_globals)

        # Create an event handler for a Provider Document
        instance = self.EventHandlerClass(self)
        # Now generate all of the events for a Provider document.
        # We pass ourselves along so that we can, in turn, get passed
        # to all event handlers.
        docevents.generate_events(self.session, self)
        self.renderer.render(self.doc.getvalue())
        instance.unregister()


class ProviderHelpCommand(HelpCommand):
    """Implements top level help command.

    This is what is called when ``aws help`` is run.

    """
    EventHandlerClass = ProviderDocumentEventHandler

    def __init__(self, session, command_table, arg_table,
                 description, synopsis, usage):
        HelpCommand.__init__(self, session, None,
                             command_table, arg_table)
        self.description = description
        self.synopsis = synopsis
        self.help_usage = usage
        self._subcommand_table = None
        self._topic_tag_db = None
        self._related_items = ['aws help topics']

    @property
    def event_class(self):
        return 'aws'

    @property
    def name(self):
        return 'aws'

    @property
    def subcommand_table(self):
        if self._subcommand_table is None:
            if self._topic_tag_db is None:
                self._topic_tag_db = TopicTagDB()
            self._topic_tag_db.load_json_index()
            self._subcommand_table = self._create_subcommand_table()
        return self._subcommand_table

    def _create_subcommand_table(self):
        subcommand_table = {}
        # Add the ``aws help topics`` command to the ``topic_table``
        topic_lister_command = TopicListerCommand(self.session)
        subcommand_table['topics'] = topic_lister_command
        topic_names = self._topic_tag_db.get_all_topic_names()

        # Add all of the possible topics to the ``topic_table``
        for topic_name in topic_names:
            topic_help_command = TopicHelpCommand(self.session, topic_name)
            subcommand_table[topic_name] = topic_help_command
        return subcommand_table


class ServiceHelpCommand(HelpCommand):
    """Implements service level help.

    This is the object invoked whenever a service command
    help is implemented, e.g. ``aws ec2 help``.

    """

    EventHandlerClass = ServiceDocumentEventHandler

    def __init__(self, session, obj, command_table, arg_table, name,
                 event_class):
        super(ServiceHelpCommand, self).__init__(session, obj, command_table,
                                                 arg_table)
        self._name = name
        self._event_class = event_class

    @property
    def event_class(self):
        return self._event_class

    @property
    def name(self):
        return self._name


class OperationHelpCommand(HelpCommand):
    """Implements operation level help.

    This is the object invoked whenever help for a service is requested,
    e.g. ``aws ec2 describe-instances help``.

    """
    EventHandlerClass = OperationDocumentEventHandler

    def __init__(self, session, operation_model, arg_table, name,
                 event_class):
        HelpCommand.__init__(self, session, operation_model, None, arg_table)
        self.param_shorthand = ParamShorthandParser()
        self._name = name
        self._event_class = event_class

    @property
    def event_class(self):
        return self._event_class

    @property
    def name(self):
        return self._name


class TopicListerCommand(HelpCommand):
    EventHandlerClass = TopicListerDocumentEventHandler

    def __init__(self, session):
        super(TopicListerCommand, self).__init__(session, None, {}, {})

    @property
    def event_class(self):
        return 'topics'

    @property
    def name(self):
        return 'topics'


class TopicHelpCommand(HelpCommand):
    EventHandlerClass = TopicDocumentEventHandler

    def __init__(self, session, topic_name):
        super(TopicHelpCommand, self).__init__(session, None, {}, {})
        self._topic_name = topic_name

    @property
    def event_class(self):
        return 'topics.' + self.name

    @property
    def name(self):
        return self._topic_name
