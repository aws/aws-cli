#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Test help output for the AWS CLI.

The purpose of these docs is to test that the generated output looks how
we expect.

It's intended to be as end to end as possible, but instead of looking
at the man output, we look one step before at the generated rst output
(it's easier to verify).

"""
import os
import re
import shlex
import docutils.nodes
import docutils.parsers.rst
import docutils.utils

from awscli.argparser import MainArgParser
from awscli.argparser import ServiceArgParser
from awscli.testutils import BaseAWSHelpOutputTest, create_clidriver


# Mapping of command names to subcommands that have examples in their help
# output.  This isn't mean to be an exhaustive list, but should help catch
# things like command table renames, virtual commands, etc.
COMMAND_EXAMPLES = {
    'cloudwatch': ['put-metric-data'],
    's3': ['cp', 'ls', 'mb', 'mv', 'rb', 'rm', 'sync'],
    's3api': ['get-object', 'put-object'],
    'ec2': ['run-instances', 'start-instances', 'stop-instances'],
    'swf': ['deprecate-domain', 'describe-domain'],
    'sqs': ['create-queue', 'get-queue-attributes'],
    'emr': ['add-steps', 'create-default-roles', 'describe-cluster', 'schedule-hbase-backup'],
    'opsworks': ['register'],
}
_dname = os.path.dirname
EXAMPLES_DIR = os.path.join(
    _dname(_dname(_dname(_dname(os.path.abspath(__file__))))),
    'awscli', 'examples')

ALLOWED_FILENAME_CHAR_REGEX = re.compile(r'([a-z0-9_\-\.]*$)')


# Used so that docutils doesn't write errors to stdout/stderr.
# We're collecting and reporting these via AssertionErrors messages.
class NoopWriter(object):
    def write(self, *args, **kwargs):
        pass


class _ExampleTests(BaseAWSHelpOutputTest):
    def noop_test(self):
        pass


def test_examples():
    for command, subcommands in COMMAND_EXAMPLES.items():
        for subcommand in subcommands:
            yield verify_has_examples, command, subcommand


def verify_has_examples(command, subcommand):
    t = _ExampleTests(methodName='noop_test')
    t.setUp()
    try:
        t.driver.main([command, subcommand, 'help'])
        t.assert_contains_with_count('========\nExamples\n========', 1)
    finally:
        t.tearDown()


def test_all_doc_examples():
    # CLIDriver can take up a lot of resources so we'll just create one
    # instance and use it for all the validation tests.
    driver = create_clidriver()
    command_validator = CommandValidator(driver)

    for example_file in iter_all_doc_examples():
        yield verify_has_only_ascii_chars, example_file
        yield verify_is_valid_rst, example_file
        yield verify_cli_commands_valid, example_file, command_validator


def iter_all_doc_examples():
    # Iterate over all rst doc examples0
    _dname = os.path.dirname
    for rootdir, _, filenames in os.walk(EXAMPLES_DIR):
        for filename in filenames:
            if not filename.endswith('.rst'):
                continue
            full_path = os.path.join(rootdir, filename)
            yield full_path


def verify_has_only_ascii_chars(filename):
    with open(filename, 'rb') as f:
        bytes_content = f.read()
        try:
            bytes_content.decode('ascii')
        except UnicodeDecodeError as e:
            # The test has failed so we'll try to provide a useful error
            # message.
            offset = e.start
            spread = 20
            bad_text = bytes_content[offset-spread:e.start+spread]
            underlined = ' ' * spread + '^'
            error_text = '\n'.join([bad_text, underlined])
            line_number = bytes_content[:offset].count(b'\n') + 1
            raise AssertionError(
                "Non ascii characters found in the examples file %s, line %s:"
                "\n\n%s\n" % (filename, line_number, error_text))


def verify_is_valid_rst(filename):
    _, errors = parse_rst(filename)
    if errors:
        raise AssertionError(_make_error_msg(filename, errors))


def parse_rst(filename):
    with open(filename) as f:
        contents = f.read()
    parser = docutils.parsers.rst.Parser()
    components = (docutils.parsers.rst.Parser,)
    settings = docutils.frontend.OptionParser(
        components=components).get_default_values()
    document = docutils.utils.new_document('<cli-example>', settings=settings)
    errors = []

    def record_errors(msg):
        msg.level = msg['level']
        msg.type = msg['type']
        error_message = docutils.nodes.Element.astext(msg.children[0])
        line_number = msg['line']
        errors.append({'msg': error_message, 'line_number': line_number})

    document.reporter.stream = NoopWriter()
    document.reporter.attach_observer(record_errors)
    parser.parse(contents, document)
    return document, errors


def _make_error_msg(filename, errors):
    with open(filename) as f:
        lines = f.readlines()
    relative_name = filename[len(EXAMPLES_DIR) + 1:]
    failure_message = [
        'The file "%s" contains invalid RST: ' % relative_name,
        '',
    ]
    for error in errors:
        # This may not always be super helpful because you sometimes need
        # more than one line of context to understand what went wrong,
        # but by giving you the filename and the line number, it's usually
        # enough to track down what went wrong.
        line_number = min(error['line_number'], len(lines))
        line_number -= 1
        if line_number > 0:
            line_number -= 1
        current_message = [
            'Line %s: %s' % (error['line_number'], error['msg']),
            '  %s' % lines[line_number],
        ]
        failure_message.extend(current_message)
    return '\n'.join(failure_message)


def verify_cli_commands_valid(filename, command_validator):
    cli_commands = find_all_cli_commands(filename)
    for command in cli_commands:
        command_validator.validate_cli_command(command, filename)


def find_all_cli_commands(filename):
    document, _ = parse_rst(filename)
    visitor = CollectCLICommands(document)
    document.walk(visitor)
    return visitor.cli_commands


class CommandValidator(object):
    def __init__(self, driver):
        self.driver = driver
        help_command = self.driver.create_help_command()
        self._service_command_table = help_command.command_table
        self._global_arg_table = help_command.arg_table
        self._main_parser = MainArgParser(
            self._service_command_table, driver.session.user_agent(),
            'Some description',
            self._global_arg_table,
            prog="aws"
        )

    def validate_cli_command(self, command, filename):
        # The plan is to expand this to use the proper CLI parser and
        # parse arguments and verify them with the service model, but
        # as a first pass, we're going to verify that the service name
        # and operation match what we expect.  We can do this without
        # having to use a parser.
        self._parse_service_operation(command, filename)

    def _parse_service_operation(self, command, filename):
        try:
            command_parts = shlex.split(command)[1:]
        except Exception as e:
            raise AssertionError(
                "Failed to parse this example as shell command: %s\n\n"
                "Error:\n%s\n" % (command, e)
            )
        # Strip off the 'aws ' part and break it out into a list.
        parsed_args, remaining = self._parse_next_command(
            filename, command, command_parts, self._main_parser)
        # We know the service is good.  Parse the operation.
        cmd = self._service_command_table[parsed_args.command]
        cmd_table = cmd.create_help_command().command_table
        service_parser = ServiceArgParser(operations_table=cmd_table,
                                          service_name=parsed_args.command)
        self._parse_next_command(filename, command, remaining, service_parser)

    def _parse_next_command(self, filename, original_cmd, args_list, parser):
        # Strip off the 'aws ' part and break it out into a list.
        errors = []
        parser._print_message = lambda message, file: errors.append(
            message)
        try:
            parsed_args, remaining = parser.parse_known_args(args_list)
            return parsed_args, remaining
        except SystemExit:
            # Yes...we have to catch SystemExit. argparse raises this
            # when you have an invalid command.
            error_msg = [
                'Invalid CLI command: %s\n\n' % original_cmd,
            ]
            if errors:
                error_msg.extend(errors)
            raise AssertionError(''.join(error_msg))


class CollectCLICommands(docutils.nodes.GenericNodeVisitor):
    def __init__(self, document):
        docutils.nodes.GenericNodeVisitor.__init__(self, document)
        self.cli_commands = []

    def visit_literal_block(self, node):
        contents = node.rawsource.strip()
        if contents.startswith('aws '):
            self.cli_commands.append(contents)

    def default_visit(self, node):
        pass


def test_example_file_names():
    for root, _, files in os.walk(EXAMPLES_DIR):
        for filename in files:
            filepath = os.path.join(root, filename)
            yield (_assert_file_is_rst_or_txt, filepath)
            yield (_assert_name_contains_only_allowed_characters, filename)


def _assert_file_is_rst_or_txt(filepath):
    assert filepath.endswith('.rst') or filepath.endswith('.txt')


def _assert_name_contains_only_allowed_characters(filename):
    assert ALLOWED_FILENAME_CHAR_REGEX.match(filename)
