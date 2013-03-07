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

import textwrap
from six.moves import cStringIO


class BaseStyle(object):

    def __init__(self, doc, indent_width=4, **kwargs):
        self.doc = doc
        self.indent_width = indent_width
        self.kwargs = kwargs
        self.keep_data = True

    def spaces(self, indent):
        return ' ' * (indent * self.indent_width)

    def start_bold(self, attrs=None):
        return ''

    def end_bold(self):
        return ''

    def bold(self, s):
        return self.start_bold() + s + self.end_bold()

    def ref(self, link, title=None):
        self.bold(link)

    def h2(self, s):
        return self.bold(s)

    def h3(self, s):
        return self.bold(s)

    def start_underline(self, attrs=None):
        return ''

    def end_underline(self):
        return ''

    def underline(self, s):
        return self.start_underline() + s + self.end_underline()

    def start_italics(self, attrs=None):
        return ''

    def end_italics(self):
        return ''

    def italics(self, s):
        return self.start_italics() + s + self.end_italics()

    def start_p(self, attrs=None):
        self.doc.add_paragraph()

    def end_p(self):
        return ''

    def start_code(self, attrs=None):
        self.doc.do_translation = True
        return self.start_bold(attrs)

    def end_code(self):
        self.doc.do_translation = False
        return self.end_bold()

    def start_a(self, attrs=None):
        self.doc.do_translation = True
        return self.start_underline()

    def end_a(self):
        self.doc.do_translation = False
        return self.end_underline()

    def start_i(self, attrs=None):
        self.doc.do_translation = True
        return self.start_italics()

    def end_i(self):
        self.doc.do_translation = False
        return self.end_italics()

    def start_li(self, attrs=None):
        return ''

    def end_li(self):
        return ''

    def start_examples(self, attrs):
        self.doc.keep_data = False

    def end_examples(self):
        self.doc.keep_data = True


class CLIStyle(BaseStyle):

    def start_bold(self, attrs=None):
        if self.kwargs.get('do_ansi', False):
            return '\033[1m'
        return ''

    def end_bold(self):
        if self.kwargs.get('do_ansi', False):
            return '\033[0m'
        return ''

    def start_underline(self, attrs=None):
        if self.kwargs.get('do_ansi', False):
            return '\033[4m'
        return ''

    def end_underline(self):
        if self.kwargs.get('do_ansi', False):
            return '\033[0m'
        return ''

    def start_italics(self, attrs=None):
        if self.kwargs.get('do_ansi', False):
            return '\033[3m'
        return ''

    def end_italics(self):
        if self.kwargs.get('do_ansi', False):
            return '\033[0m'
        return ''

    def start_li(self, attrs=None):
        para = self.doc.add_paragraph()
        para.subsequent_indent = para.initial_indent + 1
        para.write('  * ')

    def h2(self, s):
        para = self.doc.get_current_paragraph()
        para.lines_before = 1
        return self.bold(s)

    def end_p(self):
        para = self.doc.get_current_paragraph()
        para.lines_after = 2


class ReSTStyle(object):

    def __init__(self, doc, indent_width=2, **kwargs):
        self.doc = doc
        self.indent_width = indent_width
        self.kwargs = kwargs
        self.keep_data = True
        self.do_p = True

    def spaces(self, indent):
        return ' ' * (indent * self.indent_width)

    def start_bold(self, attrs=None):
        return '**'

    def end_bold(self):
        return '** '

    def start_b(self, attrs=None):
        self.doc.do_translation = True
        return self.start_bold(attrs)

    def end_b(self):
        self.doc.do_translation = False
        return '** '

    def bold(self, s):
        retval = ''
        if s:
            retval = self.start_bold() + s + self.end_bold()
        return retval

    def ref(self, title, link=None):
        if link is None:
            link = title
        return ':doc:`%s <%s>`' % (title, link)

    def h1(self, s):
        para = self.doc.add_paragraph()
        para = self.doc.get_current_paragraph()
        para.write(s)
        para = self.doc.add_paragraph()
        para.write('*' * len(s))
        para = self.doc.add_paragraph()
        return ''

    def h2(self, s):
        para = self.doc.add_paragraph()
        para = self.doc.get_current_paragraph()
        para.write(s)
        para = self.doc.add_paragraph()
        para.write('=' * len(s))
        para = self.doc.add_paragraph()
        return ''

    def h3(self, s):
        para = self.doc.add_paragraph()
        para = self.doc.get_current_paragraph()
        para.write(s)
        para = self.doc.add_paragraph()
        para.write('-' * len(s))
        para = self.doc.add_paragraph()
        return ''

    def start_underline(self, attrs=None):
        return ''

    def end_underline(self):
        return ''

    def underline(self, s):
        retval = ''
        if s:
            retval = self.start_underline() + s + self.end_underline()
        return retval

    def start_italics(self, attrs=None):
        return '*'

    def end_italics(self):
        return '*'

    def italics(self, s):
        retval = ''
        if s:
            retval = self.start_italics() + s + self.end_italics()
        return retval

    def start_p(self, attrs=None):
        if self.do_p:
            self.doc.add_paragraph()

    def end_p(self):
        if self.do_p:
            self.doc.add_paragraph()

    def start_code(self, attrs=None):
        self.doc.do_translation = True
        s = '``'
        para = self.doc.get_current_paragraph()
        if para.current_char and not para.current_char.isspace():
            s = ' ' + s
        return s

    def end_code(self):
        self.doc.do_translation = False
        return '`` '

    def code(self, s):
        retval = ''
        if s:
            retval = self.start_code() + s + self.end_code()
        return retval

    def start_note(self, attrs=None):
        para = self.doc.add_paragraph()
        para.write('.. note::')
        self.doc.indent()
        para = self.doc.add_paragraph()
        para = self.doc.add_paragraph()

    def end_note(self):
        self.doc.dedent()
        self.doc.add_paragraph()

    def start_important(self, attrs=None):
        para = self.doc.add_paragraph()
        para.write('.. warning::')
        self.doc.indent()
        para = self.doc.add_paragraph()
        para = self.doc.add_paragraph()

    def end_important(self):
        self.doc.dedent()
        self.doc.add_paragraph()

    def start_a(self, attrs=None):
        self.doc.do_translation = True
        self.doc.get_current_paragraph().write(' ')
        return self.start_underline()

    def end_a(self):
        self.doc.do_translation = False
        self.doc.get_current_paragraph().write(' ')
        return self.end_underline()

    def start_i(self, attrs=None):
        self.doc.do_translation = True
        return self.start_italics()

    def end_i(self):
        self.doc.do_translation = False
        return self.end_italics()

    def start_li(self, attrs=None):
        para = self.doc.add_paragraph()
        para.subsequent_indent = para.initial_indent + 1
        para.write('* ')
        para.current_char = None
        self.do_p = False

    def end_li(self):
        self.do_p = True
        return ''

    def start_ul(self, attrs=None):
        self.doc.add_paragraph()

    def end_ul(self):
        self.doc.add_paragraph()

    def start_examples(self, attrs=None):
        self.doc.keep_data = False

    def end_examples(self):
        self.doc.keep_data = True

    def start_fullname(self, attrs=None):
        self.doc.keep_data = False

    def end_fullname(self):
        self.doc.keep_data = True
