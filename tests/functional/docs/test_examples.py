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

import contextlib
import functools
import json
import os
import re
import shlex
import textwrap

import docutils.frontend
import docutils.nodes
import docutils.parsers.rst
import docutils.utils
import pytest

from awscli.argparser import ArgTableArgParser, MainArgParser, ServiceArgParser
from awscli.clidriver import ServiceOperation
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
BASELINE_PATH = os.path.join(
    _dname(os.path.abspath(__file__)), 'example_style_baseline.json'
)

TITLE_RE = re.compile(r'^\*\*(?:Example (?P<num>\d+): )?(?P<text>.+)\*\*$')
# An OS named as the shell the example runs in, as opposed to a resource
# such as "Windows AMIs" or "maintenance windows".
OS_NAME_RE = re.compile(
    r'\b(?:on|using) (?:Linux|Mac ?OS|macOS|Windows|PowerShell|Unix)\b'
)
LIST_ITEM_RE = re.compile(r'^(\s*(?:[*+-]|\d+\.|#\.)\s+)\S')
OUTPUT_HEADER = 'Output::'
LOOSE_OUTPUT_HEADER_RE = re.compile(r'^Output\s*:', re.IGNORECASE)
CONTENTS_HEADER_RE = re.compile(r'^Contents of ``(?P<name>[^`]+)``::$')
LOOSE_CONTENTS_HEADER_RE = re.compile(r'^Contents of\b', re.IGNORECASE)
FILE_REF_RE = re.compile(r'(?<!\w)file://(?P<path>[^\s\'"]+)')
OPTION_RE = re.compile(r'(?:^|\s)--(?P<name>[A-Za-z0-9][\w-]*)')
GUIDE_LINK_RE = re.compile(
    r'`[^`<]+ <https://(?:[\w-]+\.)*amazon\.com/[^>\s]*>`__ '
    r'in the \*[^*]*Guide\*\.'
)
API_REFERENCE_URL = '/APIReference/'
HTTP_LINK_REGEX = re.compile(r'`.+?<http://')
# Tokens that end the arguments passed to the CLI.  A lone "<" is a
# redirect, but "<value>" is a placeholder.
SHELL_OPERATORS = {'<', '&&', '||', ';', '&', '2>', '2>&1'}
SHELL_OPERATOR_PREFIXES = ('>', '|')

# Placeholders from the AWS CLI code example style guide:
# https://aws.github.io/aws-cli/docs_styleguide.html
# 123456789012, or 123456789111, 123456789222, ... for multiple accounts.
APPROVED_ACCOUNT_ID_RE = re.compile(r'^123456789(?:012|([1-9])\1\1)$')
ACCOUNT_ID_RE = re.compile(r'(?<![\d.])\d{12}(?![\d.])')
GUID_RE = re.compile(
    r'(?<![\w-])[0-9A-Za-z]{8}-[0-9A-Za-z]{4}-[0-9A-Za-z]{4}-'
    r'[0-9A-Za-z]{4}-[0-9A-Za-z]{12}(?![\w-])'
)
# a1b2c3d4-5678-90ab-cdef-EXAMPLE11111, ...-EXAMPLE22222, ...
APPROVED_GUID_RE = re.compile(r'^a1b2c3d4-5678-90ab-cdef-EXAMPLE([1-9])\1{4}$')
BUCKET_NAME_RES = [
    re.compile(r's3://(?P<name>[a-z0-9][a-z0-9.-]*)'),
    re.compile(r'arn:aws:s3:::(?P<name>[a-z0-9][a-z0-9.-]*)'),
    re.compile(r'--bucket(?:-name)?[ =]+["\']?(?P<name>[a-z0-9][a-z0-9.-]*)'),
    re.compile(r'"Bucket(?:Name)?"\s*:\s*"(?P<name>[a-z0-9][a-z0-9.-]*)"'),
]
# amzn-s3-demo-bucket, or amzn-s3-demo-bucket1, amzn-s3-demo-bucket2, ...
APPROVED_BUCKET_RE = re.compile(r'^amzn-s3-demo-bucket[1-9]?[0-9]*$')
APPROVED_REGION = 'us-west-2'
REGION_RE = re.compile(
    r'(?<![\w-])(?:us-gov|us-iso[bef]?|eusc|af|ap|ca|cn|eu|il|me|mx|sa|us)'
    r'-(?:north|south|east|west|central)(?:east|west)?-\d+(?!\d)'
)


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

    @property
    def text(self):
        return ' '.join(line.strip() for line in self.lines)

    @property
    def literal_kind(self):
        if self.kind != 'literal':
            return None
        if self.lines[0].strip().startswith('aws '):
            return 'command'
        intro = self.intro.lines[-1].strip() if self.intro else ''
        if LOOSE_OUTPUT_HEADER_RE.match(intro):
            return 'output'
        if LOOSE_CONTENTS_HEADER_RE.match(intro):
            return 'contents'
        return 'other'


class Section:
    def __init__(self, title):
        # The title block, or None for blocks before the first title.
        self.title = title
        self.blocks = []

    def literals(self, kind):
        return [b for b in self.blocks if b.literal_kind == kind]


class Example:
    def __init__(self, relpath):
        self.relpath = relpath
        with open(os.path.join(EXAMPLES_DIR, relpath), 'rb') as f:
            self.raw = f.read()
        self.contents = self.raw.decode('utf-8', errors='replace')
        self.lines = self.contents.splitlines()
        self.blocks = _parse_blocks(self.lines)
        self.sections = _split_sections(self.blocks)

    @property
    def command_path(self):
        parts = self.relpath.split('/')
        name = parts[-1][: -len('.rst')]
        if name == '_examples':
            return parts[:-1]
        return parts[:-1] + [name]

    def literals(self, kind):
        return [b for b in self.blocks if b.literal_kind == kind]

    @functools.cached_property
    def rst(self):
        """The parsed docutils document and its parse errors."""
        return parse_rst(self.contents)


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


def _split_sections(blocks):
    sections = [Section(None)]
    for block in blocks:
        if block.kind == 'title':
            sections.append(Section(block))
        else:
            sections[-1].blocks.append(block)
    if not sections[0].blocks and len(sections) > 1:
        sections.pop(0)
    return sections


def _scan_command_lines(lines):
    """Split a command block's lines into shell-aware pieces.

    Yields ``(line, starts_unquoted, ends_unquoted, unquoted_text)`` for
    each physical line, where ``unquoted_text`` is the part of the line that
    is outside of any quotes.
    """
    quote = None
    for line in lines:
        starts_unquoted = quote is None
        unquoted = []
        escaped = False
        for ch in line:
            if escaped:
                escaped = False
            elif ch == '\\' and quote != "'":
                escaped = True
            elif quote:
                if ch == quote:
                    quote = None
                continue
            elif ch in ('"', "'"):
                quote = ch
                continue
            if quote is None:
                unquoted.append(ch)
        yield line, starts_unquoted, quote is None, ''.join(unquoted)


def _split_commands(block):
    """Split a command block into the separate ``aws`` commands in it."""
    commands = []
    for offset, scanned in enumerate(_scan_command_lines(block.lines)):
        line, starts_unquoted = scanned[0], scanned[1]
        if starts_unquoted and line.strip().startswith('aws '):
            commands.append([])
        if commands:
            commands[-1].append((block.start + offset + 1, scanned))
    return commands


def _output_format(block):
    """Return the --output value of a command block, if it has one."""
    try:
        parts = shlex.split(' '.join(block.lines).replace('\\', ' '))
    except ValueError:
        return None
    for i, part in enumerate(parts):
        if part == '--output' and i + 1 < len(parts):
            return parts[i + 1]
        if part.startswith('--output='):
            return part.split('=', 1)[1]
    return None


class StyleContext:
    """Shared state for the rules that need the CLI driver."""

    @functools.cached_property
    def driver(self):
        # CLIDriver can take up a lot of resources so we'll just create one
        # instance and use it for all the rules.
        return create_clidriver()

    @functools.cached_property
    def command_table(self):
        return self.driver.subcommand_table

    @functools.cached_property
    def command_validator(self):
        return CommandValidator(self.driver)

    def find_command(self, path):
        """Return the command for ``path``, or None if there isn't one."""
        table = self.command_table
        command = None
        for name in path:
            if name not in table:
                return None
            command = table[name]
            table = command.subcommand_table
        return command

    def is_api_operation(self, path):
        return isinstance(self.find_command(path), ServiceOperation)


RULES = {}
STRICT_RULES = set()


def rule(name, strict=False):
    def register(func):
        RULES[name] = func
        if strict:
            STRICT_RULES.add(name)
        return func

    return register


# Used so that docutils doesn't write errors to stdout/stderr.
# We're collecting and reporting these via AssertionErrors messages.
class NoopWriter:
    def write(self, *args, **kwargs):
        pass


def parse_rst(contents):
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
        Validates the syntax of a CLI command by actually parsing it, which
        catches:
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
            # Only the arguments before a redirect or pipe, such as
            # "> skeleton.json", are passed to the CLI.
            for i, part in enumerate(command_parts):
                if part in SHELL_OPERATORS or part.startswith(
                    SHELL_OPERATOR_PREFIXES
                ):
                    command_parts = command_parts[:i]
                    break
        except Exception as e:
            raise AssertionError(
                "Failed to parse this example as shell command: "
                f"{command}\n\nError:\n{e}\n"
            )

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
            errors = []
            try:
                with self._cli_required_args(
                    service_name, operation_name, arg_table, remaining_args
                ):
                    operation_parser = ArgTableArgParser(arg_table)
                    operation_parser._print_message = (
                        lambda message, file: errors.append(message)
                    )
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

    @contextlib.contextmanager
    def _cli_required_args(
        self, service_name, operation_name, arg_table, args
    ):
        """Apply the CLI's rules for which arguments are required.

        Arguments such as ``--cli-input-json`` and ``--generate-cli-skeleton``
        make all other arguments optional when they are used.  The CLI does
        this in a handler for the event emitted below, which changes the
        argument table in place, so the original values are restored
        afterwards for the other examples that use the same operation.
        """
        required = {name: arg.required for name, arg in arg_table.items()}
        try:
            self.driver.session.emit(
                'before-building-argument-table-parser.'
                f'{service_name}.{operation_name}',
                argument_table=arg_table,
                args=args,
                session=self.driver.session,
            )
            yield
        finally:
            for name, arg in arg_table.items():
                arg.required = required[name]


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


@rule('ascii', strict=True)
def check_ascii(example, ctx):
    try:
        example.raw.decode('ascii')
    except UnicodeDecodeError as e:
        # The test has failed so we'll try to provide a useful error
        # message.
        offset = e.start
        spread = 20
        bad_text = example.raw[offset - spread : e.start + spread]
        underlined = ' ' * spread + '^'
        error_text = '\n'.join([repr(bad_text), underlined])
        line_number = example.raw[:offset].count(b'\n') + 1
        return [
            f'Line {line_number}: non ascii characters found:\n\n'
            f'{error_text}\n'
        ]
    return []


@rule('valid-rst', strict=True)
def check_valid_rst(example, ctx):
    _, errors = example.rst
    failure_message = []
    for error in errors:
        # This may not always be super helpful because you sometimes need
        # more than one line of context to understand what went wrong,
        # but by giving you the filename and the line number, it's usually
        # enough to track down what went wrong.
        line_number = min(error['line_number'], len(example.lines))
        line_number -= 1
        if line_number > 0:
            line_number -= 1
        failure_message.append(
            f'Line {error["line_number"]}: invalid RST: {error["msg"]}\n'
            f'  {example.lines[line_number]}'
        )
    return failure_message


@rule('cli-command', strict=True)
def check_cli_command(example, ctx):
    document, _ = example.rst
    visitor = CollectCLICommands(document)
    document.walk(visitor)
    errors = []
    for command in visitor.cli_commands:
        try:
            ctx.command_validator.validate_cli_command(
                command, example.relpath
            )
        except AssertionError as e:
            errors.append(str(e))
    return errors


@rule('no-http-links', strict=True)
def check_no_http_links(example, ctx):
    match = HTTP_LINK_REGEX.search(example.contents)
    if not match:
        return []
    contents = example.contents
    error_line_number = contents[: match.start()].count('\n') + 1
    error_line_begin = contents.rfind('\n', 0, match.start())
    error_line_end = contents.find('\n', match.end())
    error_line = contents[error_line_begin:error_line_end]
    marker_idx = error_line.find('http://') - 1
    marker_line = (' ' * marker_idx) + '^'
    return [
        f'Line {error_line_number}: found http:// link\n'
        f'{error_line}\n{marker_line}'
    ]


@rule('whitespace')
def check_whitespace(example, ctx):
    errors = []
    for i, line in enumerate(example.lines, 1):
        if '\t' in line:
            errors.append(f'Line {i}: tab character')
        if line != line.rstrip():
            errors.append(f'Line {i}: trailing whitespace')

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


@rule('location')
def check_location(example, ctx):
    path = example.command_path
    table = ctx.command_table
    for i, name in enumerate(path):
        if name not in table:
            break
        table = table[name].subcommand_table
    else:
        return []
    parent = path[:i]
    error = 'No command "aws {}" for example file "{}"'.format(
        ' '.join(path),
        example.relpath,
    )
    if i == len(path) - 1 and 'wait' in table:
        waiters = table['wait'].subcommand_table
        if name in waiters:
            error += '; waiter examples belong in {}'.format(
                '/'.join(parent + ['wait', name + '.rst'])
            )
    return [error]


@rule('title')
def check_title(example, ctx):
    titles = [b for b in example.blocks if b.kind == 'title']
    if not example.blocks or example.blocks[0].kind != 'title':
        return ['Line 1: file must start with a title such as **To ...**']
    errors = []
    numbers = []
    for title in titles:
        match = TITLE_RE.match(title.lines[0])
        text = match.group('text')
        numbers.append(match.group('num'))
        if title.lines[0] != title.lines[0].strip() or text != text.strip():
            errors.append(
                f'Line {title.lineno}: no spaces between the title and the '
                'asterisks'
            )
        if not text.strip().startswith('To '):
            errors.append(
                f"Line {title.lineno}: title must start with 'To ', e.g. "
                '**To ...** or **Example 1: To ...**'
            )
        suffix = re.search(r'\([^()]*\)$', text)
        prefix = text[: suffix.start()] if suffix else text
        if OS_NAME_RE.search(prefix):
            errors.append(
                f'Line {title.lineno}: put the OS name in a parenthesized '
                'suffix, e.g. **To ... (Linux and macOS)**'
            )
    for section in example.sections:
        commands = section.literals('command')
        if section.title and commands and all(map(_is_os_specific, commands)):
            if not re.search(r'\([^()]+\)\*\*$', section.title.lines[0]):
                errors.append(
                    f'Line {section.title.lineno}: commands that are not for '
                    'Linux must name the OS in the title, e.g. '
                    '**To ... (Windows)**'
                )
    if len(titles) > 1:
        expected = [str(n) for n in range(1, len(titles) + 1)]
        if numbers != expected:
            errors.append(
                'Titles must be numbered Example 1: to Example {}:, '
                'found {}'.format(
                    len(titles), ', '.join(n or '(none)' for n in numbers)
                )
            )
    return errors


def _continuation_marker(first_line):
    # Windows Command Prompt and PowerShell examples continue lines with ^
    # and ` instead of \.
    marker = first_line[-1:]
    return marker if marker in ('^', '`') else '\\'


def _is_os_specific(block):
    return _continuation_marker(block.lines[0]) != '\\'


@rule('description')
def check_description(example, ctx):
    path = example.command_path
    # Waiter examples use "wait <waiter-name>".
    names = [' '.join(path[1:])]
    expected = f'``{names[0]}``'
    errors = []
    for section in example.sections:
        if section.title is None:
            continue
        paras = [b for b in section.blocks if b.kind == 'para']
        if not paras or not any(
            paras[0].text.startswith(f'The following ``{name}`` example')
            for name in names
        ):
            lineno = paras[0].lineno if paras else section.title.lineno
            errors.append(
                f'Line {lineno}: description must start with '
                f'"The following {expected} example"'
            )
    for block in example.literals('command'):
        if not block.intro.lines[-1].rstrip().endswith('. ::'):
            lineno = block.intro.lineno + len(block.intro.lines) - 1
            errors.append(
                f"Line {lineno}: the paragraph before a command must end "
                "with '. ::'"
            )
    return errors


@rule('command')
def check_command(example, ctx):
    errors = []
    for block in example.literals('command'):
        for command in _split_commands(block):
            last = len(command) - 1
            marker = _continuation_marker(command[0][1][0])
            for n, (lineno, scanned) in enumerate(command):
                line, starts_unquoted, ends_unquoted, unquoted = scanned
                if not starts_unquoted:
                    continue
                expected_indent = 4 if n == 0 else 8
                if _indent(line) != expected_indent:
                    errors.append(
                        f'Line {lineno}: expected an indent of '
                        f'{expected_indent} spaces'
                    )
                continued = line.endswith(marker)
                if (
                    n < last
                    and ends_unquoted
                    and not line.endswith(' ' + marker)
                ):
                    errors.append(
                        f'Line {lineno}: continued lines must end with '
                        f"' {marker}'"
                    )
                if n == last and continued:
                    errors.append(
                        f'Line {lineno}: the last line must not end with '
                        f"'{marker}'"
                    )
                options = [
                    m.group('name') for m in OPTION_RE.finditer(unquoted)
                ]
                if n == 0 and options:
                    errors.append(
                        f'Line {lineno}: put parameters on the following '
                        'lines, not on the first line with the command'
                    )
                elif n > 0 and not line.strip().startswith('--'):
                    errors.append(
                        f'Line {lineno}: each continued line must start with '
                        'a --parameter'
                    )
                if len(options) > 1:
                    found = ', '.join('--' + o for o in options)
                    errors.append(
                        f'Line {lineno}: put each parameter on its own line, '
                        f'found {found}'
                    )
                for option in options:
                    if option in ('output', 'region'):
                        errors.append(
                            f'Line {lineno}: avoid --{option}; examples '
                            'should use the default configuration'
                        )
    return errors


@rule('file-contents')
def check_file_contents(example, ctx):
    shown = set()
    errors = []
    for block in example.blocks:
        if block.kind != 'para':
            continue
        header = block.lines[-1].strip()
        match = CONTENTS_HEADER_RE.match(header)
        if match:
            shown.add(match.group('name'))
            shown.add(os.path.basename(match.group('name')))
            if block.lines[-1][:1].isspace():
                lineno = block.lineno + len(block.lines) - 1
                errors.append(
                    f'Line {lineno}: the "Contents of" line must not be '
                    'indented'
                )
        elif LOOSE_CONTENTS_HEADER_RE.match(header) and header.endswith('::'):
            lineno = block.lineno + len(block.lines) - 1
            errors.append(
                f'Line {lineno}: use the format "Contents of ``<file>``::"'
            )
    for block in example.literals('command'):
        for offset, line in enumerate(block.lines):
            for match in FILE_REF_RE.finditer(line):
                ref = match.group('path')
                if ref in shown or os.path.basename(ref) in shown:
                    continue
                name = os.path.basename(ref)
                errors.append(
                    f'Line {block.lineno + offset}: file://{ref} has no '
                    f'"Contents of ``{name}``::" block'
                )
    return errors


@rule('output')
def check_output(example, ctx):
    errors = []
    for block in example.blocks:
        if block.kind != 'para':
            continue
        # The header must not be indented.
        header = block.lines[-1].rstrip()
        if (
            LOOSE_OUTPUT_HEADER_RE.match(header.lstrip())
            and header != OUTPUT_HEADER
        ):
            lineno = block.lineno + len(block.lines) - 1
            errors.append(
                f'Line {lineno}: use "{OUTPUT_HEADER}" as the output header, '
                f'found "{header}"'
            )
    for section in example.sections:
        commands = section.literals('command')
        outputs = section.literals('output')
        if commands and not outputs:
            text = ' '.join(b.text for b in section.blocks if b.kind == 'para')
            if 'produces no output' not in text:
                lineno = (section.title or commands[0]).lineno
                errors.append(
                    f'Line {lineno}: add an "{OUTPUT_HEADER}" block, or say '
                    'the command "produces no output"'
                )
        if commands and _output_format(commands[-1]) not in (None, 'json'):
            # Non-JSON output is reported by the command rule.
            continue
        if not ctx.is_api_operation(example.command_path):
            # Custom commands such as "s3 cp" print plain text.
            continue
        for block in outputs:
            error = _parse_json(block)
            if error:
                errors.append(
                    f'Line {block.lineno}: output is not valid JSON: {error}'
                )
    return errors


@rule('link')
def check_link(example, ctx):
    errors = []
    prose = ' '.join(b.text for b in example.blocks if b.kind != 'literal')
    if not GUIDE_LINK_RE.search(prose):
        errors.append(
            'Missing a link in the format "For more information, see '
            '`Title <https://...>`__ in the *... Guide*."'
        )
    for i, line in enumerate(example.lines, 1):
        if API_REFERENCE_URL in line:
            errors.append(
                f'Line {i}: link to a user or developer guide instead of '
                'the API Reference'
            )
    return errors


@rule('sanitization')
def check_sanitization(example, ctx):
    found = {}

    def report(kind, value, lineno):
        found.setdefault((kind, value), lineno)

    for i, line in enumerate(example.lines, 1):
        for value in ACCOUNT_ID_RE.findall(line):
            if not APPROVED_ACCOUNT_ID_RE.match(value):
                report('account ID', value, i)
        for value in GUID_RE.findall(line):
            if not APPROVED_GUID_RE.match(value):
                report('GUID', value, i)
        for regex in BUCKET_NAME_RES:
            for match in regex.finditer(line):
                if not APPROVED_BUCKET_RE.match(match.group('name')):
                    report('bucket name', match.group('name'), i)
        for value in REGION_RE.findall(line):
            if value != APPROVED_REGION:
                report('region', value, i)
    hints = {
        'account ID': 'use 123456789012, or 123456789111, 123456789222, '
        '... for multiple accounts',
        'GUID': 'use a1b2c3d4-5678-90ab-cdef-EXAMPLE11111, or '
        'a1b2c3d4-5678-90ab-cdef-EXAMPLE22222, ... for multiple GUIDs',
        'bucket name': 'use amzn-s3-demo-bucket, or amzn-s3-demo-bucket1, '
        'amzn-s3-demo-bucket2, ... for multiple buckets',
        'region': f'use {APPROVED_REGION}',
    }
    return [
        f'Line {lineno}: {kind} "{value}" is not an approved placeholder; '
        f'{hints[kind]}'
        for (kind, value), lineno in sorted(
            found.items(), key=lambda item: item[1]
        )
    ]


def _get_rst_files():
    rst_files = []
    for root, _, filenames in os.walk(EXAMPLES_DIR):
        for filename in filenames:
            if filename.startswith('.') or not filename.endswith('.rst'):
                # Ignore hidden files as it starts with "."
                continue
            relpath = os.path.relpath(
                os.path.join(root, filename), EXAMPLES_DIR
            )
            rst_files.append(relpath.replace(os.sep, '/'))
    return sorted(rst_files)


def _is_example(relpath):
    # Command descriptions and the global option docs at the top level are
    # not examples.
    return '/' in relpath and not _is_description(relpath.split('/')[-1])


def _is_description(filename):
    if filename == '_examples.rst':
        return False
    return filename.startswith('_') or filename.endswith('_description.rst')


def _load_baseline():
    if not os.path.isfile(BASELINE_PATH):
        return {}
    with open(BASELINE_PATH) as f:
        return {name: set(paths) for name, paths in json.load(f).items()}


RST_FILES = _get_rst_files()
EXAMPLE_FILES = [path for path in RST_FILES if _is_example(path)]
BASELINE = _load_baseline()


@functools.cache
def _get_example(relpath):
    return Example(relpath)


def find_violations(rule_name, relpath, ctx):
    return RULES[rule_name](_get_example(relpath), ctx)


@pytest.fixture(scope='module')
def style_context():
    return StyleContext()


def _assert_follows_rule(rule_name, relpath, ctx):
    errors = find_violations(rule_name, relpath, ctx)
    baselined = BASELINE.get(rule_name, ())
    if rule_name not in STRICT_RULES and relpath in baselined:
        if not errors:
            pytest.fail(
                f'{relpath} now follows the {rule_name} rule; remove it '
                f'from {os.path.basename(BASELINE_PATH)}'
            )
        return
    if errors:
        details = '\n'.join(errors)
        raise AssertionError(
            f'The example file "{relpath}" does not follow the {rule_name} '
            f'rule:\n\n{details}\n'
        )


@pytest.mark.parametrize('example_file', RST_FILES)
def test_example_ascii(style_context, example_file):
    _assert_follows_rule('ascii', example_file, style_context)


@pytest.mark.filterwarnings('ignore::DeprecationWarning')
@pytest.mark.parametrize('example_file', RST_FILES)
def test_example_valid_rst(style_context, example_file):
    _assert_follows_rule('valid-rst', example_file, style_context)


@pytest.mark.filterwarnings('ignore::DeprecationWarning')
@pytest.mark.parametrize('example_file', RST_FILES)
def test_example_cli_command(style_context, example_file):
    _assert_follows_rule('cli-command', example_file, style_context)


@pytest.mark.parametrize('example_file', RST_FILES)
def test_example_no_http_links(style_context, example_file):
    _assert_follows_rule('no-http-links', example_file, style_context)


@pytest.mark.parametrize('example_file', EXAMPLE_FILES)
def test_example_whitespace(style_context, example_file):
    _assert_follows_rule('whitespace', example_file, style_context)


@pytest.mark.parametrize('example_file', EXAMPLE_FILES)
def test_example_location(style_context, example_file):
    _assert_follows_rule('location', example_file, style_context)


@pytest.mark.parametrize('example_file', EXAMPLE_FILES)
def test_example_title(style_context, example_file):
    _assert_follows_rule('title', example_file, style_context)


@pytest.mark.parametrize('example_file', EXAMPLE_FILES)
def test_example_description(style_context, example_file):
    _assert_follows_rule('description', example_file, style_context)


@pytest.mark.parametrize('example_file', EXAMPLE_FILES)
def test_example_command(style_context, example_file):
    _assert_follows_rule('command', example_file, style_context)


@pytest.mark.parametrize('example_file', EXAMPLE_FILES)
def test_example_file_contents(style_context, example_file):
    _assert_follows_rule('file-contents', example_file, style_context)


@pytest.mark.parametrize('example_file', EXAMPLE_FILES)
def test_example_output(style_context, example_file):
    _assert_follows_rule('output', example_file, style_context)


@pytest.mark.parametrize('example_file', EXAMPLE_FILES)
def test_example_link(style_context, example_file):
    _assert_follows_rule('link', example_file, style_context)


@pytest.mark.parametrize('example_file', EXAMPLE_FILES)
def test_example_sanitization(style_context, example_file):
    _assert_follows_rule('sanitization', example_file, style_context)


def test_baseline_is_current():
    unknown_rules = set(BASELINE) - set(RULES)
    assert not unknown_rules, f'Unknown rules in baseline: {unknown_rules}'
    strict_rules = sorted(name for name in STRICT_RULES if BASELINE.get(name))
    assert (
        not strict_rules
    ), f'Strict rules cannot be baselined: {strict_rules}'
    missing = sorted(
        path
        for paths in BASELINE.values()
        for path in paths
        if path not in EXAMPLE_FILES
    )
    assert not missing, (
        'Baselined example files no longer exist:\n' + '\n'.join(missing)
    )


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
    doc_examples = []
    for root, _, filenames in os.walk(EXAMPLES_DIR):
        for filename in filenames:
            if filename.startswith('.'):
                # Ignore hidden files as it starts with "."
                continue
            doc_examples.append(os.path.join(root, filename))
    return doc_examples


DOC_EXAMPLES = _get_all_doc_examples()
EXAMPLE_COMMAND_TESTS = _get_example_test_cases()


@pytest.mark.parametrize("command, subcommand", EXAMPLE_COMMAND_TESTS)
def test_examples(command, subcommand):
    t = _ExampleTests(methodName='noop_test')
    t.setUp()
    try:
        t.driver.main([command, subcommand, 'help'])
        t.assert_contains_with_count('========\nExamples\n========', 1)
    finally:
        t.tearDown()


@pytest.mark.parametrize("example_file", DOC_EXAMPLES)
def test_example_file_name(example_file):
    filename = example_file.split(os.sep)[-1]
    _assert_file_is_rst_or_txt(example_file)
    _assert_name_contains_only_allowed_characters(filename)


def _assert_file_is_rst_or_txt(filepath):
    assert filepath.endswith('.rst') or filepath.endswith('.txt')


def _assert_name_contains_only_allowed_characters(filename):
    assert ALLOWED_FILENAME_CHAR_REGEX.match(filename)
