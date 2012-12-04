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
try:
    import fcntl
    import termios
except:
    pass
import struct
import textwrap
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


class CLIHelp(object):

    def __init__(self, indent_width=4):
        self.height, self.width = get_terminal_size()
        self.indent_width = indent_width

    def strip_docs(self, s):
        if not s:
            return []
        s = s.replace('<p>', '')
        s = s.strip()
        l = s.split()
        s = ' '.join(l)
        l = s.split('</p>')
        return l

    def indent_size(self, indent):
        return indent * self.indent_width

    def spaces(self, indent):
        return ' ' * self.indent_size(indent)

    def _do_parameter(self, param, lines):
        # hack until we have a more formal way of marking
        # deprecated parameters
        indent = 1
        spaces = self.spaces(indent)
        if param.documentation.find('Deprecated') >= 0:
            return
        doc_lines = self.strip_docs(param.documentation)
        lines.append('%s%s' % (spaces, param.cli_name))
        if len(doc_lines) > 0:
            indent += 1
            spaces = self.spaces(indent)
            line = doc_lines[0]
            wrapped_lines = textwrap.wrap(line, self.width - len(spaces),
                                          drop_whitespace=True)
            if len(wrapped_lines) > 0:
                for wline in wrapped_lines:
                    lines.append('%s%s' % (spaces, wline))
        lines.append('')

    def do_operation(self, op):
        spaces = self.spaces(1)
        doc_lines = self.strip_docs(op.documentation)
        lines = ['', 'NAME']
        lines.append('%s%s' % (spaces, op.cli_name))
        lines.append('')
        lines.append('DESCRIPTION')
        wlines = textwrap.wrap(doc_lines[0].strip(),
                               self.width, initial_indent=spaces,
                               subsequent_indent=spaces)
        lines.extend(wlines)
        lines.append('')
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
        spaces = self.spaces(2)
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
            self._do_parameter(param, lines)
        if not required:
            lines.append('%sNone' % spaces)
            lines.append('')
        msg = get_data('messages/OptionalParameters')
        lines.append('%s:' % msg)
        for param in optional:
            self._do_parameter(param, lines)
        if not optional:
            lines.append('%sNone' % spaces)
            lines.append('')
        return lines

    def do_service(self, service):
        lines = []
        lines.append(service.cli_name)
        doc_lines = self.strip_docs(service.documentation)
        if len(doc_lines) > 0:
            lines.append(textwrap.fill(doc_lines[0].strip(),
                                       self.width,
                                       drop_whitespace=True))
        # Now handle operations
        max_len = max([len(m.cli_name) for m in service.operations])
        max_len += 2 * self.indent_width
        for op in service.operations:
            doc_lines = self.strip_docs(op.documentation)
            if len(doc_lines) > 0:
                line = doc_lines[0]
                wrapped_lines = textwrap.wrap(line, self.width - max_len,
                                              drop_whitespace=True)
                if len(wrapped_lines) > 0:
                    line = '%s%s%s' % (' ' * self.indent_width,
                                       op.cli_name.ljust(max_len - self.indent_width),
                                       wrapped_lines[0])
                    lines.append(line)
                    for wline in wrapped_lines[1:]:
                        lines.append('%s%s' % (' ' * max_len, wline))
            else:
                lines.append('%s%s' % (' ' * 4, op.cli_name))
        return lines

    def merge_docs(self, object, line):
        lines = []
        if object.documentation:
            ntabs = len(line) / self.indent_width
            if len(line) % self.indent_width > 0:
                ntabs += 1
            ntabs += 1
            doc_lines = textwrap.wrap(self.strip_docs(object.documentation),
                                      self.width - self.indent_size(ntabs))
            spaces = ' ' * (self.indent_size(ntabs) - len(line))
            lines.append(line + spaces + doc_lines[0])
            for line in doc_lines[1:]:
                lines.append(self.spaces(ntabs) + line)
        else:
            lines.append(line)
        return lines

    def _help(self, object):
        l = []
        if isinstance(object, BotoCoreObject):
            if object.type == 'operation':
                l = self.do_operation(object)
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
