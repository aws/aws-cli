# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import sys
from unittest import mock

from awscli.autocomplete import completer, main


def test_can_create_completer():
    cli_completer = main.create_autocompleter()
    assert isinstance(cli_completer, completer.AutoCompleter)


def test_autocomplete_does_not_write_carriage_returns():
    raw = io.BytesIO()
    # Simulate Windows stdout, which writes "\r\n" for each "\n".
    stdout = io.TextIOWrapper(raw, encoding='utf-8', newline='\r\n')
    fake_completer = mock.Mock()
    fake_completer.autocomplete.return_value = [
        completer.CompletionResult('ec2'),
        completer.CompletionResult('ecs'),
    ]
    with mock.patch.object(sys, 'stdout', stdout):
        with mock.patch.object(
            main, 'create_autocompleter', return_value=fake_completer
        ):
            main.autocomplete('aws e')
    stdout.flush()
    assert raw.getvalue() == b'ec2\necs\n'
