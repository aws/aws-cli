# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import string
try:
    import fcntl
    import termios
    _have_fcntl = True
except:
    _have_fcntl = False

import struct
import textwrap
from six.moves import html_parser
from six.moves import cStringIO
from .style import CLIStyle


def get_terminal_size():
    try:
        height, width = struct.unpack('hh', fcntl.ioctl(sys.stdout,
                                                        termios.TIOCGWINSZ,
                                                        '1234'))
    except:
        height = 24
        width = 80
    return (height, width)


class HelpParser(html_parser.HTMLParser):
    """
    A simple HTML parser.  Really focused only on
    the subset of HTML that shows up in the documentation strings
    found in the models.
    """

    def __init__(self, doc):
        html_parser.HTMLParser.__init__(self)
        self.doc = doc
        self.unhandled_tags = []

    def handle_starttag(self, tag, attrs):
        handler_name = 'start_%s' % tag
        if hasattr(self.doc.style, handler_name):
            s = getattr(self.doc.style, handler_name)(attrs)
            if s:
                self.doc.get_current_paragraph().write(s)
        else:
            self.unhandled_tags.append(tag)

    def handle_endtag(self, tag):
        handler_name = 'end_%s' % tag
        if hasattr(self.doc.style, handler_name):
            s = getattr(self.doc.style, handler_name)()
            if s:
                self.doc.get_current_paragraph().write(s)

    def handle_data(self, data):
        data = data.replace('\n', '')
        if len(data) == 0:
            return
        space_first = data[0] == ' '
        space_last = data[-1] == ' '
        words = data.split()
        words = self.doc.translate_words(words)
        data = ' '.join(words)
        if space_first:
            if len(data) > 0 and not data[0].isupper():
                data = ' ' + data
        if space_last:
            if len(data) > 0 and data[-1] != '.':
                data = data + ' '
        if len(data) == 0:
            data = ' '
        self.doc.handle_data(data)


class Paragraph(object):

    def __init__(self, doc, width, initial_indent):
        self.doc = doc
        self.width = width
        self.initial_indent = initial_indent
        self.subsequent_indent = initial_indent
        self.lines_before = 0
        self.lines_after = 1
        self.fp = cStringIO()

    def write(self, s):
        self.fp.write(s)

    def wrap(self):
        init_indent = self.doc.style.spaces(self.initial_indent)
        sub_indent = self.doc.style.spaces(self.subsequent_indent)
        s = textwrap.fill(self.fp.getvalue(), self.width,
                          initial_indent=init_indent,
                          subsequent_indent=sub_indent,
                          break_on_hyphens=False)
        return '\n' * self.lines_before + s + '\n' * self.lines_after


class Document(object):

    def __init__(self, session, style_name):
        self.session = session
        if style_name == 'cli':
            self.style = CLIStyle(self, do_ansi=_have_fcntl)
        self.width = get_terminal_size()[1]
        self.help_parser = HelpParser(self)
        self.paragraphs = []
        self.keep_data = True
        self.do_translation = False
        self.initial_indent = 0
        self.subsequent_indent = 0

    def indent(self):
        self.initial_indent += 1

    def dedent(self):
        self.initial_indent -= 1

    def translate_words(self, words):
        return words

    def add_paragraph(self):
        self.paragraphs.append(Paragraph(self, self.width,
                                         self.initial_indent))
        return self.paragraphs[-1]

    def get_current_paragraph(self):
        if len(self.paragraphs) == 0:
            self.add_paragraph(self)
        return self.paragraphs[-1]

    def do_name(self, operation):
        msg = self.session.get_data('messages/Name')
        self.add_paragraph().write(self.style.h2(msg))
        self.indent()
        self.add_paragraph().write(operation.cli_name)
        self.dedent()

    def do_description(self, operation):
        msg = self.session.get_data('messages/Description')
        self.add_paragraph().write(self.style.h2(msg))
        self.indent()
        if operation.documentation:
            self.help_parser.feed(operation.documentation)
        self.dedent()

    def handle_data(self, data):
        if data and self.keep_data:
            paragraph = self.get_current_paragraph()
            paragraph.write(data)

    def render(self, fp):
        for paragraph in self.paragraphs:
            fp.write(paragraph.wrap())

    def build(self, object):
        pass


class OperationDocument(Document):

    def do_parameter(self, parameter, subitem=False):
        if subitem:
            pname = parameter.py_name
        else:
            pname = parameter.cli_name
        para = self.add_paragraph()
        para.write(self.style.bold(pname))
        para.write(' (%s)' % parameter.type)
        self.indent()
        if parameter.documentation:
            self.help_parser.feed(parameter.documentation)
        if parameter.type == 'structure':
            for param in parameter.members:
                self.do_parameter(param, True)
        elif parameter.type == 'list':
            self.do_parameter(parameter.members, True)
        self.dedent()

    def do_parameters(self, operation):
        required = []
        optional = []
        if operation.params:
            required = [p for p in operation.params if p.required]
            optional = [p for p in operation.params if not p.required]
        msg = self.session.get_data('messages/Synopsis')
        self.add_paragraph().write(self.style.h2(msg))
        self.indent()
        self.add_paragraph().write('aws %s %s' % (operation.service.short_name,
                                                  operation.cli_name))
        self.indent()
        for param in required:
            para = self.add_paragraph()
            para.write('%s ' % param.cli_name)
            if param.type != 'boolean':
                para.write(self.style.italics('value'))
        for param in optional:
            para = self.add_paragraph()
            para.write('[%s ' % param.cli_name)
            if param.type != 'boolean':
                para.write(self.style.italics('value'))
            para.write(']')
        self.dedent()
        self.dedent()
        msg = self.session.get_data('messages/RequiredParameters')
        self.add_paragraph().write(self.style.h2(msg))
        self.indent()
        none_msg = self.session.get_data('messages/None')
        for param in required:
            self.do_parameter(param)
        if not required:
            self.add_paragraph().write(none_msg)
        self.dedent()
        msg = self.session.get_data('messages/OptionalParameters')
        self.add_paragraph().write(self.style.h2(msg))
        self.indent()
        for param in optional:
            self.do_parameter(param)
        if not optional:
            self.add_paragraph().write(none_msg)

    def build(self, operation):
        self.do_name(operation)
        self.do_description(operation)
        self.do_parameters(operation)


class ServiceDocument(Document):

    def do_operation_summary(self, operation):
        self.indent()
        self.add_paragraph().write(self.style.bold(operation.cli_name))
        if operation.documentation:
            self.indent()
            self.help_parser.feed(operation.documentation)
            self.dedent()
        self.dedent()

    def build(self, service):
        self.do_name(service)
        self.do_description(service)
        for operation in service.operations:
            self.do_operation_summary(operation)


class ProviderDocument(Document):

    def do_usage(self, title):
        self.add_paragraph().write(self.style.h2('aws'))
        self.indent()
        self.help_parser.feed(title)

    def do_service_names(self, provider_name):
        msg = 'Available services:'
        self.add_paragraph().write(self.style.h2(msg))
        service_data = self.session.get_data('%s/_services' % provider_name)
        for service_name in sorted(service_data):
            self.style.start_li()
            self.get_current_paragraph().write(service_name)
            self.style.end_li()

    def do_options(self, options):
        self.add_paragraph().write(self.style.h2('Options'))
        self.indent()
        for option in options:
            if option.startswith('--'):
                option_data = options[option]
                para = self.add_paragraph()
                para.write(self.style.bold(option))
                if 'metavar' in option_data:
                    para.write(' <%s>' % option_data['metavar'])
                if 'help' in option_data:
                    self.indent()
                    self.add_paragraph().write(option_data['help'])
                    self.dedent()
                if 'choices' in option_data:
                    choices = option_data['choices']
                    if not isinstance(choices, list):
                        choices = self.session.get_data(choices)
                    for choice in sorted(choices):
                        self.style.start_li()
                        self.get_current_paragraph().write(choice)
                        self.style.end_li()
        self.dedent()

    def build(self, provider_name='aws'):
        cli = self.session.get_data('cli')
        self.do_usage(cli['description'])
        self.do_service_names(provider_name)
        self.do_options(cli['options'])


def get_help(session, provider=None,
             service=None, operation=None,
             style='cli', fp=None):
    """
    Return a complete help document for the given object.

    :type style: string
    :param style: The style of help to be generated.  Choices are:
        * cli - help suitable for interactive CLI use
        * rst - help in reST format

    :type fp: file pointer
    :param fp: If you pass in a file pointer, the help document will
        be written to that file pointer.  If ``fp`` is ``None`` (the
        default) the help document will be written to ``sys.stdout``.
    """
    if fp is None:
        fp = sys.stdout
    if provider:
        doc = ProviderDocument(session, style)
        doc.build(provider)
        doc.render(fp)
    if operation:
        doc = OperationDocument(session, style)
        doc.build(operation)
        doc.render(fp)
    elif service:
        doc = ServiceDocument(session, style)
        doc.build(service)
        doc.render(fp)
