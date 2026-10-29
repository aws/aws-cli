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

import contextlib
import json
import os
import re
import shlex
import textwrap

import docutils.nodes
import docutils.parsers.rst
import docutils.utils
import pytest
from botocore.validate import ParamValidator

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
HTTP_LINK_REGEX = re.compile(r'`.+?<http://')
# Tokens that end the arguments passed to the CLI.  A lone "<" is a
# redirect, but "<value>" is a placeholder.
SHELL_OPERATORS = {'<', '&&', '||', ';', '&', '2>', '2>&1'}
SHELL_OPERATOR_PREFIXES = ('>', '|')

# Used by the checks that the examples follow the AWS CLI code example
# style guide: https://aws.github.io/aws-cli/docs_styleguide.html
TITLE_RE = re.compile(r'^\*\*(?:Example (?P<num>\d+): )?(?P<text>.+)\*\*$')
ERROR_LINE_RE = re.compile(r'^Line (\d+):')
LIST_ITEM_RE = re.compile(r'^(\s*(?:[*+-]|\d+\.|#\.)\s+)\S')
# An OS named as the shell the example runs in, as opposed to a resource
# such as "Windows AMIs" or "maintenance windows".
CONTENTS_HEADER_RE = re.compile(r'^Contents of ``(?P<name>[^`]+)``::$')
LOOSE_CONTENTS_HEADER_RE = re.compile(r'^Contents of\b', re.IGNORECASE)
FILE_REF_RE = re.compile(r'(?<!\w)file://(?P<path>[^\s\'"]+)')
OUTPUT_HEADER = 'Output::'
NO_OUTPUT = 'This command produces no output.'
LOOSE_OUTPUT_HEADER_RE = re.compile(r'^Output\s*:', re.IGNORECASE)
OPTION_RE = re.compile(r'(?:^|\s)--(?P<name>[A-Za-z0-9][\w-]*)')
# A pipe, redirect or command separator ends the arguments of an aws
# command, e.g. "--output text | base64 --decode".  "<value>" is a
# placeholder, not a redirect.
SHELL_OPERATOR_RE = re.compile(r'(?:^|\s)(?:\|\|?|&&|;|>>?|<)(?=\s|$)')
OS_NAME_RE = re.compile(
    r'\b(?:on|using) (?:Linux|Mac ?OS|macOS|Windows|PowerShell|Unix)\b'
)
# A link to a guide topic: `Title <https://...>`__ in the *... Guide*.
GUIDE_LINK_RE = re.compile(
    r'`[^`<]+ <https://(?:[\w-]+\.)*amazon\.com/[^>\s]*>`__ '
    r'in the \*[^*]*Guide\*\.'
)
API_REFERENCE_URL = '/apireference/'
# Placeholders from the "Sanitizing sensitive information" section.
# 123456789012, or 123456789111, 123456789222, ... for multiple accounts.
APPROVED_ACCOUNT_ID_RE = re.compile(r'^123456789(?:012|([1-9])\1\1)$')
# Not digits inside a longer ID, such as ami-066877671789bd71b.
ACCOUNT_ID_RE = re.compile(r'(?<![\w.])\d{12}(?![\w.])')
GUID_RE = re.compile(
    r'(?<![\w-])[0-9A-Za-z]{8}-[0-9A-Za-z]{4}-[0-9A-Za-z]{4}-'
    r'[0-9A-Za-z]{4}-[0-9A-Za-z]{12}(?![\w-])'
)
# a1b2c3d4-5678-90ab-cdef-EXAMPLE11111, ...-EXAMPLE22222, ...
APPROVED_GUID_RE = re.compile(r'^a1b2c3d4-5678-90ab-cdef-EXAMPLE([1-9])\1{4}$')
BUCKET_NAME_RES = [
    # Not an access point ARN, such as s3://arn:aws:s3:...
    re.compile(r's3://(?!arn:)(?P<name>[a-z0-9][a-z0-9.-]*)'),
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
# Examples that are known to break a style rule, keyed by the rule's name,
# then the file, then the example's title, with the reason for each example.
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

    @property
    def text(self):
        return ' '.join(line.strip() for line in self.lines)

    @property
    def is_command(self):
        return self.kind == 'literal' and self.lines[0].strip().startswith(
            'aws '
        )

    @property
    def runs_aws(self):
        """A command block, or a shell pipeline that runs an aws command."""
        if self.is_command:
            return True
        if self.kind != 'literal' or self.intro is None:
            return False
        # Not the output or file contents shown after a command, where a
        # table row like "|  aws  |" is not a pipeline.
        intro = self.intro.lines[-1].strip()
        if LOOSE_OUTPUT_HEADER_RE.match(intro) or intro.startswith(
            'Contents of'
        ):
            return False
        return any(
            re.search(r'\|\s*aws ', line) and not _is_table_row(line)
            for line in self.lines
        )

    @property
    def is_output(self):
        return (
            self.kind == 'literal'
            and not self.is_command
            and self.intro is not None
            and LOOSE_OUTPUT_HEADER_RE.match(self.intro.lines[-1].strip())
        )


def _is_table_row(line):
    line = line.strip()
    return line.startswith('|') and line.endswith('|')


class Section:
    def __init__(self, title):
        # The title block, or None for blocks before the first title.
        self.title = title
        self.blocks = []

    @property
    def commands(self):
        return [b for b in self.blocks if b.is_command]

    @property
    def outputs(self):
        return [b for b in self.blocks if b.is_output]


class Example:
    def __init__(self, relpath):
        self.relpath = relpath
        with open(os.path.join(EXAMPLES_DIR, relpath)) as f:
            self.lines = f.read().splitlines()
        self.blocks = _parse_blocks(self.lines)
        self.sections = _split_sections(self.blocks)

    @property
    def command_path(self):
        parts = self.relpath.split('/')
        name = parts[-1][: -len('.rst')]
        if name == '_examples':
            return parts[:-1]
        return parts[:-1] + [name]

    @property
    def commands(self):
        return [b for b in self.blocks if b.is_command]


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
            'title'
            if len(para) == 1 and TITLE_RE.match(para[0].rstrip())
            else 'para'
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


def check_location(example, command_table):
    path = example.command_path
    table = command_table
    for i, name in enumerate(path):
        if name not in table:
            break
        table = table[name].subcommand_table
    else:
        return []
    command = ' '.join(path)
    error = f'No command "aws {command}" for example file "{example.relpath}"'
    if i == len(path) - 1 and 'wait' in table:
        if name in table['wait'].subcommand_table:
            waiter_path = '/'.join(path[:i] + ['wait', name + '.rst'])
            error += f'; waiter examples belong in {waiter_path}'
    return [error]


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


def _continuation_marker(first_line):
    # Windows Command Prompt and PowerShell examples continue lines with ^
    # and ` instead of \.
    marker = first_line[-1:]
    return marker if marker in ('^', '`') else '\\'


def _is_os_specific(block):
    return _continuation_marker(block.lines[0]) != '\\'


def check_title(example):
    titles = [b for b in example.blocks if b.kind == 'title']
    if not example.blocks or example.blocks[0].kind != 'title':
        return ['Line 1: file must start with a title such as **To ...**']
    errors = []
    numbers = []
    for title in titles:
        match = TITLE_RE.match(title.lines[0].rstrip())
        text = match.group('text')
        numbers.append(match.group('num'))
        if text != text.strip():
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
        commands = section.commands
        if section.title and commands and all(map(_is_os_specific, commands)):
            title_line = section.title.lines[0].rstrip()
            if not re.search(r'\([^()]+\)\*\*$', title_line):
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


def check_description(example):
    # For waiter examples the command is "wait <waiter-name>", and for a
    # top-level command such as "login" it is the group itself.
    path = example.command_path
    command = ' '.join(path[1:]) or path[0]
    expected = f'The following ``{command}`` example'
    errors = []
    for section in example.sections:
        if section.title is None:
            continue
        paras = [b for b in section.blocks if b.kind == 'para']
        if not paras or not paras[0].text.startswith(expected):
            lineno = paras[0].lineno if paras else section.title.lineno
            errors.append(
                f'Line {lineno}: description must start with "{expected}"'
            )
    for block in example.commands:
        if not block.intro.lines[-1].rstrip().endswith('. ::'):
            lineno = block.intro.lineno + len(block.intro.lines) - 1
            errors.append(
                f"Line {lineno}: the paragraph before a command must end "
                "with '. ::'"
            )
    return errors


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


def _aws_part(command):
    """Return the lines of a command before any pipe or redirect.

    Also returns whether the next line continues the command with a pipe,
    as in "aws ecr get-login-password \\" followed by "| docker login".
    """
    for n, (_, scanned) in enumerate(command):
        _, starts_unquoted, _, unquoted = scanned
        if not starts_unquoted:
            continue
        operator = SHELL_OPERATOR_RE.search(unquoted)
        if operator:
            if unquoted[: operator.start()].strip():
                return command[: n + 1], False
            return command[:n], True
    return command, False


def check_command(example):
    errors = []
    for block in example.commands:
        for command in _split_commands(block):
            command, piped = _aws_part(command)
            last = len(command) - 1
            marker = _continuation_marker(command[0][1][0])
            for n, (lineno, scanned) in enumerate(command):
                line, starts_unquoted, ends_unquoted, unquoted = scanned
                if not starts_unquoted:
                    continue
                operator = SHELL_OPERATOR_RE.search(unquoted)
                if operator:
                    unquoted = unquoted[: operator.start()]
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
                if n == last and continued and not piped:
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
    return errors


def check_file_contents(example):
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
    for block in example.commands:
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


def _is_api_operation(command_table, path):
    """Whether ``path`` is a modeled API operation, not a custom command."""
    command = None
    for name in path:
        if name not in command_table:
            return False
        command = command_table[name]
        command_table = command.subcommand_table
    return isinstance(command, ServiceOperation)


def _operation_for(command_table, block):
    """The modeled API operation that a command block runs, if any."""
    parts = block.lines[0].split()
    if len(parts) < 3:
        return None
    service = command_table.get(parts[1])
    if service is None:
        return None
    operation = service.subcommand_table.get(parts[2])
    return operation if isinstance(operation, ServiceOperation) else None


def _as_modeled(value, shape):
    """Undo what the CLI does to output before it is printed.

    Null values are printed as null, and IAM policy documents and
    CloudFormation templates are decoded into JSON.
    """
    if shape.type_name == 'structure' and isinstance(value, dict):
        return {
            key: _as_modeled(item, shape.members[key])
            if key in shape.members
            else item
            for key, item in value.items()
            if item is not None
        }
    if shape.type_name == 'list' and isinstance(value, list):
        return [
            _as_modeled(item, shape.member)
            for item in value
            if item is not None
        ]
    if shape.type_name == 'map' and isinstance(value, dict):
        return {
            key: _as_modeled(item, shape.value)
            for key, item in value.items()
            if item is not None
        }
    # botocore's json_decode_policies (IAM) and json_decode_template_body
    # (CloudFormation GetTemplate) handlers.
    decoded = ('policyDocumentType', 'TemplateBody')
    if shape.name in decoded and isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


def _output_shape_errors(command_table, commands, block):
    """Check JSON output against the output shape of its command.

    The output is checked against the closest command before it.  Members
    that are left out are fine, since examples often show only part of the
    output, but members that don't exist and values of the wrong type are
    reported.  Output filtered by --query or shown in another --output
    format is not checked.
    """
    before = [c for c in commands if c.start < block.start]
    if not before:
        return []
    command = before[-1]
    operation = _operation_for(command_table, command)
    if operation is None or _output_format(command) not in (None, 'json'):
        return []
    options = {
        word.split('=')[0] for line in command.lines for word in line.split()
    }
    if options & {'--query', '--generate-cli-skeleton'}:
        # The output is filtered, or is a skeleton instead of a response.
        return []
    shape = operation._operation_model.output_shape
    duplicates = []

    def no_duplicates(pairs):
        keys = [key for key, _ in pairs]
        duplicates.extend(k for k in set(keys) if keys.count(k) > 1)
        return dict(pairs)

    try:
        data = json.loads(
            textwrap.dedent('\n'.join(block.lines)),
            object_pairs_hook=no_duplicates,
        )
    except ValueError:
        # Reported as invalid JSON below.
        return []
    if duplicates:
        return [
            f'Line {block.lineno}: output has duplicate keys: '
            + ', '.join(sorted(set(duplicates)))
        ]
    if shape is None or not shape.members:
        return [
            f'Line {block.lineno}: the command returns no output, so use '
            f'"{NO_OUTPUT}" instead of an "{OUTPUT_HEADER}" block'
        ]
    if not isinstance(data, dict):
        return [f'Line {block.lineno}: output must be a JSON object']
    data = _as_modeled(data, shape)
    if 'NextToken' not in shape.members:
        # Added by the CLI's own pagination, e.g. with --max-items.
        data.pop('NextToken', None)
    report = ParamValidator().validate(data, shape)
    # Service-side limits on values are not about the shape of the output.
    skipped = (
        'Missing required',
        'Invalid length',
        'Invalid range',
        'Invalid value',
    )
    return [
        f'Line {block.lineno}: output does not match the service model: '
        + line.strip()
        for line in report.generate_report().splitlines()
        if line.strip() and not line.strip().startswith(skipped)
    ]


def check_output(example, command_table):
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
        commands = [b for b in section.blocks if b.runs_aws]
        outputs = section.outputs
        paras = [b for b in section.blocks if b.kind == 'para']
        for block in paras:
            if 'produces no output' in block.text and (
                not block.text.startswith(NO_OUTPUT)
                or not commands
                or block.start < commands[0].start
            ):
                errors.append(
                    f'Line {block.lineno}: say "{NO_OUTPUT}" in its own '
                    'paragraph after the command'
                )
        if commands and not outputs:
            if not any(
                b.text.startswith(NO_OUTPUT) and b.start > commands[0].start
                for b in paras
            ):
                lineno = (section.title or commands[0]).lineno
                errors.append(
                    f'Line {lineno}: add an "{OUTPUT_HEADER}" block, or say '
                    f'"{NO_OUTPUT}" after the command'
                )
        for block in outputs:
            errors.extend(_output_shape_errors(command_table, commands, block))
        if commands and _output_format(commands[-1]) not in (None, 'json'):
            # Output in another format is not checked as JSON.
            continue
        if not _is_api_operation(command_table, example.command_path):
            # Custom commands such as "s3 cp" print plain text.
            continue
        for block in outputs:
            error = _parse_json(block)
            if error:
                errors.append(
                    f'Line {block.lineno}: output is not valid JSON: {error}'
                )
    return errors


def check_link(example):
    errors = []
    prose = ' '.join(b.text for b in example.blocks if b.kind != 'literal')
    if not GUIDE_LINK_RE.search(prose):
        titles = [b for b in example.blocks if b.kind == 'title']
        lineno = titles[0].lineno if titles else 1
        errors.append(
            f'Line {lineno}: missing a link in the format "For more '
            'information, see `Title <https://...>`__ in the *... Guide*."'
        )
    for i, line in enumerate(example.lines, 1):
        if API_REFERENCE_URL in line.lower():
            errors.append(
                f'Line {i}: link to a user or developer guide instead of '
                'the API Reference'
            )
    return errors


def check_sanitization(example):
    found = {}

    def report(kind, value, lineno):
        found.setdefault((kind, value), lineno)

    # An example that needs several regions, such as a cross-region copy,
    # can't use the single placeholder region.
    titles = [b.lineno for b in example.blocks if b.kind == 'title']
    regions = {}
    for i, line in enumerate(example.lines, 1):
        part = sum(lineno <= i for lineno in titles)
        regions.setdefault(part, set()).update(REGION_RE.findall(line))

    for i, line in enumerate(example.lines, 1):
        part = sum(lineno <= i for lineno in titles)
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
            if value != APPROVED_REGION and len(regions[part]) < 2:
                report('region', value, i)
    hints = {
        'account ID': 'use 123456789012, or 123456789111, 123456789222, '
        '... for multiple accounts',
        'GUID': 'use a1b2c3d4-5678-90ab-cdef-EXAMPLE11111, or '
        'a1b2c3d4-5678-90ab-cdef-EXAMPLE22222, ... for multiple GUIDs',
        'bucket name': 'use amzn-s3-demo-bucket, or amzn-s3-demo-bucket1, '
        'amzn-s3-demo-bucket2, ... for multiple buckets',
        'region': f'use {APPROVED_REGION}, unless the resource can only '
        'exist in a different region',
    }
    return [
        f'Line {lineno}: {kind} "{value}" is not an approved placeholder; '
        f'{hints[kind]}'
        for (kind, value), lineno in sorted(
            found.items(), key=lambda item: item[1]
        )
    ]


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


def _title(block):
    return block.lines[0].strip()[2:-2]


def _example_title(example, error):
    """The title of the example that ``error`` is in, or None."""
    match = ERROR_LINE_RE.match(error)
    if not match:
        return None
    title = None
    for block in example.blocks:
        if block.lineno > int(match.group(1)):
            break
        if block.kind == 'title':
            title = _title(block)
    return title


def _assert_follows_rule(rule, example, errors):
    exceptions = _get_exceptions(rule).get(example.relpath, {})
    excepted = set()
    remaining = []
    for error in errors:
        title = _example_title(example, error)
        if title in exceptions:
            excepted.add(title)
        else:
            remaining.append(error)
    fixed = sorted(set(exceptions) - excepted)
    assert not fixed, (
        f'These examples in {example.relpath} now follow the {rule} rule; '
        f'remove them from "{rule}" in '
        f'{os.path.basename(EXCEPTIONS_PATH)}: {fixed}'
    )
    if remaining:
        details = '\n'.join(remaining)
        raise AssertionError(
            f'The example file "{example.relpath}" does not follow the '
            f'{rule} rule:\n\n{details}\n'
        )


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


@pytest.fixture(scope="module")
def command_table():
    return create_clidriver().subcommand_table


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
                "Failed to parse this example as shell command: %s\n\n"
                "Error:\n%s\n" % (command, e)
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
    example = Example(example_file)
    errors = check_whitespace(example)
    _assert_follows_rule('whitespace', example, errors)


@pytest.mark.parametrize('example_file', STYLE_EXAMPLE_FILES)
def test_example_location(command_table, example_file):
    example = Example(example_file)
    errors = check_location(example, command_table)
    _assert_follows_rule('location', example, errors)


@pytest.mark.parametrize('example_file', STYLE_EXAMPLE_FILES)
def test_example_title(example_file):
    example = Example(example_file)
    errors = check_title(example)
    _assert_follows_rule('title', example, errors)


@pytest.mark.parametrize('example_file', STYLE_EXAMPLE_FILES)
def test_example_description(example_file):
    example = Example(example_file)
    errors = check_description(example)
    _assert_follows_rule('description', example, errors)


@pytest.mark.parametrize('example_file', STYLE_EXAMPLE_FILES)
def test_example_command(example_file):
    example = Example(example_file)
    errors = check_command(example)
    _assert_follows_rule('command', example, errors)


@pytest.mark.parametrize('example_file', STYLE_EXAMPLE_FILES)
def test_example_file_contents(example_file):
    example = Example(example_file)
    errors = check_file_contents(example)
    _assert_follows_rule('file-contents', example, errors)


@pytest.mark.parametrize('example_file', STYLE_EXAMPLE_FILES)
def test_example_output(command_table, example_file):
    example = Example(example_file)
    errors = check_output(example, command_table)
    _assert_follows_rule('output', example, errors)


@pytest.mark.parametrize('example_file', STYLE_EXAMPLE_FILES)
def test_example_link(example_file):
    example = Example(example_file)
    errors = check_link(example)
    _assert_follows_rule('link', example, errors)


@pytest.mark.parametrize('example_file', STYLE_EXAMPLE_FILES)
def test_example_sanitization(example_file):
    example = Example(example_file)
    errors = check_sanitization(example)
    _assert_follows_rule('sanitization', example, errors)


def test_example_style_exceptions_exist():
    missing = []
    for rule, files in EXCEPTIONS.items():
        for path, examples in files.items():
            if path not in STYLE_EXAMPLE_FILES:
                missing.append(f'{rule}: {path}')
                continue
            blocks = Example(path).blocks
            titles = {_title(b) for b in blocks if b.kind == 'title'}
            missing.extend(
                f'{rule}: {path}: {title}'
                for title in examples
                if title not in titles
            )
    assert not missing, f"Exceptions for examples that do not exist: {missing}"
