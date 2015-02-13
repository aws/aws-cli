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

import bcdoc.docevents
from bcdoc.restdoc import ReSTDocument
from bcdoc.textwriter import TextWriter

from awscli.clidocs import ProviderDocumentEventHandler
from awscli.clidocs import ServiceDocumentEventHandler
from awscli.clidocs import OperationDocumentEventHandler
from awscli.clidocs import TopicListerDocumentEventHandler
from awscli.clidocs import TopicDocumentEventHandler
from awscli.argprocess import ParamShorthand
from awscli.argparser import ArgTableArgParser
from awscli.topictags import TopicTagDB


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
        cmdline = ['groff', '-man', '-T', 'ascii']
        LOG.debug("Running command: %s", cmdline)
        p3 = self._popen(cmdline, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        groff_output = p3.communicate(input=man_contents)[0]
        return groff_output

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
        self.related_items = []
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

    def __call__(self, args, parsed_globals):
        # Create an event handler for a Provider Document
        instance = self.EventHandlerClass(self)
        # Now generate all of the events for a Provider document.
        # We pass ourselves along so that we can, in turn, get passed
        # to all event handlers.
        bcdoc.docevents.generate_events(self.session, self)
        self.renderer.render(self.doc.getvalue())
        instance.unregister()


class ProviderHelpCommand(HelpCommand):
    """Implements top level help command.

    This is what is called when ``aws help`` is run.

    """
    EventHandlerClass = ProviderDocumentEventHandler

    def __init__(self, session, command_table, arg_table,
                 description, synopsis, usage):
        HelpCommand.__init__(self, session, session.provider,
                             command_table, arg_table)
        self.description = description
        self.synopsis = synopsis
        self.help_usage = usage
        self._topic_table = None
        self._topic_tag_db = None

    @property
    def event_class(self):
        return 'aws'

    @property
    def name(self):
        return self.obj.name

    @property
    def topic_table(self):
        if self._topic_table is None:
            if self._topic_tag_db is None:
                self._topic_tag_db = TopicTagDB()
            self._topic_tag_db.load_json_index()
            self._topic_table = self._create_topic_table()
        return self._topic_table

    def _create_topic_table(self):
        topic_table = {}
        # Add the ``aws help topics`` command to the ``topic_table``
        topic_lister_command = TopicListerCommand(
            self.session, self._topic_tag_db)
        topic_table['topics'] = topic_lister_command
        topic_names = self._topic_tag_db.get_all_topic_names()

        # Add all of the possible topics to the ``topic_table``
        for topic_name in topic_names:
            topic_help_command = TopicHelpCommand(
                self.session, topic_name, self._topic_tag_db)
            topic_table[topic_name] = topic_help_command
        return topic_table

    def __call__(self, args, parsed_globals):
        if args:
            topic_parser = ArgTableArgParser({}, self.topic_table)
            parsed_topic, remaining = topic_parser.parse_known_args(args)
            self.topic_table[parsed_topic.subcommand].__call__(
                args, parsed_globals)
        else:
            super(ProviderHelpCommand, self).__call__(args, parsed_globals)


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
        self.param_shorthand = ParamShorthand()
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

    DESCRIPTION = (
        'This is the AWS CLI Topic Guide. It gives access to a set '
        'of topics that provide a deeper understanding of the CLI. To access '
        'the list of topics from the command line, run ``aws help topics``. '
        'To access a specific topic from the command line, run '
        '``aws help [topicname]``, where ``topicname`` is the name of the '
        'topic as it appears in the output from ``aws help topics``.')

    def __init__(self, session, topic_tag_db):
        super(TopicListerCommand, self).__init__(session, None, {}, {})
        self._topic_tag_db = topic_tag_db
        self._categories = None
        self._entries = None

    @property
    def event_class(self):
        return 'topics'

    @property
    def name(self):
        return 'topics'

    @property
    def title(self):
        return 'AWS CLI Topic Guide'

    @property
    def description(self):
        return self.DESCRIPTION

    @property
    def categories(self):
        """
        :returns: A dictionary where the keys are all of the possible
            topic categories and the values are all of the topics that
            are grouped in that category
        """
        if self._categories is None:
            self._categories = self._topic_tag_db.query('category')
        return self._categories

    @property
    def topic_names(self):
        """
        :returns: A list of all of the topic names.
        """
        return self._topic_tag_db.get_all_topic_names()

    @property
    def entries(self):
        """
        :returns: A dictionary where the keys are the names of all topics
            and the values are the respective entries that appears in the
            catagory that a topic belongs to
        """
        if self._entries is None:
            topic_entry_template = '`%s <%s.html>`_: %s'
            topic_entries = {}
            for topic_name in self.topic_names:
                # Get the description of the topic.
                sentence_description = self._topic_tag_db.get_tag_single_value(
                    topic_name, 'description')
                # Create the full entry description.
                full_description = topic_entry_template % (
                    topic_name, topic_name, sentence_description)
                # Add the entry to the dictionary.
                topic_entries[topic_name] = full_description
            self._entries = topic_entries
        return self._entries


class TopicHelpCommand(HelpCommand):
    EventHandlerClass = TopicDocumentEventHandler

    def __init__(self, session, topic_name, topic_tag_db):
        super(TopicHelpCommand, self).__init__(session, None, {}, {})
        self._topic_tag_db = topic_tag_db
        self._topic_name = topic_name
        self._contents = None

    @property
    def event_class(self):
        return 'topic'

    @property
    def name(self):
        return self._topic_name

    @property
    def title(self):
        return self._topic_tag_db.get_tag_single_value(
            self._topic_name, 'title')

    @property
    def contents(self):
        """
        :returns: The contents of the topic source file with all of its tags
            excluded.
        """
        if self._contents is None:
            topic_filename = os.path.join(self._topic_tag_db.topic_dir,
                                          self.name+'.rst')
            self._contents = self._remove_tags_from_content(topic_filename)
        return self._contents

    def _remove_tags_from_content(self, filename):
        with open(filename, 'r') as f:
            lines = f.readlines()

        content_begin_index = 0
        for i, line in enumerate(lines):
            # If a line is encountered that does not begin with the tag
            # end the search for tags and mark where tags end.
            if not self._line_has_tag(line):
                content_begin_index = i
                break

        # Join all of the non-tagged lines back together.
        return ''.join(lines[i:])

    def _line_has_tag(self, line):
        for tag in self._topic_tag_db.valid_tags:
            if line.startswith(':'+tag+':'):
                return True
        return False
