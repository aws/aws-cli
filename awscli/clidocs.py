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
import os
import re

from botocore.model import StringShape
from botocore.utils import is_json_value_header

from awscli import SCALAR_TYPES
from awscli.argprocess import ParamShorthandDocGen
from awscli.bcdoc.docevents import DOC_EVENTS
from awscli.topictags import TopicTagDB
from awscli.utils import (
    find_service_and_method_in_event_name,
    is_document_type,
    is_streaming_blob_type,
    is_tagged_union_type,
    operation_uses_document_types,
)

LOG = logging.getLogger(__name__)
EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'examples'
)
GLOBAL_OPTIONS_FILE = os.path.join(EXAMPLES_DIR, 'global_options.rst')
GLOBAL_OPTIONS_SYNOPSIS_FILE = os.path.join(
    EXAMPLES_DIR, 'global_synopsis.rst'
)


class CLIDocumentEventHandler:
    def __init__(self, help_command):
        self.help_command = help_command
        self.register(help_command.session, help_command.event_class)
        self._arg_groups = self._build_arg_table_groups(help_command)
        self._documented_arg_groups = []

    def _build_arg_table_groups(self, help_command):
        arg_groups = {}
        for arg in help_command.arg_table.values():
            if arg.group_name is not None:
                arg_groups.setdefault(arg.group_name, []).append(arg)
        return arg_groups

    def _get_argument_type_name(self, shape, default):
        if is_json_value_header(shape):
            return 'JSON'
        if is_document_type(shape):
            return 'document'
        if is_streaming_blob_type(shape):
            return 'streaming blob'
        if is_tagged_union_type(shape):
            return 'tagged union structure'
        return default

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
        self._map_handlers(
            self.help_command.session,
            self.help_command.event_class,
            self.help_command.session.unregister,
        )

    # These are default doc handlers that apply in the general case.

    def doc_breadcrumbs(self, help_command, **kwargs):
        doc = help_command.doc
        if doc.target != 'man':
            cmd_names = help_command.event_class.split('.')
            doc.write('[ ')
            doc.write(':ref:`aws <cli:aws>`')
            full_cmd_list = ['aws']
            for cmd in cmd_names[:-1]:
                doc.write(' . ')
                full_cmd_list.append(cmd)
                full_cmd_name = ' '.join(full_cmd_list)
                doc.write(f':ref:`{cmd} <cli:{full_cmd_name}>`')
            doc.write(' ]')

    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.new_paragraph()
        reference = help_command.event_class.replace('.', ' ')
        if reference != 'aws':
            reference = 'aws ' + reference
        doc.writeln(f'.. _cli:{reference}:')
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
        doc.writeln(help_command.name)

    def doc_synopsis_option(self, arg_name, help_command, **kwargs):
        doc = help_command.doc
        argument = help_command.arg_table[arg_name]
        if argument.group_name in self._arg_groups:
            if argument.group_name in self._documented_arg_groups:
                # This arg is already documented so we can move on.
                return
            option_str = ' | '.join(
                a.cli_name for a in self._arg_groups[argument.group_name]
            )
            self._documented_arg_groups.append(argument.group_name)
        elif argument.cli_name.startswith('--'):
            option_str = f'{argument.cli_name} <value>'
        else:
            option_str = f'<{argument.cli_name}>'
        if not (
            argument.required
            or getattr(argument, '_DOCUMENT_AS_REQUIRED', False)
        ):
            option_str = f'[{option_str}]'
        doc.writeln(option_str)

    def doc_synopsis_end(self, help_command, **kwargs):
        doc = help_command.doc
        # Append synopsis for global options.
        doc.write_from_file(GLOBAL_OPTIONS_SYNOPSIS_FILE)
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
                f'``{a.cli_name}``' for a in self._arg_groups[argument.group_name]
            )
            self._documented_arg_groups.append(argument.group_name)
        else:
            name = f'``{argument.cli_name}``'
        argument_type_name = self._get_argument_type_name(
            argument.argument_model, argument.cli_type_name
        )
        doc.write(f'{name} ({argument_type_name})\n')
        doc.style.indent()
        doc.include_doc_string(argument.documentation)
        if is_streaming_blob_type(argument.argument_model):
            self._add_streaming_blob_note(doc)
        if is_tagged_union_type(argument.argument_model):
            self._add_tagged_union_note(argument.argument_model, doc)
        if hasattr(argument, 'argument_model'):
            self._document_enums(argument.argument_model, doc)
            self._document_nested_structure(argument.argument_model, doc)
        doc.style.dedent()
        doc.style.new_paragraph()

    def doc_global_option(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Global Options')
        doc.write_from_file(GLOBAL_OPTIONS_FILE)

    def doc_relateditems_start(self, help_command, **kwargs):
        if help_command.related_items:
            doc = help_command.doc
            doc.style.h2('See Also')

    def doc_relateditem(self, help_command, related_item, **kwargs):
        doc = help_command.doc
        doc.write('* ')
        doc.style.sphinx_reference_label(
            label=f'cli:{related_item}', text=related_item
        )
        doc.write('\n')

    def _document_enums(self, model, doc):
        """Documents top-level parameter enums"""
        if isinstance(model, StringShape):
            if model.enum:
                doc.style.new_paragraph()
                doc.write('Possible values:')
                doc.style.start_ul()
                for enum in model.enum:
                    doc.style.li(f'``{enum}``')
                doc.style.end_ul()

    def _document_nested_structure(self, model, doc):
        """Recursively documents parameters in nested structures"""
        member_type_name = getattr(model, 'type_name', None)
        if member_type_name == 'structure':
            for member_name, member_shape in model.members.items():
                self._doc_member(
                    doc, member_name, member_shape, stack=[model.name]
                )
        elif member_type_name == 'list':
            self._doc_member(doc, '', model.member, stack=[model.name])
        elif member_type_name == 'map':
            key_shape = model.key
            key_name = key_shape.serialization.get('name', 'key')
            self._doc_member(doc, key_name, key_shape, stack=[model.name])
            value_shape = model.value
            value_name = value_shape.serialization.get('name', 'value')
            self._doc_member(doc, value_name, value_shape, stack=[model.name])

    def _doc_member(self, doc, member_name, member_shape, stack):
        if member_shape.name in stack:
            # Document the recursion once, otherwise just
            # note the fact that it's recursive and return.
            if stack.count(member_shape.name) > 1:
                if member_shape.type_name == 'structure':
                    doc.write('( ... recursive ... )')
                return
        stack.append(member_shape.name)
        try:
            self._do_doc_member(doc, member_name, member_shape, stack)
        finally:
            stack.pop()

    def _do_doc_member(self, doc, member_name, member_shape, stack):
        docs = member_shape.documentation
        type_name = self._get_argument_type_name(
            member_shape, member_shape.type_name
        )
        if member_name:
            doc.write(f'{member_name} -> ({type_name})')
        else:
            doc.write(f'({type_name})')
        doc.style.indent()
        doc.style.new_paragraph()
        doc.include_doc_string(docs)
        if is_tagged_union_type(member_shape):
            self._add_tagged_union_note(member_shape, doc)
        doc.style.new_paragraph()
        member_type_name = member_shape.type_name
        if member_type_name == 'structure':
            for sub_name, sub_shape in member_shape.members.items():
                self._doc_member(doc, sub_name, sub_shape, stack)
        elif member_type_name == 'map':
            key_shape = member_shape.key
            key_name = key_shape.serialization.get('name', 'key')
            self._doc_member(doc, key_name, key_shape, stack)
            value_shape = member_shape.value
            value_name = value_shape.serialization.get('name', 'value')
            self._doc_member(doc, value_name, value_shape, stack)
        elif member_type_name == 'list':
            self._doc_member(doc, '', member_shape.member, stack)
        doc.style.dedent()
        doc.style.new_paragraph()

    def _add_streaming_blob_note(self, doc):
        doc.style.start_note()
        msg = (
            "This argument is of type: streaming blob. "
            "Its value must be the path to a file "
            "(e.g. ``path/to/file``) and must **not** "
            "be prefixed with ``file://`` or ``fileb://``"
        )
        doc.writeln(msg)
        doc.style.end_note()

    def _add_tagged_union_note(self, shape, doc):
        doc.style.start_note()
        members_str = ", ".join(f'``{key}``' for key in shape.members.keys())
        doc.writeln(
            "This is a Tagged Union structure. Only one of the "
            f"following top level keys can be set: {members_str}."
        )
        doc.style.end_note()


class ProviderDocumentEventHandler(CLIDocumentEventHandler):
    def doc_breadcrumbs(self, help_command, event_name, **kwargs):
        pass

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
        pass

    def doc_option(self, arg_name, help_command, **kwargs):
        pass

    def doc_subitems_start(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Available Services')
        doc.style.toctree()

    def doc_subitem(self, command_name, help_command, **kwargs):
        doc = help_command.doc
        doc.style.tocitem(command_name, file_name=f"{command_name}/index")


class ServiceDocumentEventHandler(CLIDocumentEventHandler):
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

    def doc_global_option(self, help_command, **kwargs):
        pass

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        service_model = help_command.obj
        doc.style.h2('Description')
        # TODO: need a documentation attribute.
        doc.include_doc_string(service_model.documentation)

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
        if len(subcommand_table) > 0:
            doc.style.tocitem(command_name, file_name=f"{command_name}/index")
        else:
            doc.style.tocitem(command_name)


class OperationDocumentEventHandler(CLIDocumentEventHandler):
    AWS_DOC_BASE = 'https://docs.aws.amazon.com/goto/WebAPI'

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        operation_model = help_command.obj
        doc.style.h2('Description')
        doc.include_doc_string(operation_model.documentation)
        self._add_webapi_crosslink(help_command)
        self._add_note_for_document_types_if_used(help_command)

    def _add_webapi_crosslink(self, help_command):
        doc = help_command.doc
        operation_model = help_command.obj
        service_model = operation_model.service_model
        service_uid = service_model.metadata.get('uid')
        if service_uid is None:
            # If there's no service_uid in the model, we can't
            # be certain if the generated cross link will work
            # so we don't generate any crosslink info.
            return
        doc.style.new_paragraph()
        doc.write("See also: ")
        link = f'{self.AWS_DOC_BASE}/{service_uid}/{operation_model.name}'
        doc.style.external_link(title="AWS API Documentation", link=link)
        doc.writeln('')

    def _add_note_for_document_types_if_used(self, help_command):
        if operation_uses_document_types(help_command.obj):
            help_command.doc.style.new_paragraph()
            help_command.doc.writeln(
                f'``{help_command.name}`` uses document type values. Document '
                'types follow the JSON data model where valid values are: '
                'strings, numbers, booleans, null, arrays, and objects. For '
                'command input, options and nested parameters that are labeled '
                'with the type ``document`` must be provided as JSON. '
                'Shorthand syntax does not support document types.'
            )

    def _json_example_value_name(
        self, argument_model, include_enum_values=True
    ):
        # If include_enum_values is True, then the valid enum values
        # are included as the sample JSON value.
        if isinstance(argument_model, StringShape):
            if argument_model.enum and include_enum_values:
                choices = argument_model.enum
                return '|'.join(f'"{c}"' for c in choices)
            else:
                return '"string"'
        elif argument_model.type_name == 'boolean':
            return 'true|false'
        else:
            return argument_model.type_name

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
                example_name = self._json_example_value_name(argument_model.member)
                doc.write(f'{example_name}, ...')
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
            doc.write(f'{key_string}: ')
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
            if argument_model.is_document_type:
                self._doc_document_member(doc)
            else:
                self._doc_input_structure_members(doc, argument_model, stack)

    def _doc_document_member(self, doc):
        doc.write('{...}')

    def _doc_input_structure_members(self, doc, argument_model, stack):
        doc.write('{')
        doc.style.indent()
        doc.style.new_line()
        members = argument_model.members
        for i, member_name in enumerate(members):
            member_model = members[member_name]
            member_type_name = member_model.type_name
            if member_type_name in SCALAR_TYPES:
                example_name = self._json_example_value_name(member_model)
                doc.write(f'"{member_name}": {example_name}')
            elif member_type_name == 'structure':
                doc.write(f'"{member_name}": ')
                self._json_example(doc, member_model, stack)
            elif member_type_name == 'map':
                doc.write(f'"{member_name}": ')
                self._json_example(doc, member_model, stack)
            elif member_type_name == 'list':
                doc.write(f'"{member_name}": ')
                self._json_example(doc, member_model, stack)
            if i < len(members) - 1:
                doc.write(',')
                doc.style.new_line()
        doc.style.dedent()
        doc.style.new_line()
        doc.write('}')

    def doc_option_example(self, arg_name, help_command, event_name, **kwargs):
        service_id, operation_name = find_service_and_method_in_event_name(
            event_name
        )
        doc = help_command.doc
        cli_argument = help_command.arg_table[arg_name]
        if cli_argument.group_name in self._arg_groups:
            if cli_argument.group_name in self._documented_arg_groups:
                # Args with group_names (boolean args) don't
                # need to generate example syntax.
                return
        argument_model = cli_argument.argument_model
        docgen = ParamShorthandDocGen()
        if docgen.supports_shorthand(cli_argument.argument_model):
            example_shorthand_syntax = docgen.generate_shorthand_example(
                cli_argument, service_id, operation_name
            )
            if example_shorthand_syntax is None:
                # If the shorthand syntax returns a value of None,
                # this indicates to us that there is no example
                # needed for this param so we can immediately
                # return.
                return
            if example_shorthand_syntax:
                doc.style.new_paragraph()
                doc.write('Shorthand Syntax')
                doc.style.start_codeblock()
                for example_line in example_shorthand_syntax.splitlines():
                    doc.writeln(example_line)
                doc.style.end_codeblock()
        if (
            argument_model is not None
            and argument_model.type_name == 'list'
            and argument_model.member.type_name in SCALAR_TYPES
        ):
            # A list of scalars is special.  While you *can* use
            # JSON ( ["foo", "bar", "baz"] ), you can also just
            # use the argparse behavior of space separated lists.
            # "foo" "bar" "baz".  In fact we don't even want to
            # document the JSON syntax in this case.
            member = argument_model.member
            doc.style.new_paragraph()
            doc.write('Syntax')
            doc.style.start_codeblock()
            example_type = self._json_example_value_name(
                member, include_enum_values=False
            )
            doc.write(f'{example_type} {example_type} ...')
            if isinstance(member, StringShape) and member.enum:
                # If we have enum values, we can tell the user
                # exactly what valid values they can provide.
                self._write_valid_enums(doc, member.enum)
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
            doc.write(f"    {value}\n")
        doc.write("\n")

    def doc_output(self, help_command, event_name, **kwargs):
        doc = help_command.doc
        doc.style.h2('Output')
        operation_model = help_command.obj
        output_shape = operation_model.output_shape
        if output_shape is None or not output_shape.members:
            doc.write('None')
        else:
            for member_name, member_shape in output_shape.members.items():
                self._doc_member(doc, member_name, member_shape, stack=[])


class TopicListerDocumentEventHandler(CLIDocumentEventHandler):
    DESCRIPTION = (
        'This is the AWS CLI Topic Guide. It gives access to a set '
        'of topics that provide a deeper understanding of the CLI. To access '
        'the list of topics from the command line, run ``aws help topics``. '
        'To access a specific topic from the command line, run '
        '``aws help [topicname]``, where ``topicname`` is the name of the '
        'topic as it appears in the output from ``aws help topics``.'
    )

    def __init__(self, help_command):
        self.help_command = help_command
        self.register(help_command.session, help_command.event_class)
        self._topic_tag_db = TopicTagDB()
        self._topic_tag_db.load_json_index()

    def doc_breadcrumbs(self, help_command, **kwargs):
        doc = help_command.doc
        if doc.target != 'man':
            doc.write('[ ')
            doc.style.sphinx_reference_label(label='cli:aws', text='aws')
            doc.write(' ]')

    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.new_paragraph()
        doc.style.link_target_definition(
            refname=f'cli:aws help {self.help_command.name}', link=''
        )
        doc.style.h1('AWS CLI Topic Guide')

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Description')
        doc.include_doc_string(self.DESCRIPTION)
        doc.style.new_paragraph()

    def doc_synopsis_start(self, help_command, **kwargs):
        pass

    def doc_synopsis_end(self, help_command, **kwargs):
        pass

    def doc_options_start(self, help_command, **kwargs):
        pass

    def doc_options_end(self, help_command, **kwargs):
        pass

    def doc_global_option(self, help_command, **kwargs):
        pass

    def doc_subitems_start(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.h2('Available Topics')

        categories = self._topic_tag_db.query('category')
        topic_names = self._topic_tag_db.get_all_topic_names()

        # Sort the categories
        category_names = sorted(categories.keys())
        for category_name in category_names:
            doc.style.h3(category_name)
            doc.style.new_paragraph()
            # Write out the topic and a description for each topic under
            # each category.
            for topic_name in sorted(categories[category_name]):
                description = self._topic_tag_db.get_tag_single_value(
                    topic_name, 'description'
                )
                doc.write('* ')
                doc.style.sphinx_reference_label(
                    label=f'cli:aws help {topic_name}', text=topic_name
                )
                doc.write(f': {description}\n')
        # Add a hidden toctree to make sure everything is connected in
        # the document.
        doc.style.hidden_toctree()
        for topic_name in topic_names:
            doc.style.hidden_tocitem(topic_name)


class TopicDocumentEventHandler(TopicListerDocumentEventHandler):
    def doc_breadcrumbs(self, help_command, **kwargs):
        doc = help_command.doc
        if doc.target != 'man':
            doc.write('[ ')
            doc.style.sphinx_reference_label(label='cli:aws', text='aws')
            doc.write(' . ')
            doc.style.sphinx_reference_label(
                label='cli:aws help topics', text='topics'
            )
            doc.write(' ]')

    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.new_paragraph()
        doc.style.link_target_definition(
            refname=f'cli:aws help {self.help_command.name}', link=''
        )
        title = self._topic_tag_db.get_tag_single_value(
            help_command.name, 'title'
        )
        doc.style.h1(title)

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        topic_filename = os.path.join(
            self._topic_tag_db.topic_dir, f'{help_command.name}.rst'
        )
        contents = self._remove_tags_from_content(topic_filename)
        doc.writeln(contents)
        doc.style.new_paragraph()

    def _remove_tags_from_content(self, filename):
        with open(filename) as f:
            lines = f.readlines()

        content_begin_index = 0
        for i, line in enumerate(lines):
            # If a line is encountered that does not begin with the tag
            # end the search for tags and mark where tags end.
            if not self._line_has_tag(line):
                content_begin_index = i
                break

        # Join all of the non-tagged lines back together.
        return ''.join(lines[content_begin_index:])

    def _line_has_tag(self, line):
        for tag in self._topic_tag_db.valid_tags:
            if line.startswith(f':{tag}:'):
                return True
        return False

    def doc_subitems_start(self, help_command, **kwargs):
        pass


class GlobalOptionsDocumenter:
    """Documenter used to pre-generate global options docs."""

    def __init__(self, help_command):
        self._help_command = help_command

    def _remove_multilines(self, s):
        return re.sub(r'\n+', '\n', s)

    def doc_global_options(self):
        help_command = self._help_command
        for arg in help_command.arg_table:
            argument = help_command.arg_table.get(arg)
            help_command.doc.writeln(
                f"``{argument.cli_name}`` ({argument.cli_type_name})"
            )
            help_command.doc.style.indent()
            help_command.doc.style.new_paragraph()
            help_command.doc.include_doc_string(argument.documentation)
            if argument.choices:
                help_command.doc.style.start_ul()
                for choice in argument.choices:
                    help_command.doc.style.li(choice)
                help_command.doc.style.end_ul()
            help_command.doc.style.dedent()
            help_command.doc.style.new_paragraph()
        global_options = help_command.doc.getvalue().decode('utf-8')
        return self._remove_multilines(global_options)

    def doc_global_synopsis(self):
        help_command = self._help_command
        for arg in help_command.arg_table:
            argument = help_command.arg_table.get(arg)
            if argument.cli_type_name == 'boolean':
                arg_synopsis = f"[{argument.cli_name}]"
            else:
                arg_synopsis = f"[{argument.cli_name} <value>]"
            help_command.doc.writeln(arg_synopsis)
        global_synopsis = help_command.doc.getvalue().decode('utf-8')
        return self._remove_multilines(global_synopsis)
