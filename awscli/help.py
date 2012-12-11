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
    pass
import struct
import textwrap
from six.moves import html_parser
from six.moves import cStringIO
from botocore import BotoCoreObject, ScalarTypes
from botocore.service import Service
from botocore.base import get_data


def get_terminal_size():
    try:
        height, width = struct.unpack('hh', fcntl.ioctl(sys.stdout,
                                                        termios.TIOCGWINSZ,
                                                        '1234'))
    except:
        height = 24
        width = 80
    return (height, width)

class CLIHTMLParser(html_parser.HTMLParser):

    def __init__(self, doc_string, use_ansi_codes):
        html_parser.HTMLParser.__init__(self)
        self.use_ansi_codes = use_ansi_codes
        self.keep_data = True
        self.paragraphs = []
        self.add_new_paragraphs = True
        self.unhandled_tags = []
        if doc_string:
            self.feed(doc_string)

    def add_paragraph(self):
        if self.add_new_paragraphs:
            self.paragraphs.append(cStringIO())

    def get_current_paragraph(self):
        if len(self.paragraphs) == 0:
            self.add_paragraph()
        return self.paragraphs[-1]

    def _handle_start_p(self, attrs):
        self.add_paragraph()

    def _handle_start_code(self, attrs):
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'\033[1m')

    def _handle_end_code(self):
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'\033[0m')

    def _handle_start_examples(self, attrs):
        self.keep_data = False

    def _handle_end_examples(self):
        self.keep_data = True

    def _handle_start_li(self, attrs):
        self.add_paragraph()
        self.add_new_paragraphs = False
        paragraph = self.get_current_paragraph()
        paragraph.write('* ')

    def _handle_end_li(self):
        self.add_new_paragraphs = True

    def handle_starttag(self, tag, attrs):
        handler_name = '_handle_start_%s' % tag
        if hasattr(self, handler_name):
            getattr(self, handler_name)(attrs)
        else:
            self.unhandled_tags.append(tag)

    def handle_endtag(self, tag):
        handler_name = '_handle_end_%s' % tag
        if hasattr(self, handler_name):
            getattr(self, handler_name)()

    def handle_data(self, data):
        data = data.replace('\n', '')
        if len(data) == 0:
            return
        space_first = data[0] == ' '
        space_last = data[-1] == ' '
        data = ' '.join(data.split())
        if space_first:
            if len(data) > 0 and not data[0].isupper():
                data = ' ' + data
        if space_last:
            if len(data) > 0 and data[-1] != '.':
                data = data + ' '
        if data and self.keep_data:
            paragraph = self.get_current_paragraph()
            paragraph.write(data)

    def get_paragraphs(self):
        return [p.getvalue() for p in self.paragraphs]


class CLIHelp(object):

    def __init__(self, indent_width=4):
        self.height, self.width = get_terminal_size()
        self.indent_width = indent_width

    def indent_size(self, indent):
        return indent * self.indent_width

    def spaces(self, indent):
        return ' ' * self.indent_size(indent)

    def _do_section(self, title, item, lines, indent):
        spaces = self.spaces(indent)
        # hack until we have a more formal way of marking
        # deprecated parameters
        if item.documentation and item.documentation.find('Deprecated') >= 0:
            return
        lines.append('%s%s' % (spaces, title))
        if not item.documentation:
            lines.append('')
            return
        p = CLIHTMLParser(item.documentation, _have_fcntl)
        paragraphs = p.get_paragraphs()
        if len(paragraphs) > 0:
            indent += 1
            spaces = self.spaces(indent)
            for paragraph in paragraphs:
                if paragraph[0] == '*':
                    subsequent_indent = spaces + '  '
                else:
                    subsequent_indent = spaces
                wlines = textwrap.wrap(paragraph, self.width - len(spaces),
                                       initial_indent=spaces,
                                       subsequent_indent=subsequent_indent)
                lines.extend(wlines)
                lines.append('')

    def do_operation(self, op, indent):
        spaces = self.spaces(indent)
        lines = ['', 'NAME']
        lines.append('%s%s' % (spaces, op.cli_name))
        lines.append('')
        self._do_section('DESCRIPTION', op, lines, indent)
        # Now handle parameters
        required = []
        optional = []
        if op.params:
            required = [p for p in op.params if p.required]
            optional = [p for p in op.params if not p.required]
        lines.append('SYNOPSIS')
        lines.append('%saws %s %s' % (spaces,
                                      op.service.short_name,
                                      op.cli_name))
        indent += 1
        spaces = self.spaces(indent)
        for param in required:
            line = '%s%s ' % (spaces, param.cli_name)
            if param.type != 'boolean':
                line += '<value>'
            lines.append(line)
        for param in optional:
            line = '%s[%s ' % (spaces, param.cli_name)
            if param.type != 'boolean':
                line += '<value>]'
            else:
                line += ']'
            lines.append(line)
        lines.append('')
        msg = get_data('messages/RequiredParameters')
        lines.append('%s:' % msg)
        for param in required:
            self._do_section(param.cli_name, param, lines, indent)
        if not required:
            lines.append('%sNone' % spaces)
            lines.append('')
        msg = get_data('messages/OptionalParameters')
        lines.append('%s:' % msg)
        for param in optional:
            self._do_section(param.cli_name, param, lines, indent)
        if not optional:
            lines.append('%sNone' % spaces)
            lines.append('')
        return lines

    def do_service(self, service):
        indent = 0
        lines = []
        self._do_section(service.cli_name, service, lines, indent)
        indent += 1
        for op in service.operations:
            self._do_section(op.cli_name, op, lines, indent)
        return lines

    def _help(self, object):
        l = []
        if isinstance(object, BotoCoreObject):
            if object.type == 'operation':
                l = self.do_operation(object, 1)
        elif isinstance(object, Service):
            l = self.do_service(object)
        return l

    def __call__(self, object, indent=0, fp=sys.stdout):
        lines = self._help(object)
        if fp:
            for line in lines:
                fp.write(line + '\n')
        else:
            return lines
