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
from botocore import xform_name
from botocore.docs.bcdoc.docevents import DOC_EVENTS
from botocore.model import StringShape

from awscli import SCALAR_TYPES
from awscli.argprocess import ParamShorthandDocGen
from awscli.topictags import TopicTagDB

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
                doc.write(':ref:`%s <cli:%s>`' % (cmd, full_cmd_name))
            doc.write(' ]')

    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.new_paragraph()
        reference = help_command.event_class.replace('.', ' ')
        if reference != 'aws':
            reference = 'aws ' + reference
        doc.writeln('.. _cli:%s:' % reference)
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
        self._document_enums(argument, doc)
        doc.style.dedent()
        doc.style.new_paragraph()

    def doc_relateditems_start(self, help_command, **kwargs):
        if help_command.related_items:
            doc = help_command.doc
            doc.style.h2('See Also')

    def doc_relateditem(self, help_command, related_item, **kwargs):
        doc = help_command.doc
        doc.write('* ')
        doc.style.sphinx_reference_label(
            label='cli:%s' % related_item,
            text=related_item
        )
        doc.write('\n')

    def _document_enums(self, argument, doc):
        """Documents top-level parameter enums"""
        if hasattr(argument, 'argument_model'):
            model = argument.argument_model
            if isinstance(model, StringShape):
                if model.enum:
                    doc.style.new_paragraph()
                    doc.write('Possible values:')
                    doc.style.start_ul()
                    for enum in model.enum:
                        doc.style.li('``%s``' % enum)
                    doc.style.end_ul()


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
        service_model = self.help_command.obj
        for operation_name in service_model.operation_names:
            d[operation_name] = xform_name(operation_name, '-')
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
        if (len(subcommand_table) > 0):
            file_name = '%s/index' % command_name
            doc.style.tocitem(command_name, file_name=file_name)
        else:
            doc.style.tocitem(command_name)


class OperationDocumentEventHandler(CLIDocumentEventHandler):

    def build_translation_map(self):
        operation_model = self.help_command.obj
        d = {}
        for cli_name, cli_argument in self.help_command.arg_table.items():
            if cli_argument.argument_model is not None:
                d[cli_argument.argument_model.name] = cli_name
        for operation_name in operation_model.service_model.operation_names:
            d[operation_name] = xform_name(operation_name, '-')
        return d

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        operation_model = help_command.obj
        doc.style.h2('Description')
        doc.include_doc_string(operation_model.documentation)

    def _json_example_value_name(self, argument_model, include_enum_values=True):
        # If include_enum_values is True, then the valid enum values
        # are included as the sample JSON value.
        if isinstance(argument_model, StringShape):
            if argument_model.enum and include_enum_values:
                choices = argument_model.enum
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
        if docgen.supports_shorthand(cli_argument.argument_model):
            example_shorthand_syntax = docgen.generate_shorthand_example(
                cli_argument.cli_name, cli_argument.argument_model)
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
        if argument_model is not None and argument_model.type_name == 'list' and \
                argument_model.member.type_name in SCALAR_TYPES:
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
                member, include_enum_values=False)
            doc.write('%s %s ...' % (example_type, example_type))
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
            doc.write("    %s\n" % value)
        doc.write("\n")

    def doc_output(self, help_command, event_name, **kwargs):
        doc = help_command.doc
        doc.style.h2('Output')
        operation_model = help_command.obj
        output_shape = operation_model.output_shape
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


class TopicListerDocumentEventHandler(CLIDocumentEventHandler):
    DESCRIPTION = (
        'This is the AWS CLI Topic Guide. It gives access to a set '
        'of topics that provide a deeper understanding of the CLI. To access '
        'the list of topics from the command line, run ``aws help topics``. '
        'To access a specific topic from the command line, run '
        '``aws help [topicname]``, where ``topicname`` is the name of the '
        'topic as it appears in the output from ``aws help topics``.')

    def __init__(self, help_command):
        self.help_command = help_command
        self.register(help_command.session, help_command.event_class)
        self.help_command.doc.translation_map = self.build_translation_map()
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
            refname='cli:aws help %s' % self.help_command.name,
            link='')
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
                    topic_name, 'description')
                doc.write('* ')
                doc.style.sphinx_reference_label(
                    label='cli:aws help %s' % topic_name,
                    text=topic_name
                )
                doc.write(': %s\n' % description)
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
                label='cli:aws help topics',
                text='topics'
            )
            doc.write(' ]')

    def doc_title(self, help_command, **kwargs):
        doc = help_command.doc
        doc.style.new_paragraph()
        doc.style.link_target_definition(
            refname='cli:aws help %s' % self.help_command.name,
            link='')
        title = self._topic_tag_db.get_tag_single_value(
            help_command.name, 'title')
        doc.style.h1(title)

    def doc_description(self, help_command, **kwargs):
        doc = help_command.doc
        topic_filename = os.path.join(self._topic_tag_db.topic_dir,
                                      help_command.name + '.rst')
        contents = self._remove_tags_from_content(topic_filename)
        doc.writeln(contents)
        doc.style.new_paragraph()

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
        return ''.join(lines[content_begin_index:])

    def _line_has_tag(self, line):
        for tag in self._topic_tag_db.valid_tags:
            if line.startswith(':' + tag + ':'):
                return True
        return False

    def doc_subitems_start(self, help_command, **kwargs):
        pass
