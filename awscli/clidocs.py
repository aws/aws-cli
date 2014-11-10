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
import logging
from bcdoc.docevents import DOC_EVENTS

from awscli import SCALAR_TYPES
from awscli.argprocess import ParamShorthandDocGen

LOG = logging.getLogger(__name__)


class CLIDocumentEventHandler(object):

    def __init__(self, help_command):
        self.help_command = help_command
        self.register(help_command.session, help_command.event_class)
        self.help_command.doc.translation_map = self.build_translation_map()
        self._arg_groups = self._build_arg_table_groups(help_command)
        self._documented_arg_groups = []

    def _build_arg_table_groups(self, help_command):
        arg_groups = {}
        for name, arg in help_command.arg_table.items():
            if arg.group_name is not None:
                arg_groups.setdefault(arg.group_name, []).append(arg)
        return arg_groups

    def build_translation_map(self):
        return dict()

    def _map_handlers(self, session, event_class, mapfn):
        for event in DOC_EVENTS:
            event_handler_name = event.replace('-', '_')
            if hasattr(self, event_handler_name):
                event_handler = getattr(self, event_handler_name)
                format_string = DOC_EVENTS[event]
                num_args = len(format_string.split('.')) - 2
                format_args = (event_class,) + ('*',) * num_args
                event_string = event + format_string % format_args
                unique_id = event_class + event_handler_name
                mapfn(event_string, event_handler, unique_id)

    def register(self, session, event_class):
        """
        The default register iterates through all of the
        available document events and looks for a corresponding
        handler method defined in the object.  If it's there, that
        handler method will be registered for the all events of
        that type for the specified ``event_class``.
        """
        self._map_handlers(session, event_class, session.register)

    def unregister(self):
        """
        The default unregister iterates through all of the
        available document events and looks for a corresponding
        handler method defined in the object.  If it's there, that
        handler method will be unregistered for the all events of
        that type for the specified ``event_class``.
        """
        self._map_handlers(self.help_command.session,
                           self.help_command.event_class,
                           self.help_command.session.unregister)

    # These are default doc handlers that apply in the general case.

    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h1(help_command.name)

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Description')
        doc.include_doc_string(help_command.description)
        doc.style.new_paragraph()

    def doc_synopsis_start(self, help_command, **kwargs):
        self._documented_arg_groups = []
        doc = help_command.doc
        doc.style.h2('Synopsis')
        doc.style.start_codeblock()
        doc.writeln('%s' % help_command.name)

    def doc_synopsis_option(self, arg_name, help_command, **kwargs):
        doc = help_command.doc
        argument = help_command.arg_table[arg_name]
        if argument.group_name in self._arg_groups:
            if argument.group_name in self._documented_arg_groups:
                # This arg is already documented so we can move on.
                return
            option_str = ' | '.join(
                [a.cli_name for a in
                 self._arg_groups[argument.group_name]])
            self._documented_arg_groups.append(argument.group_name)
        else:
            option_str = '%s <value>' % argument.cli_name
        if not argument.required:
            option_str = '[%s]' % option_str
        doc.writeln('%s' % option_str)

    def doc_synopsis_end(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.end_codeblock()
        # Reset the documented arg groups for other sections
        # that may document args (the detailed docs following
        # the synopsis).
        self._documented_arg_groups = []

    def doc_options_start(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Options')
        if not help_command.arg_table:
            doc.write('*None*\n')

    def doc_option(self, arg_name, help_command, **kwargs):
        doc = help_command.doc
        argument = help_command.arg_table[arg_name]
        if argument.group_name in self._arg_groups:
            if argument.group_name in self._documented_arg_groups:
                # This arg is already documented so we can move on.
                return
            name = ' | '.join(
                ['``%s``' % a.cli_name for a in
                 self._arg_groups[argument.group_name]])
            self._documented_arg_groups.append(argument.group_name)
        else:
            name = '``%s``' % argument.cli_name
        doc.write('%s (%s)\n' % (name, argument.cli_type_name))
        doc.style.indent()
        doc.include_doc_string(argument.documentation)
        doc.style.dedent()
        doc.style.new_paragraph()


class ProviderDocumentEventHandler(CLIDocumentEventHandler):

    def doc_synopsis_start(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Synopsis')
        doc.style.codeblock(help_command.synopsis)
        doc.include_doc_string(help_command.help_usage)

    def doc_synopsis_option(self, arg_name, help_command, **kwargs):
        pass

    def doc_synopsis_end(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.new_paragraph()

    def doc_options_start(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Options')

    def doc_option(self, arg_name, help_command, **kwargs):
        doc = help_command.doc
        argument = help_command.arg_table[arg_name]
        doc.writeln('``%s`` (%s)' % (argument.cli_name,
                                     argument.cli_type_name))
        doc.include_doc_string(argument.documentation)
        if argument.choices:
            doc.style.start_ul()
            for choice in argument.choices:
                doc.style.li(choice)
            doc.style.end_ul()

    def doc_subitems_start(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Available Services')
        doc.style.toctree()

    def doc_subitem(self, command_name, help_command, **kwargs):
        doc = help_command.doc
        file_name = '%s/index' % command_name
        doc.style.tocitem(command_name, file_name=file_name)


class ServiceDocumentEventHandler(CLIDocumentEventHandler):

    def build_translation_map(self):
        d = {}
        for op in self.help_command.obj.operations:
            d[op.name] = op.cli_name
        return d

    # A service document has no synopsis.
    def doc_synopsis_start(self, help_command, **kwargs):
        pass

    def doc_synopsis_option(self, arg_name, help_command, **kwargs):
        pass

    def doc_synopsis_end(self, help_command, **kwargs):
        pass

    # A service document has no option section.
    def doc_options_start(self, help_command, **kwargs):
        pass

    def doc_option(self, arg_name, help_command, **kwargs):
        pass

    def doc_option_example(self, arg_name, help_command, **kwargs):
        pass

    def doc_options_end(self, help_command, **kwargs):
        pass

    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h1(help_command.name)

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        service = help_command.obj
        doc.style.h2('Description')
        doc.include_doc_string(service.documentation)

    def doc_subitems_start(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Available Commands')
        doc.style.toctree()

    def doc_subitem(self, command_name, help_command, **kwargs):
        doc = help_command.doc
        subcommand = help_command.command_table[command_name]
        subcommand_table = getattr(subcommand, 'subcommand_table', {})
        # If the subcommand table has commands in it,
        # direct the subitem to the command's index because
        # it has more subcommands to be documented.
        if (len(subcommand_table) > 0):
            file_name = '%s/index' % command_name
            doc.style.tocitem(command_name, file_name=file_name)
        else:
            doc.style.tocitem(command_name)


class OperationDocumentEventHandler(CLIDocumentEventHandler):

    def build_translation_map(self):
        operation = self.help_command.obj
        d = {}
        for cli_name, cli_argument in self.help_command.arg_table.items():
            if cli_argument.argument_model is not None:
                d[cli_argument.argument_model.name] = cli_name
        for operation in operation.service.operations:
            d[operation.name] = operation.cli_name
        return d

    def doc_breadcrumbs(self, help_command, event_name, **kwargs):
        doc = help_command.doc
        if doc.target != 'man':
            l = event_name.split('.')
            if len(l) > 1:
                service_name = l[1]
                doc.write('[ ')
                doc.style.ref('aws', '../index')
                doc.write(' . ')
                doc.style.ref(service_name, 'index')
                doc.write(' ]')

    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h1(help_command.name)

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        operation = help_command.obj
        doc.style.h2('Description')
        doc.include_doc_string(operation.documentation)

    def _json_example_value_name(self, argument_model, include_enum_values=True):
        # If include_enum_values is True, then the valid enum values
        # are included as the sample JSON value.
        if argument_model.type_name == 'string':
            if 'enum' in argument_model.metadata and include_enum_values:
                choices = argument_model.metadata['enum']
                return '|'.join(['"%s"' % c for c in choices])
            else:
                return '"string"'
        elif argument_model.type_name == 'boolean':
            return 'true|false'
        else:
            return '%s' % argument_model.type_name

    def _json_example(self, doc, argument_model, stack):
        if argument_model.name in stack:
            # Document the recursion once, otherwise just
            # note the fact that it's recursive and return.
            if stack.count(argument_model.name) > 1:
                if argument_model.type_name == 'structure':
                    doc.write('{ ... recursive ... }')
                return
        stack.append(argument_model.name)
        try:
            self._do_json_example(doc, argument_model, stack)
        finally:
            stack.pop()

    def _do_json_example(self, doc, argument_model, stack):
        if argument_model.type_name == 'list':
            doc.write('[')
            if argument_model.member.type_name in SCALAR_TYPES:
                doc.write('%s, ...' % self._json_example_value_name(argument_model.member))
            else:
                doc.style.indent()
                doc.style.new_line()
                self._json_example(doc, argument_model.member, stack)
                doc.style.new_line()
                doc.write('...')
                doc.style.dedent()
                doc.style.new_line()
            doc.write(']')
        elif argument_model.type_name == 'map':
            doc.write('{')
            doc.style.indent()
            key_string = self._json_example_value_name(argument_model.key)
            doc.write('%s: ' % key_string)
            if argument_model.value.type_name in SCALAR_TYPES:
                doc.write(self._json_example_value_name(argument_model.value))
            else:
                doc.style.indent()
                self._json_example(doc, argument_model.value, stack)
                doc.style.dedent()
            doc.style.new_line()
            doc.write('...')
            doc.style.dedent()
            doc.write('}')
        elif argument_model.type_name == 'structure':
            doc.write('{')
            doc.style.indent()
            doc.style.new_line()
            self._doc_input_structure_members(doc, argument_model, stack)

    def _doc_input_structure_members(self, doc, argument_model, stack):
        members = argument_model.members
        for i, member_name in enumerate(members):
            member_model = members[member_name]
            member_type_name = member_model.type_name
            if member_type_name in SCALAR_TYPES:
                doc.write('"%s": %s' % (member_name,
                    self._json_example_value_name(member_model)))
            elif member_type_name == 'structure':
                doc.write('"%s": ' % member_name)
                self._json_example(doc, member_model, stack)
            elif member_type_name == 'map':
                doc.write('"%s": ' % member_name)
                self._json_example(doc, member_model, stack)
            elif member_type_name == 'list':
                doc.write('"%s": ' % member_name)
                self._json_example(doc, member_model, stack)
            if i < len(members) - 1:
                doc.write(',')
                doc.style.new_line()
            else:
                doc.style.dedent()
                doc.style.new_line()
        doc.write('}')

    def doc_option_example(self, arg_name, help_command, **kwargs):
        doc = help_command.doc
        cli_argument = help_command.arg_table[arg_name]
        if cli_argument.group_name in self._arg_groups:
            if cli_argument.group_name in self._documented_arg_groups:
                # Args with group_names (boolean args) don't
                # need to generate example syntax.
                return
        argument_model = cli_argument.argument_model
        docgen = ParamShorthandDocGen()
        if docgen.supports_shorthand(cli_argument):
            # TODO: bcdoc should not know about shorthand syntax. This
            # should be pulled out into a separate handler in the
            # awscli.customizations package.
            example_shorthand_syntax = docgen.generate_shorthand_example(
                cli_argument)
            if example_shorthand_syntax is None:
                # If the shorthand syntax returns a value of None,
                # this indicates to us that there is no example
                # needed for this param so we can immediately
                # return.
                return
            doc.style.new_paragraph()
            doc.write('Shorthand Syntax')
            doc.style.start_codeblock()
            for example_line in example_shorthand_syntax.splitlines():
                doc.writeln(example_line)
            doc.style.end_codeblock()
        if argument_model is not None and argument_model.type_name == 'list' and \
                argument_model.member.type_name in SCALAR_TYPES:
            # A list of scalars is special.  While you *can* use
            # JSON ( ["foo", "bar", "baz"] ), you can also just
            # use the argparse behavior of space separated lists.
            # "foo" "bar" "baz".  In fact we don't even want to
            # document the JSON syntax in this case.
            doc.style.new_paragraph()
            doc.write('Syntax')
            doc.style.start_codeblock()
            example_type = self._json_example_value_name(
                argument_model.member, include_enum_values=False)
            doc.write('%s %s ...' % (example_type, example_type))
            if 'enum' in argument_model.member.metadata:
                # If we have enum values, we can tell the user
                # exactly what valid values they can provide.
                enum = argument_model.member.metadata['enum']
                self._write_valid_enums(doc, enum)
            doc.style.end_codeblock()
            doc.style.new_paragraph()
        elif cli_argument.cli_type_name not in SCALAR_TYPES:
            doc.style.new_paragraph()
            doc.write('JSON Syntax')
            doc.style.start_codeblock()
            self._json_example(doc, argument_model, stack=[])
            doc.style.end_codeblock()
            doc.style.new_paragraph()

    def _write_valid_enums(self, doc, enum_values):
        doc.style.new_paragraph()
        doc.write("Where valid values are:\n")
        for value in enum_values:
            doc.write("    %s\n" % value)
        doc.write("\n")

    def doc_output(self, help_command, event_name, **kwargs):
        doc = help_command.doc
        doc.style.h2('Output')
        operation = help_command.obj
        output_shape = operation.model.output_shape
        if output_shape is None:
            doc.write('None')
        else:
            for member_name, member_shape in output_shape.members.items():
                self._doc_member_for_output(doc, member_name, member_shape, stack=[])

    def _doc_member_for_output(self, doc, member_name, member_shape, stack):
        if member_shape.name in stack:
            # Document the recursion once, otherwise just
            # note the fact that it's recursive and return.
            if stack.count(member_shape.name) > 1:
                if member_shape.type_name == 'structure':
                    doc.write('( ... recursive ... )')
                return
        stack.append(member_shape.name)
        try:
            self._do_doc_member_for_output(doc, member_name,
                                           member_shape, stack)
        finally:
            stack.pop()

    def _do_doc_member_for_output(self, doc, member_name, member_shape, stack):
        docs = member_shape.documentation
        if member_name:
            doc.write('%s -> (%s)' % (member_name, member_shape.type_name))
        else:
            doc.write('(%s)' % member_shape.type_name)
        doc.style.indent()
        doc.style.new_paragraph()
        doc.include_doc_string(docs)
        doc.style.new_paragraph()
        member_type_name = member_shape.type_name
        if member_type_name == 'structure':
            for sub_name, sub_shape in member_shape.members.items():
                self._doc_member_for_output(doc, sub_name, sub_shape, stack)
        elif member_type_name == 'map':
            key_shape = member_shape.key
            key_name = key_shape.serialization.get('name', 'key')
            self._doc_member_for_output(doc, key_name, key_shape, stack)
            value_shape = member_shape.value
            value_name = value_shape.serialization.get('name', 'value')
            self._doc_member_for_output(doc, value_name, value_shape, stack)
        elif member_type_name == 'list':
            self._doc_member_for_output(doc, '', member_shape.member, stack)
        doc.style.dedent()
        doc.style.new_paragraph()
