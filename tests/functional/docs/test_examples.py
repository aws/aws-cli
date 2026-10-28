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

import json
import os
import re
import shlex
import textwrap

import docutils.nodes
import docutils.parsers.rst
import docutils.utils
import pytest

from awscli.argparser import ArgTableArgParser, MainArgParser, ServiceArgParser
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
    'emr': [
        'add-steps',
        'create-default-roles',
        'describe-cluster',
        'schedule-hbase-backup',
    ],
}
_dname = os.path.dirname
EXAMPLES_DIR = os.path.join(
    _dname(_dname(_dname(_dname(os.path.abspath(__file__))))),
    'awscli',
    'examples',
)

ALLOWED_FILENAME_CHAR_REGEX = re.compile(r'([a-z0-9_\-\.]*$)')
HTTP_LINK_REGEX = re.compile(r'`.+?<http://')

# Used by the checks that the examples follow the AWS CLI code example
# style guide: https://aws.github.io/aws-cli/docs_styleguide.html
TITLE_RE = re.compile(r'^\*\*(?:Example (?P<num>\d+): )?(?P<text>.+)\*\*$')
LIST_ITEM_RE = re.compile(r'^(\s*(?:[*+-]|\d+\.|#\.)\s+)\S')
# Files that are known to break a style rule, keyed by the rule's name, with
# the reason for each file.
EXCEPTIONS_PATH = os.path.join(
    _dname(os.path.abspath(__file__)), 'example_style_exceptions.json'
)


# Used so that docutils doesn't write errors to stdout/stderr.
# We're collecting and reporting these via AssertionErrors messages.
class NoopWriter:
    def write(self, *args, **kwargs):
        pass


class _ExampleTests(BaseAWSHelpOutputTest):
    def noop_test(self):
        pass


def _get_example_test_cases():
    test_cases = []
    for command, subcommands in COMMAND_EXAMPLES.items():
        for subcommand in subcommands:
            test_cases.append((command, subcommand))
    return test_cases


def _get_all_doc_examples():
    rst_doc_examples = []
    other_doc_examples = []
    # Iterate over all rst doc examples
    for root, _, filenames in os.walk(EXAMPLES_DIR):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            if filename.startswith('.'):
                # Ignore hidden files as it starts with "."
                continue
            if not filename.endswith('.rst'):
                other_doc_examples.append(full_path)
                continue
            rst_doc_examples.append(full_path)
    return rst_doc_examples, other_doc_examples


class Block:
    def __init__(self, kind, start, lines, intro=None):
        # kind is one of 'title', 'para' or 'literal'.
        self.kind = kind
        # 0-based index of the block's first line in the file.
        self.start = start
        self.lines = lines
        # For literal blocks, the paragraph that ends with '::'.
        self.intro = intro

    @property
    def lineno(self):
        return self.start + 1


class Example:
    def __init__(self, relpath):
        self.relpath = relpath
        with open(os.path.join(EXAMPLES_DIR, relpath)) as f:
            self.lines = f.read().splitlines()
        self.blocks = _parse_blocks(self.lines)


def _indent(line):
    return len(line) - len(line.lstrip(' '))


def _parse_blocks(lines):
    blocks = []
    i = 0
    intro = None
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        if intro is not None and lines[i][:1] in (' ', '\t'):
            end = i
            while end < len(lines) and (
                not lines[end].strip() or lines[end][:1] in (' ', '\t')
            ):
                end += 1
            last = end
            while not lines[last - 1].strip():
                last -= 1
            blocks.append(Block('literal', i, lines[i:last], intro))
            intro = None
            i = end
            continue
        end = i
        while end < len(lines) and lines[end].strip():
            end += 1
        para = lines[i:end]
        kind = (
            'title' if len(para) == 1 and TITLE_RE.match(para[0]) else 'para'
        )
        block = Block(kind, i, para)
        blocks.append(block)
        intro = block if para[-1].rstrip().endswith('::') else None
        i = end
    return blocks


def _indent_error(lineno, indent):
    return f'Line {lineno}: indent of {indent} spaces is not a multiple of 4'


def _is_json(block):
    return _parse_json(block) is None


def _parse_json(block):
    """Return None if the block is JSON, otherwise the parse error."""
    try:
        json.loads(textwrap.dedent('\n'.join(block.lines)))
    except ValueError as e:
        return str(e)
    return None


def check_whitespace(example):
    errors = []
    for i, line in enumerate(example.lines, 1):
        indentation = line[: len(line) - len(line.lstrip())]
        if line.strip() and '\t' in indentation:
            errors.append(f'Line {i}: tab used for indentation')

    list_offsets = set()
    for block in example.blocks:
        if block.kind == 'title':
            list_offsets = set()
        if block.start > 0 and example.lines[block.start - 1].strip():
            errors.append(
                f'Line {block.lineno}: missing blank line before this section'
            )
        if block.kind == 'para':
            for offset, line in enumerate(block.lines):
                lineno = block.lineno + offset
                if offset < len(block.lines) - 1 and TITLE_RE.match(line):
                    errors.append(
                        f'Line {lineno}: missing blank line after title'
                    )
                elif offset < len(block.lines) - 1 and line.endswith('::'):
                    errors.append(
                        f"Line {lineno}: missing blank line after '::'"
                    )
                list_item = LIST_ITEM_RE.match(line)
                if list_item:
                    list_offsets.add(len(list_item.group(1)))
                indent = _indent(line)
                if indent % 4 and indent not in list_offsets:
                    errors.append(_indent_error(lineno, indent))
        elif block.kind == 'literal':
            if _is_json(block):
                lines = enumerate(block.lines)
            else:
                # Only the base indent matters for text output, where
                # columns are aligned to the content.
                lines = [(0, block.lines[0])]
            for offset, line in lines:
                indent = _indent(line)
                if line.strip() and indent % 4:
                    errors.append(_indent_error(block.lineno + offset, indent))
    return errors


def _is_description(filename):
    if filename == '_examples.rst':
        return False
    return filename.startswith('_') or filename.endswith('_description.rst')


def _get_style_example_files():
    example_files = []
    for root, _, filenames in os.walk(EXAMPLES_DIR):
        if root == EXAMPLES_DIR:
            # The global option docs at the top level are not examples.
            continue
        for filename in filenames:
            if filename.startswith('.') or not filename.endswith('.rst'):
                continue
            if _is_description(filename):
                continue
            relpath = os.path.relpath(
                os.path.join(root, filename), EXAMPLES_DIR
            )
            example_files.append(relpath.replace(os.sep, '/'))
    return sorted(example_files)


def _load_exceptions():
    with open(EXCEPTIONS_PATH) as f:
        return json.load(f)


def _get_exceptions(rule):
    return EXCEPTIONS.get(rule, {})


RST_DOC_EXAMPLES, OTHER_DOC_EXAMPLES = _get_all_doc_examples()
EXAMPLE_COMMAND_TESTS = _get_example_test_cases()
STYLE_EXAMPLE_FILES = _get_style_example_files()
EXCEPTIONS = _load_exceptions()


def line_num(content, loc):
    return content[:loc].count('\n') + 1


def extract_error_line(content, error_start, error_end):
    error_line_begin = content.rfind('\n', 0, error_start)
    error_line_end = content.find('\n', error_end)
    return content[error_line_begin:error_line_end]


@pytest.fixture(scope="module")
def command_validator():
    # CLIDriver can take up a lot of resources so we'll just create one
    # instance and use it for all the validation tests.
    driver = create_clidriver()
    return CommandValidator(driver)


@pytest.mark.parametrize("command, subcommand", EXAMPLE_COMMAND_TESTS)
def test_examples(command, subcommand):
    t = _ExampleTests(methodName='noop_test')
    t.setUp()
    try:
        t.driver.main([command, subcommand, 'help'])
        t.assert_contains_with_count('========\nExamples\n========', 1)
    finally:
        t.tearDown()


@pytest.mark.filterwarnings('ignore::DeprecationWarning')
@pytest.mark.parametrize("example_file", RST_DOC_EXAMPLES)
def test_rst_doc_examples(command_validator, example_file):
    verify_has_only_ascii_chars(example_file)
    verify_is_valid_rst(example_file)
    verify_cli_commands_valid(example_file, command_validator)
    verify_no_http_links(example_file)


def verify_no_http_links(filename):
    with open(filename) as f:
        contents = f.read()
    match = HTTP_LINK_REGEX.search(contents)
    if match:
        error_line_number = line_num(contents, match.span()[0])
        error_line = extract_error_line(
            contents, match.span()[0], match.span()[1]
        )
        marker_idx = error_line.find('http://') - 1
        marker_line = (" " * marker_idx) + '^'
        raise AssertionError(
            'Found http:// link in the examples file %s, line %s\n'
            '%s\n%s' % (filename, error_line_number, error_line, marker_line)
        )


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
            bad_text = bytes_content[offset - spread : e.start + spread]
            underlined = ' ' * spread + '^'
            error_text = '\n'.join([bad_text, underlined])
            line_number = bytes_content[:offset].count(b'\n') + 1
            raise AssertionError(
                "Non ascii characters found in the examples file %s, line %s:"
                "\n\n%s\n" % (filename, line_number, error_text)
            )


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
        components=components
    ).get_default_values()
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
    relative_name = filename[len(EXAMPLES_DIR) + 1 :]
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


class CommandValidator:
    def __init__(self, driver):
        self.driver = driver
        help_command = self.driver.create_help_command()
        self._service_command_table = help_command.command_table
        self._global_arg_table = help_command.arg_table
        self._main_parser = MainArgParser(
            self._service_command_table,
            driver.session.user_agent(),
            'Some description',
            self._global_arg_table,
            prog="aws",
        )

    def validate_cli_command(self, command, filename):
        """
        Validates the syntax of a CLI command by actually parsing it, which catches:
        - Invalid service names
        - Invalid operation names
        - Missing required arguments
        - Invalid argument names
        - Malformed argument syntax
        """
        try:
            command_parts = shlex.split(command)[1:]
            # Strip newlines from arguments that may have been included due to
            # backslash line continuations in the RST examples
            command_parts = [part.lstrip('\n') for part in command_parts]
        except Exception as e:
            raise AssertionError(
                "Failed to parse this example as shell command: %s\n\n"
                "Error:\n%s\n" % (command, e)
            )

        # TODO - for now skip validation if command uses
        # --cli-input-json, --cli-input-yaml, or --generate-cli-skeleton
        if any(
            arg.startswith('--cli-input-json')
            or arg.startswith('--cli-input-yaml')
            or arg == '--generate-cli-skeleton'
            for arg in command_parts
        ):
            return

        try:
            # Parse global args
            parsed_args, remaining = self._main_parser.parse_known_args(
                command_parts
            )
            service_name = parsed_args.command

            # Get the service command
            service_cmd = self._service_command_table[service_name]

            # Create the service parser
            cmd_table = service_cmd.create_help_command().command_table
            if not cmd_table:
                # Top-level commands without sub-operations (e.g. login)
                return
            service_parser = ServiceArgParser(
                operations_table=cmd_table, service_name=service_name
            )

            # Parse the operation
            parsed_operation, remaining_args = service_parser.parse_known_args(
                remaining
            )

            if not hasattr(parsed_operation, 'operation'):
                # Not a standard operation (might be help, wait, etc.)
                return

            operation_name = parsed_operation.operation
            operation_cmd = cmd_table[operation_name]

            # Validate all arguments using the operation's argument parser
            arg_table = operation_cmd.arg_table
            operation_parser = ArgTableArgParser(arg_table)

            errors = []
            operation_parser._print_message = (
                lambda message, file: errors.append(message)
            )

            try:
                operation_parser.parse_known_args(remaining_args)
            except (SystemExit, Exception) as e:
                error_msg = [
                    f'Invalid CLI command: {command}\n\n',
                    f'File: {filename}\n\n',
                ]
                if errors:
                    error_msg.extend(errors)
                else:
                    error_msg.append(f'Error: {e}\n')
                raise AssertionError(''.join(error_msg))

        except Exception as e:
            raise AssertionError(
                f"Failed to validate command: {command}\n"
                f"File: {filename}\n"
                f"Error: {e}"
            )


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


@pytest.mark.parametrize("example_file", RST_DOC_EXAMPLES + OTHER_DOC_EXAMPLES)
def test_example_file_name(example_file):
    filename = example_file.split(os.sep)[-1]
    _assert_file_is_rst_or_txt(example_file)
    _assert_name_contains_only_allowed_characters(filename)


def _assert_file_is_rst_or_txt(filepath):
    assert filepath.endswith('.rst') or filepath.endswith('.txt')


def _assert_name_contains_only_allowed_characters(filename):
    assert ALLOWED_FILENAME_CHAR_REGEX.match(filename)


@pytest.mark.parametrize('example_file', STYLE_EXAMPLE_FILES)
def test_example_whitespace(example_file):
    errors = check_whitespace(Example(example_file))
    if example_file in _get_exceptions('whitespace'):
        assert errors, (
            f'{example_file} now follows the whitespace rule; remove it '
            f'from "whitespace" in {os.path.basename(EXCEPTIONS_PATH)}'
        )
        return
    if errors:
        details = '\n'.join(errors)
        raise AssertionError(
            f'The example file "{example_file}" does not follow the '
            f'whitespace rule:\n\n{details}\n'
        )


def test_example_style_exceptions_exist():
    missing = sorted(
        f'{rule}: {path}'
        for rule, paths in EXCEPTIONS.items()
        for path in paths
        if path not in STYLE_EXAMPLE_FILES
    )
    assert not missing, f"Exceptions for files that do not exist: {missing}"
