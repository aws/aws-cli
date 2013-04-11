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
import textwrap
from six.moves import html_parser
from six.moves import cStringIO
from .style import ReSTStyle
from botocore import ScalarTypes


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
        else:
            self.doc.get_current_paragraph().write(' ')

    def handle_data(self, data):
        data = data.replace('\n', '')
        if not data:
            return
        if data.isspace():
            data = ' '
        words = data.split()
        words = self.doc.translate_words(words)
        data = ' '.join(words)
        begin_space = data[0].isspace()
        end_space = data[-1].isspace()
        if begin_space:
            if len(data) > 0 and not data[0].isupper():
                data = ' ' + data
        if end_space:
            if len(data) > 0 and data[-1] != '.':
                data = data + ' '
        self.doc.handle_data(data)

    def handle_data(self, data):
        if data.isspace():
            data = ' '
        else:
            end_space = data[-1].isspace()
            words = data.split()
            words = self.doc.translate_words(words)
            data = ' '.join(words)
            if end_space:
                data += ' '
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
        self.current_char = None

    def write(self, s):
        if self.doc.keep_data:
            self.fp.write(s)
            if s:
                self.current_char = s[-1]

    def wrap(self):
        init_indent = self.doc.style.spaces(self.initial_indent)
        sub_indent = self.doc.style.spaces(self.subsequent_indent)
        s = textwrap.fill(self.fp.getvalue(), self.width,
                          initial_indent=init_indent,
                          subsequent_indent=sub_indent,
                          break_on_hyphens=False)
        return '\n' * self.lines_before + s + '\n' * self.lines_after


class Document(object):

    def __init__(self, session):
        self.session = session
        self.style = ReSTStyle(self)
        self.width = 80
        self.help_parser = HelpParser(self)
        self.paragraphs = []
        self.keep_data = True
        self.do_translation = False
        self.translation_map = {}
        self.build_translation_map()
        self.initial_indent = 0
        self.subsequent_indent = 0

    def build_translation_map(self):
        pass

    def indent(self):
        self.initial_indent += 1

    def dedent(self):
        self.initial_indent -= 1

    def translate_words(self, words):
        return [self.translation_map.get(w, w) for w in words]

    def add_paragraph(self):
        self.paragraphs.append(Paragraph(self, self.width,
                                         self.initial_indent))
        return self.paragraphs[-1]

    def get_current_paragraph(self):
        if len(self.paragraphs) == 0:
            self.add_paragraph(self)
        return self.paragraphs[-1]

    def do_title(self, title):
        self.add_paragraph().write(self.style.h1(title))
        self.add_paragraph()

    def do_description(self, description):
        msg = self.session.get_data('messages/Description')
        self.add_paragraph().write(self.style.h2(msg))
        if description:
            self.add_paragraph()
            self.help_parser.feed(description)

    def handle_data(self, data):
        if data and self.keep_data:
            paragraph = self.get_current_paragraph()
            if paragraph.current_char is None and data.isspace():
                pass
            else:
                paragraph.write(data.encode('utf-8'))

    def render(self, fp):
        for paragraph in self.paragraphs:
            fp.write(paragraph.wrap())

    def build(self, object):
        pass


class OperationDocument(Document):

    def __init__(self, session, operation):
        self.operation = operation
        Document.__init__(self, session)

    def example_value_name(self, param):
        if param.type == 'string':
            if hasattr(param, 'enum'):
                choices = [e.decode('utf-8') for e in param.enum]
                return '|'.join(['"%s"' % c for c in choices])
            else:
                return '"string"'
        elif param.type == 'boolean':
            return 'true|false'
        else:
            return '%s' % param.type

    def _do_example(self, param):
        para = self.add_paragraph()
        if param.type == 'list':
            para.write('[')
            if param.members.type in ScalarTypes:
                para.write('%s, ...' % self.example_value_name(param.members))
            else:
                self.indent()
                self._do_example(param.members)
                self.add_paragraph().write('...')
                self.dedent()
                para = self.add_paragraph()
            para.write(']')
        elif param.type == 'map':
            para.write('{')
            self.indent()
            key_string = self.example_value_name(param.keys)
            para = self.add_paragraph()
            para.write('%s: ' % key_string)
            if param.members.type in ScalarTypes:
                para.write(self.example_value_name(param.members))
            else:
                self.indent()
                self._do_example(param.members)
                self.dedent()
            self.add_paragraph().write('...')
            self.dedent()
            self.add_paragraph().write('}')
        elif param.type == 'structure':
            para.write('{')
            self.indent()
            members = []
            for i, member in enumerate(param.members):
                para = self.add_paragraph()
                if member.type in ScalarTypes:
                    para.write('"%s": %s' % (member.py_name,
                                             self.example_value_name(member)))
                elif member.type == 'structure':
                    para.write('"%s": {' % member.py_name)
                    self.indent()
                    self._do_example(member)
                    self.dedent()
                elif member.type == 'map':
                    para.write('"%s": ' % member.py_name)
                    self.indent()
                    self._do_example(member)
                    self.dedent()
                elif member.type == 'list':
                    para.write('"%s": ' % member.py_name)
                    self.indent()
                    self._do_example(member)
                    self.dedent()
                if i < len(param.members) - 1:
                    para = self.get_current_paragraph()
                    para.write(',')
            self.dedent()
            para = self.add_paragraph()
            para.write('}')

    def do_example(self, param):
        if param.type in ('list', 'structure', 'map'):
            self.indent()
            para = self.add_paragraph()
            para.write(self.style.italics('Parameter Syntax'))
            para.write('::')
            self.indent()
            self.add_paragraph()
            self._do_example(param)
            self.dedent()
            self.dedent()
            self.add_paragraph()

    def build_translation_map(self):
        for param in self.operation.params:
            self.translation_map[param.name] = param.cli_name
        for operation in self.operation.service.operations:
            self.translation_map[operation.name] = operation.cli_name

    def do_parameter(self, parameter, subitem=False, substructure=False):
        if subitem:
            pname = parameter.py_name
        else:
            pname = parameter.cli_name
        para = self.add_paragraph()
        para.write(self.style.code(pname))
        ptype = parameter.type
        if parameter.type == 'list':
            if parameter.members.type in ScalarTypes:
                ptype = 'list of %s' % parameter.members.type
        if parameter.type == 'boolean' and parameter.false_name:
            para.write(' | ')
            para.write(self.style.code(parameter.false_name))
        para.write(' (%s)' % ptype)
        self.indent()
        if parameter.documentation:
            self.help_parser.feed(parameter.documentation)
        if parameter.type == 'structure':
            for param in parameter.members:
                self.do_parameter(param, subitem=True, substructure=True)
        elif parameter.type == 'list':
            if parameter.members.type not in ScalarTypes:
                self.do_parameter(parameter.members, subitem=True,
                                  substructure=substructure)
        self.dedent()
        self.add_paragraph()

    def do_parameters(self, operation):
        required = []
        optional = []
        if operation.params:
            required = [p for p in operation.params if p.required]
            optional = [p for p in operation.params if not p.required]
        msg = self.session.get_data('messages/Synopsis')
        self.add_paragraph().write(self.style.h2(msg))
        provider_name = self.session.get_variable('provider')
        self.add_paragraph().write('::')
        self.indent()
        self.add_paragraph()
        self.add_paragraph().write('%s %s %s' % (provider_name,
                                                 operation.service.cli_name,
                                                 operation.cli_name))
        self.indent()
        for param in required:
            para = self.add_paragraph()
            para.write('%s ' % param.cli_name)
            if param.type != 'boolean':
                para.write('<value>')
            else:
                para = self.add_paragraph()
                para.write('%s ' % param.false_name)
        for param in optional:
            para = self.add_paragraph()
            para.write('[%s ' % param.cli_name)
            if param.type != 'boolean':
                para.write('<value>')
            para.write(']')
        if operation.is_streaming():
            para = self.add_paragraph()
            para.write('output_file')
        self.dedent()
        self.dedent()
        msg = self.session.get_data('messages/RequiredParameters')
        self.add_paragraph().write(self.style.h2(msg))
        none_msg = self.session.get_data('messages/None')
        for param in required:
            self.do_parameter(param)
            self.do_example(param)
        if not required:
            self.add_paragraph().write(none_msg)
        msg = self.session.get_data('messages/OptionalParameters')
        self.add_paragraph().write(self.style.h2(msg))
        for param in optional:
            self.do_parameter(param)
            self.do_example(param)
        if not optional:
            self.add_paragraph().write(none_msg)
        if operation.is_streaming():
            msg = self.session.get_data('messages/PositionalArguments')
            self.add_paragraph().write(self.style.h2(msg))
            para = self.add_paragraph()
            para.write(self.style.code('output_file'))
            para.write(' (blob)')
            self.indent()
            self.add_paragraph().write('The output file')
            self.dedent()


    def _build_output(self, name, type_dict, lines, prefix=''):
        if not name:
            name = type_dict.get('xmlname', '')
        line = '            <listitem>\n'
        line += '                <para><phrase role="topcom">'
        line += (prefix + name)
        line += '&mdash;'
        line += '</phrase>'
        line += filter_html(type_dict.get('documentation', ''),
                            True, False)
        line += '</para>'
        line += '            </listitem>\n'
        lines.append(line)
        if type_dict['type'] == 'structure':
            sorted_keys = sorted(type_dict['members'])
            prefix = '%s%s:' % (prefix, name)
            for member in sorted_keys:
                _build_output(member, type_dict['members'][member],
                              lines, prefix)
        elif type_dict['type'] == 'list':
            prefix = '%s%s:' % (prefix, name)
            _build_output('', type_dict['members'], lines, prefix)

    def do_output(self, operation):
        if operation.output:
            for key in operation.output['members']:
                _build_output(key, operation.output['members'][key], lines)

    def build(self):
        self.do_title(self.operation.cli_name)
        self.do_description(self.operation.documentation)
        self.do_parameters(self.operation)


class ServiceDocument(Document):

    def __init__(self, session, service):
        self.service = service
        Document.__init__(self, session)

    def build_translation_map(self):
        for op in self.service.operations:
            self.translation_map[op.name] = op.cli_name

    def do_toc(self, service):
        self.add_paragraph().write(self.style.h2('Available Commands'))
        self.add_paragraph()
        self.add_paragraph().write('.. toctree::')
        self.indent()
        self.add_paragraph().write(':maxdepth: 1')
        self.add_paragraph().write(':titlesonly:')
        self.add_paragraph()
        op_names = [op.cli_name for op in service.operations]
        op_names = sorted(op_names)
        for op_name in op_names:
            self.add_paragraph().write(op_name)
        self.dedent()

    def do_man_toc(self, service):
        self.add_paragraph().write(self.style.h2('Available Commands'))
        self.add_paragraph()
        op_names = [op.cli_name for op in service.operations]
        op_names = sorted(op_names)
        self.style.start_ul()
        for op_name in op_names:
            self.style.start_li()
            self.get_current_paragraph().write(op_name)
            self.style.end_li()
        self.add_paragraph()

    def do_operation_summary(self, operation):
        self.indent()
        self.add_paragraph().write(self.style.ref(operation.cli_name))
        self.indent()
        self.add_paragraph()
        if operation.documentation:
            self.help_parser.feed(operation.documentation)
        self.dedent()
        self.dedent()

    def build(self, do_man=False):
        self.do_title(self.service.service_full_name)
        self.do_description(self.service.documentation)
        if do_man:
            self.do_man_toc(self.service)
        else:
            self.do_toc(self.service)


class ProviderDocument(Document):

    def do_usage(self, title):
        self.add_paragraph().write(self.style.h2('aws'))
        self.help_parser.feed(title)

    def do_synopsis(self, synopsis):
        self.add_paragraph().write('::')
        self.add_paragraph()
        self.indent()
        self.add_paragraph().write(synopsis)
        self.dedent()
        self.add_paragraph()

    def do_toc(self, provider_name):
        self.add_paragraph().write(self.style.h2('Available Services'))
        self.add_paragraph().write('.. toctree::')
        self.indent()
        self.add_paragraph().write(':maxdepth: 1')
        self.add_paragraph().write(':titlesonly:')
        self.add_paragraph()
        service_names = self.session.get_available_services(provider_name)
        service_names = sorted(service_names)
        for service_name in service_names:
            self.add_paragraph().write(service_name+'/index')
        self.dedent()

    def do_man_toc(self, provider_name):
        self.add_paragraph().write(self.style.h2('Available Services'))
        self.add_paragraph()
        service_names = self.session.get_available_services(provider_name)
        service_names = sorted(service_names)
        self.style.start_ul()
        for service_name in service_names:
            self.style.start_li()
            self.get_current_paragraph().write(service_name)
            self.style.end_li()

    def do_options(self, options, provider_name):
        self.add_paragraph().write(self.style.h2('OPTIONS'))
        for option in options:
            if option.startswith('--'):
                option_data = options[option]
                para = self.add_paragraph()
                usage_str = option
                if 'metavar' in option_data:
                    usage_str += ' <%s>' % option_data['metavar']
                para.write(self.style.code(usage_str))
                if 'help' in option_data:
                    self.indent()
                    self.add_paragraph().write(option_data['help'])
                    self.dedent()
                if 'choices' in option_data:
                    choices = option_data['choices']
                    if not isinstance(choices, list):
                        choices_path = choices.format(provider=provider_name)
                        choices = self.session.get_data(choices_path)
                    self.indent()
                    for choice in sorted(choices):
                        self.style.start_li()
                        self.get_current_paragraph().write(choice)
                        self.style.end_li()
                    self.dedent()

    def build(self, provider_name, do_man=False):
        cli = self.session.get_data('cli')
        self.do_title(provider_name)
        self.do_description(cli['description'])
        self.do_synopsis(cli['synopsis'])
        self.add_paragraph()
        self.help_parser.feed(cli['help_usage'])
        self.add_paragraph()
        self.do_options(cli['options'], provider_name)
        if do_man:
            self.do_man_toc(provider_name)
        else:
            self.do_toc(provider_name)


def gen_rst(session, provider=None, service=None,
            operation=None, fp=None, do_man=False):
    """
    """
    if fp is None:
        fp = sys.stdout
    if provider:
        doc = ProviderDocument(session)
        doc.build(provider, do_man)
        doc.render(fp)
    if operation:
        doc = OperationDocument(session, operation)
        doc.build()
        doc.render(fp)
    elif service:
        doc = ServiceDocument(session, service)
        doc.build(do_man)
        doc.render(fp)
