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
import json
import os
import sys
from argparse import Namespace

import pytest
from botocore.paginate import PageIterator
from ruamel.yaml import YAML

from awscli.compat import StringIO, contextlib
from awscli.formatter import (
    JSONFormatter,
    OffFormatter,
    StreamedYAMLFormatter,
    YAMLDumper,
    get_formatter,
)
from awscli.testutils import mock, unittest


class FakePageIterator(PageIterator):
    def __init__(self, responses):
        self._responses = responses

    def __iter__(self):
        for response in self._responses:
            yield response


class TestYAMLDumper(unittest.TestCase):
    def setUp(self):
        self.dumper = YAMLDumper()
        self.output = StringIO()

    def test_dump_int(self):
        self.dumper.dump(1, self.output)
        self.assertEqual(self.output.getvalue(), '1\n')

    def test_dump_float(self):
        self.dumper.dump(1.2, self.output)
        self.assertEqual(self.output.getvalue(), '1.2\n')

    def test_dump_bool(self):
        self.dumper.dump(True, self.output)
        self.assertEqual(self.output.getvalue(), 'true\n')

    def test_dump_str(self):
        self.dumper.dump('foo', self.output)
        self.assertEqual(self.output.getvalue(), '"foo"\n')

    def test_dump_structure(self):
        self.dumper.dump({'key': 'val'}, self.output)
        self.assertEqual(self.output.getvalue(), 'key: val\n')

    def test_dump_list(self):
        self.dumper.dump(['val1', 'val2'], self.output)
        self.assertEqual(self.output.getvalue(), '- val1\n- val2\n')


class TestStreamedYAMLFormatter:
    def setup_method(self):
        self.args = Namespace(query=None)
        self.formatter = StreamedYAMLFormatter(self.args)
        self.output = StringIO()

    def test_format_single_response(self):
        response = {'TableNames': ['MyTable']}
        self.formatter('list-tables', response, self.output)
        assert self.output.getvalue() == ('- TableNames:\n  - MyTable\n')

    def test_format_paginated_response(self):
        response = FakePageIterator(
            [
                {'TableNames': ['MyTable']},
                {'TableNames': ['MyTable2']},
            ]
        )
        self.formatter('list-tables', response, self.output)
        assert self.output.getvalue() == (
            '- TableNames:\n  - MyTable\n- TableNames:\n  - MyTable2\n'
        )

    def test_flushes_after_io_error(self):
        io_error_dumper = mock.Mock(YAMLDumper)
        mock_output = mock.Mock()
        io_error_dumper.dump.side_effect = OSError()
        response = {'TableNames': ['MyTable']}
        formatter = StreamedYAMLFormatter(self.args, io_error_dumper)
        formatter('list-tables', response, mock_output)
        assert mock_output.flush.called

    def test_stops_paginating_after_io_error(self):
        io_error_dumper = mock.Mock(YAMLDumper)
        mock_output = mock.Mock()
        io_error_dumper.dump.side_effect = OSError()
        response = FakePageIterator(
            [
                {'TableNames': ['MyTable']},
                {'TableNames': ['MyTable2']},
            ]
        )
        formatter = StreamedYAMLFormatter(self.args, io_error_dumper)
        formatter('list-tables', response, mock_output)
        # The dumper should have only been called once as the io error is
        # immediately raised and we should not have kept paginating.
        assert len(io_error_dumper.dump.call_args_list) == 1
        assert mock_output.flush.called

    @pytest.mark.parametrize(
        'env_vars',
        [
            {'AWS_CLI_OUTPUT_ENCODING': 'UTF-8'},
            {'PYTHONUTF8': '1'},
        ],
    )
    def test_encoding_override(self, env_vars):
        response = {'TableNames': ['桌子']}
        stdout_b = io.BytesIO()
        stdout = io.TextIOWrapper(stdout_b, encoding="cp1252", newline='\n')

        formatter = StreamedYAMLFormatter(self.args)
        with mock.patch.dict(os.environ, env_vars):
            with contextlib.redirect_stdout(stdout):
                assert 'cp1252' == sys.stdout.encoding
                formatter('list-tables', response, sys.stdout)
                # we expect the formatter to have changed the output stream
                # encoding based on AWS_CLI_OUTPUT_ENCODING
                assert 'UTF-8' == sys.stdout.encoding
                stdout.flush()

        assert stdout_b.getvalue() == ('- TableNames:\n  - 桌子\n').encode()


class TestJSONFormatter:
    def setup_method(self):
        self.args = Namespace(query=None)
        self.formatter = JSONFormatter(self.args)

    @pytest.mark.parametrize(
        'env_vars',
        [
            {'AWS_CLI_OUTPUT_ENCODING': 'UTF-8'},
            {'PYTHONUTF8': '1'},
        ],
    )
    def test_encoding_override(self, env_vars):
        """
        StreamedYAMLFormatter is tested above since it doesn't inherit from
        FullyBufferedFormatter, this is implicitly testing all other
        formatters that do.
        """
        response = {'TableNames': ['桌子']}
        stdout_b = io.BytesIO()
        stdout = io.TextIOWrapper(stdout_b, encoding="cp1252", newline='\n')

        with mock.patch.dict(os.environ, env_vars):
            with contextlib.redirect_stdout(stdout):
                assert 'cp1252' == sys.stdout.encoding
                self.formatter('list-tables', response, sys.stdout)
                # we expect the formatter to have changed the output stream
                # encoding based on AWS_CLI_OUTPUT_ENCODING
                assert 'UTF-8' == sys.stdout.encoding
                stdout.flush()

        assert (
            stdout_b.getvalue()
            == ('{\n    "TableNames": [\n        "桌子"\n    ]\n}\n').encode()
        )


class TestOffFormatter:
    def setup_method(self):
        self.args = Namespace(query=None)
        self.formatter = OffFormatter(self.args)
        self.output = StringIO()

    def test_suppresses_response(self):
        response = {'Key': 'Value'}
        self.formatter('test-command', response, self.output)
        assert self.output.getvalue() == ''

    def test_suppresses_paginated_response(self):
        response = FakePageIterator(
            [{'Items': ['Item1']}, {'Items': ['Item2']}]
        )
        self.formatter('test-command', response, self.output)
        assert self.output.getvalue() == ''

    def test_works_without_stream(self):
        response = {'Key': 'Value'}
        # Should not raise an exception
        self.formatter('test-command', response, None)


NON_ENCODABLE = 'arrow → accent é emoji \U0001f600'


def _format(output, response, encoding):
    """Format ``response`` onto a stream restricted to ``encoding``."""
    raw = io.BytesIO()
    stream = io.TextIOWrapper(
        raw, encoding=encoding, errors='backslashreplace'
    )
    args = Namespace(query=None, color='off', output=output)
    get_formatter(output, args)('command-name', response, stream)
    stream.flush()
    return raw.getvalue().decode(encoding)


@pytest.mark.parametrize('output', ['json', 'yaml', 'text', 'table'])
@pytest.mark.parametrize('encoding', ['cp1252', 'cp437', 'latin-1'])
def test_output_survives_legacy_code_page(output, encoding):
    # A stream that cannot encode the response must not abort the command.
    # See https://github.com/aws/aws-cli/issues/10574
    assert _format(output, {'Value': NON_ENCODABLE}, encoding)


@pytest.mark.parametrize('encoding', ['cp1252', 'cp437', 'latin-1'])
def test_json_output_on_legacy_code_page_round_trips(encoding):
    formatted = _format('json', {'Value': NON_ENCODABLE}, encoding)
    assert json.loads(formatted)['Value'] == NON_ENCODABLE


@pytest.mark.parametrize('encoding', ['cp1252', 'cp437', 'latin-1'])
def test_yaml_output_on_legacy_code_page_round_trips(encoding):
    formatted = _format('yaml', {'Value': NON_ENCODABLE}, encoding)
    assert YAML(typ='safe').load(formatted)['Value'] == NON_ENCODABLE


@pytest.mark.parametrize('output', ['json', 'yaml'])
def test_utf8_output_is_not_escaped(output):
    # Escaping is only a fallback; UTF-8 streams keep the literal characters.
    # Restricted to the BMP because ruamel escapes astral characters even
    # when allow_unicode is on.
    value = 'arrow → accent é'
    assert value in _format(output, {'Value': value}, 'utf-8')


def test_utf8_json_output_keeps_astral_characters_literal():
    assert NON_ENCODABLE in _format('json', {'Value': NON_ENCODABLE}, 'utf-8')
