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
    """
    A simple HTML -> Console converter.  Really focused only on
    the subset of HTML that shows up in the documentation strings
    found in the models.

    :type html: str
    :param html: The HTML to be converted.

    :type use_ansi_codes: bool
    :param use_ansi_codes: A flag to determine whether ANSI terminal
        control codes should be inserted into the output strings or
        not.  Thse codes work on many command shells but not in
        Windows standard command prompt.
    """

    def __init__(self, use_ansi_codes, translation_table=None, width=80):
        html_parser.HTMLParser.__init__(self)
        self.use_ansi_codes = use_ansi_codes
        self.translation_table = translation_table
        self.width = width
        self.indent_width = 4
        self.do_translation = False
        self.keep_data = True
        self.paragraphs = []
        self.add_new_paragraphs = True
        self.unhandled_tags = []

    @classmethod
    def bold(self, s):
        if _have_fcntl:
            return u'\033[1m%s\033[0m' % s
        else:
            return s

    @classmethod
    def underline(self, s):
        if _have_fcntl:
            return u'\033[4m%s\033[0m' % s
        else:
            return s

    @classmethod
    def italics(self, s):
        if _have_fcntl:
            return u'\033[3m%s\033[0m' % s
        else:
            return s

    def indent_size(self, indent):
        return indent * self.indent_width

    def spaces(self, indent):
        return ' ' * self.indent_size(indent)

    def translate_words(self, words):
        if self.translation_table and self.do_translation:
            new_words = []
            for word in words:
                if word in self.translation_table:
                    new_words.append(self.translation_table[word])
                else:
                    new_words.append(word)
            words = new_words
        return words

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
        self.do_translation = True
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'\033[1m')

    def _handle_end_code(self):
        self.do_translation = False
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'\033[0m')

    def _handle_start_a(self, attrs):
        self.do_translation = True
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'\033[4m')

    def _handle_end_a(self):
        self.do_translation = False
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'\033[0m')

    def _handle_start_i(self, attrs):
        self.do_translation = True

    def _handle_end_i(self):
        self.do_translation = False

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
        words = data.split()
        words = self.translate_words(words)
        data = ' '.join(words)
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
        paragraphs = [p.getvalue() for p in self.paragraphs]
        self.paragraphs = []
        return paragraphs

    def do_section(self, title, documentation, lines, indent):
        lines.append('%s%s' % (self.spaces(indent),
                               self.bold(title)))
        if documentation:
            self.feed(documentation)
        paragraphs = self.get_paragraphs()
        if len(paragraphs) > 0:
            indent += 1
            spaces = self.spaces(indent)
            for paragraph in paragraphs:
                if paragraph[0] == '*':
                    subsequent_indent = spaces + '  '
                else:
                    subsequent_indent = spaces
                wlines = textwrap.wrap(paragraph, self.width,
                                       initial_indent=spaces,
                                       subsequent_indent=subsequent_indent,
                                       break_on_hyphens=False)
                lines.extend(wlines)
                lines.append('')


class MarkdownHTMLParser(html_parser.HTMLParser):
    """
    A simple HTML -> Markdown converter.  Really focused only on
    the subset of HTML that shows up in the documentation strings
    found in the models.

    :type html: str
    :param html: The HTML to be converted.

    :type use_ansi_codes: bool
    :param use_ansi_codes: A flag to determine whether ANSI terminal
        control codes should be inserted into the output strings or
        not.  Thse codes work on many command shells but not in
        Windows standard command prompt.
    """

    def __init__(self, use_ansi_codes, translation_table=None, width=80):
        html_parser.HTMLParser.__init__(self)
        self.use_ansi_codes = use_ansi_codes
        self.translation_table = translation_table
        self.width = width
        self.indent_width = 0
        self.do_translation = False
        self.keep_data = True
        self.paragraphs = []
        self.add_new_paragraphs = True
        self.unhandled_tags = []

    @classmethod
    def bold(self, s):
        return u'**%s**' % s

    @classmethod
    def underline(self, s):
        return u'_%s_' % s

    @classmethod
    def italics(self, s):
        return u'*%s*' % s

    def indent_size(self, indent):
        return indent * self.indent_width

    def spaces(self, indent):
        return ' ' * self.indent_size(indent)

    def translate_words(self, words):
        if self.translation_table and self.do_translation:
            new_words = []
            for word in words:
                if word in self.translation_table:
                    new_words.append(self.translation_table[word])
                else:
                    new_words.append(word)
            words = new_words
        return words

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
        self.do_translation = True
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'**')

    def _handle_end_code(self):
        self.do_translation = False
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'**')

    def _handle_start_a(self, attrs):
        self.do_translation = True
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'_')

    def _handle_end_a(self):
        self.do_translation = False
        if self.use_ansi_codes:
            paragraph = self.get_current_paragraph()
            paragraph.write(u'_')

    def _handle_start_i(self, attrs):
        self.do_translation = True

    def _handle_end_i(self):
        self.do_translation = False

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
        words = data.split()
        words = self.translate_words(words)
        data = ' '.join(words)
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
        paragraphs = [p.getvalue() for p in self.paragraphs]
        self.paragraphs = []
        return paragraphs

    def do_section(self, title, documentation, lines, indent):
        lines.append('%s%s' % (self.spaces(indent),
                               self.bold(title)))
        lines.append('')
        if documentation:
            self.feed(documentation)
        paragraphs = self.get_paragraphs()
        if len(paragraphs) > 0:
            indent += 1
            spaces = self.spaces(indent)
            for paragraph in paragraphs:
                if paragraph[0] == '*':
                    subsequent_indent = spaces + '  '
                else:
                    subsequent_indent = spaces
                wlines = textwrap.wrap(paragraph, self.width,
                                       initial_indent=spaces,
                                       subsequent_indent=subsequent_indent,
                                       break_on_hyphens=False)
                lines.extend(wlines)
                lines.append('')


class CLIHelp(object):

    def __init__(self, indent_width=4, parser_cls=CLIHTMLParser):
        self.height, self.width = get_terminal_size()
        self.indent_width = indent_width
        self.parser_cls = parser_cls
        self.type_map = {}
        self.parser = self.parser_cls(_have_fcntl, self.type_map, self.width)

    def do_section(self, title, documentation, lines, indent):
        self.parser.do_section(title, documentation, lines, indent)

    def do_parameter(self, param, lines, indent, subitem=False):
        # hack until we have a more formal way of marking
        # deprecated parameters
        if param.documentation and param.documentation.find('Deprecated') >= 0:
            return
        param_name = param.cli_name
        if subitem:
            param_name = param.py_name
        self.do_section(param_name, param.documentation, lines, indent)
        if param.type == 'structure':
            for member in param.members:
                self.do_parameter(member, lines, indent+1, subitem=True)
        elif param.type == 'list':
            self.do_parameter(param.members, lines, indent+1, subitem=True)

    def do_operation(self, op, indent):
        lines = []
        self.do_section('NAME', op.cli_name, lines, indent)
        self.do_section('DESCRIPTION',
                        op.documentation, lines, indent)
        # Now handle parameters
        required = []
        optional = []
        if op.params:
            required = [p for p in op.params if p.required]
            optional = [p for p in op.params if not p.required]
        self.do_section('SYNOPSIS',
                        'aws %s %s' % (op.service.short_name, op.cli_name),
                        lines, indent)
        indent += 1
        spaces = self.parser.spaces(indent)
        for param in required:
            line = '%s%s ' % (spaces, param.cli_name)
            if param.type != 'boolean':
                line += self.parser.italics('value')
            lines.append(line)
        for param in optional:
            line = '%s[%s ' % (spaces, param.cli_name)
            if param.type != 'boolean':
                line += self.parser.italics('value')
            line += ']'
            lines.append(line)
        lines.append('')
        msg = get_data('messages/RequiredParameters')
        self.do_section(msg, None, lines, indent)
        for param in required:
            self.do_parameter(param, lines, indent)
        if not required:
            lines.append('%sNone' % spaces)
            lines.append('')
        msg = get_data('messages/OptionalParameters')
        self.do_section(msg, None, lines, indent)
        for param in optional:
            self.do_parameter(param, lines, indent)
        if not optional:
            lines.append('%sNone' % spaces)
            lines.append('')
        return lines

    def do_service(self, service, indent=0):
        lines = []
        self.do_section(service.cli_name, service.documentation, lines, indent)
        indent += 1
        for op in service.operations:
            self.do_section(op.cli_name, op.documentation, lines, indent)
        return lines

    def build_type_map(self, service):
        for op in service.operations:
            self.type_map[op.name] = op.cli_name
            for param in op.params:
                self.type_map[param.name] = param.cli_name

    def build_type_map(self, service):
        for op in service.operations:
            self.type_map[op.name] = op.cli_name

    def help(self, service, operation, fp=sys.stdout):
        self.build_type_map(service)
        lines = []
        if operation:
            lines = self.do_operation(operation, 0)
        else:
            lines = self.do_service(service, 0)
        if fp:
            for line in lines:
                fp.write(line + '\n')
        else:
            return lines
