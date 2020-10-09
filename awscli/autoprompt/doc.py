# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import io
from docutils.core import publish_string

import awscli.clidriver
from awscli.argparser import ArgTableArgParser
from awscli.bcdoc import docevents, textwriter


class DocsGetter:
    """The main documentation getter for the auto-prompt workflow.

    This class calls out to helper classes to help grab the specific docs for
    service commands and service operations.

    """
    def __init__(self, driver, aws_top_level_docs_getter=None,
                 service_command_docs_getter=None):
        self._driver = driver
        self._service_command_table = self._driver.subcommand_table
        if aws_top_level_docs_getter is None:
            aws_top_level_docs_getter = AwsTopLevelDocsGetter(self._driver)
        self._aws_top_level_docs_getter = aws_top_level_docs_getter
        if service_command_docs_getter is None:
            service_command_docs_getter = \
                ServiceCommandDocsGetter(self._driver)
        self._service_command_docs_getter = service_command_docs_getter

    @property
    def aws_top_level_docs_getter(self):
        return self._aws_top_level_docs_getter

    @property
    def service_command_docs_getter(self):
        return self._service_command_docs_getter

    def get_docs(self, command_text):
        args = command_text.split()
        if not args:
            return self._aws_top_level_docs_getter.get_docs(self._driver)
        args = self._filter_out_options(args)
        try:
            if self._is_valid_service(args):
                return self._service_command_docs_getter.get_docs(args)
            else:
                # At this point, one of two things has happened:
                # 1. An invalid service command has been entered.
                # 2. The user has cleared the buffer and has started typing
                #    out a command. The in-process command won't get parsed
                #    correctly yet (e.g. `aws ec`).
                return self._aws_top_level_docs_getter.get_docs(self._driver)
        except:
            # If there are any errors in the documentation retrieval process,
            # we pull up the default top-level aws docs. This can happen if
            # the buffer is cleared and `aws help` is entered.
            return self._aws_top_level_docs_getter.get_docs(self._driver)

    def _is_valid_service(self, args):
        self._valid_services = \
            {name for name, _ in self._service_command_table.items()}
        service, *_ = args
        return service in self._valid_services

    def _filter_out_options(self, args):
        # Because the lowest level of documentation retrieval is at the
        # service operation level, we can ignore all `--options` in the
        # passed-in arguments for the purposes of grabbing documentation. This
        # allows us to bypass the problem of getting parsing errors in
        # self.get_docs() when there are `--options` that require arguments to
        # be passed in (e.g. `aws ec2 describe-instances --output`). We also
        # need to filter out any specified files at the command line, as these
        # are positional args that don't make sense after `--options` are
        # removed.
        file_path_chars = '.:\\/'
        return [
            arg for arg in args
            if not arg.startswith('--')
            and not any(char in arg for char in file_path_chars)
        ]


class BaseDocsGetter:
    def __init__(self, driver):
        self._driver = driver
        self._cache = {}

    def _render_docs(self, help_command):
        renderer = FileRenderer()
        help_command.renderer = renderer
        help_command(None, None)
        # The report_level override is so that we don't print anything
        # to stdout/stderr on rendering issues.
        original_cli_help = renderer.contents.decode('utf-8')
        text_content = self._convert_rst_to_basic_text(original_cli_help)
        index = text_content.find('DESCRIPTION')
        if index > 0:
            text_content = text_content[index + len('DESCRIPTION'):]
        return text_content

    def _convert_rst_to_basic_text(self, contents):
        """Convert restructured text to basic text output.

        This function removes most of the decorations added
        in restructured text.

        This function is used to generate documentation we
        can show to users in a cross platform manner.

        Basic indentation and list formatting are kept,
        but many RST features are removed (such as
        section underlines).

        """
        # The report_level override is so that we don't print anything
        # to stdout/stderr on rendering issues.
        converted = publish_string(
            contents, writer=BasicTextWriter(),
            settings_overrides={'report_level': 5, 'halt_level': 5}
        )
        return converted.decode('utf-8')

    def get_doc_content(self, help_command):
        """Does the heavy lifting of retrieving the actual documentation
        content.

        """
        instance = help_command.EventHandlerClass(help_command)
        docevents.generate_events(help_command.session, help_command)
        content = self._render_docs(help_command)
        instance.unregister()
        return content


class AwsTopLevelDocsGetter(BaseDocsGetter):
    """Getter for the top-level `aws` command."""
    def get_docs(self, driver):
        if 'aws' not in self._cache:
            help_command = driver.create_help_command()
            self._cache['aws'] = self.get_doc_content(help_command)
        return self._cache['aws']


class ServiceCommandDocsGetter(BaseDocsGetter):
    def __init__(self, driver, service_operation_docs_getter=None):
        super(ServiceCommandDocsGetter, self).__init__(driver)
        self._service_command_table = self._driver.subcommand_table
        if service_operation_docs_getter is None:
            service_operation_docs_getter = \
                ServiceOperationDocsGetter(self._driver)
        self._service_operation_docs_getter = service_operation_docs_getter

    def get_docs(self, args):
        service_command, remaining = self._get_service_command(args)
        if not remaining \
                or not self._is_valid_operation(service_command, remaining):
            help_command = service_command.create_help_command()
            if help_command.name not in self._cache:
                self._cache[help_command.name] = \
                     self.get_doc_content(help_command)
            return self._cache[help_command.name]
        else:
            return self._service_operation_docs_getter.get_docs(
                service_command, remaining)

    def _get_service_command(self, args):
        service_name, remaining = self._get_service_command_name(args)
        return self._service_command_table[service_name], remaining

    def _get_service_command_name(self, args):
        parser = self._driver.create_parser(self._service_command_table)
        parsed_args, remaining = parser.parse_known_args(args)
        return parsed_args.command, remaining

    def _is_valid_operation(self, service_command, remaining):
        subcommand_table = service_command.subcommand_table
        self._valid_operations = {name for name, _ in subcommand_table.items()}
        operation, *_ = remaining
        return operation in self._valid_operations


class ServiceOperationDocsGetter(BaseDocsGetter):
    def get_docs(self, service_command, remaining):
        subcommand_table = service_command.subcommand_table
        operation_name = self._get_operation_name(service_command, remaining)
        if (service_command.name, operation_name) not in self._cache:
            service_operation = subcommand_table[operation_name]
            help_command = service_operation.create_help_command()
            self._cache[(service_command.name, operation_name)] = \
                self.get_doc_content(help_command)
        return self._cache[(service_command.name, operation_name)]

    def _get_operation_name(self, service_command, remaining):
        # We need to differentiate between `awscli.clidriver.ServiceCommand`
        # and `awscli.customizations` objects, as they use different parsers.
        if isinstance(service_command, awscli.clidriver.ServiceCommand):
            service_parser = service_command.create_parser()
            parsed_args, remaining = service_parser.parse_known_args(remaining)
            operation_name = parsed_args.operation
        else:
            service_parser = ArgTableArgParser(
                service_command.arg_table, service_command.subcommand_table)
            parsed_args, remaining = service_parser.parse_known_args(remaining)
            operation_name = parsed_args.subcommand
        return operation_name


class FileRenderer:

    def __init__(self):
        self._io = io.BytesIO()

    def render(self, contents):
        self._io.write(contents)

    @property
    def contents(self):
        return self._io.getvalue()


class BasicTextWriter(textwriter.TextWriter):
    def translate(self):
        visitor = BasicTextTranslator(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.body


class BasicTextTranslator(textwriter.TextTranslator):
    def depart_title(self, node):
        # Make the section titles upper cased, similar to
        # the man page output.
        text = ''.join(x[1] for x in self.states.pop() if x[0] == -1)
        self.stateindent.pop()
        self.states[-1].append((0, ['', text.upper(), '']))

    # The botocore TextWriter has additional formatting
    # for literals, for the aws-shell docs we don't want any
    # special processing so these nodes are noops.

    def visit_literal(self, node):
        pass

    def depart_literal(self, node):
        pass
