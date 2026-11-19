# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Text chosen by an identity provider is made safe before it is printed."""

import urllib.error
from unittest.mock import patch

import pytest

from awscli.customizations.agentregistry import utils
from awscli.customizations.agentregistry.constants import MAX_PRINTED_TEXT
from awscli.customizations.agentregistry.providers import identify_provider
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    printable,
)


@pytest.mark.parametrize(
    'text,expected',
    [
        ('invalid_grant', 'invalid_grant'),
        # Colour, clear screen, and an OSC sequence that sets the title.
        ('\x1b[31mred\x1b[0m', '[31mred [0m'),
        ('\x1b[2J\x1b[Hcleared', '[2J [Hcleared'),
        ('\x1b]0;pwned\x07title', ']0;pwned title'),
        # A C1 control sequence introducer, DEL and NUL.
        ('\x9b31mx\x7fy\x00z', '31mx y z'),
        # Line breaks cannot forge extra lines of output.
        ('line one\r\nline two', 'line one line two'),
        ('\tindented', 'indented'),
        # Bidirectional overrides cannot reorder what is shown.
        ('abc\u202edcba', 'abc dcba'),
        # Ordinary non-ASCII text is kept.
        ('caf\u00e9 \u2713 \u65e5\u672c', 'caf\u00e9 \u2713 \u65e5\u672c'),
        (None, ''),
        ('', ''),
    ],
)
def test_control_characters_are_replaced(text, expected):
    assert printable(text) == expected


def test_long_text_is_capped():
    text = printable('x' * 10_000)
    assert text == 'x' * MAX_PRINTED_TEXT + '...'
    assert printable('abcdef', limit=3) == 'abc...'
    assert printable('abc', limit=3) == 'abc'


def test_non_strings_are_converted():
    assert printable(ValueError('bad\x1b[2J')) == 'bad [2J'


def test_unsupported_issuer_is_not_echoed_raw():
    with pytest.raises(AgentRegistryJWTError) as e:
        identify_provider('http://idp.example\x1b[2J/')
    assert '\x1b' not in str(e.value)


def test_metadata_fetch_error_is_not_echoed_raw():
    error = urllib.error.URLError('refused\x1b]0;pwned\x07')
    with patch.object(utils, 'http_get_json', side_effect=error):
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.discover_registry('https://registry.example', 'reg1')
    assert 'refused' in str(e.value)
    assert '\x1b' not in str(e.value) and '\x07' not in str(e.value)


def test_issuer_with_control_characters_is_refused():
    document = {'authorization_servers': ['https://idp.example/\x1b[2J']}
    with patch.object(utils, 'http_get_json', return_value=document):
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.discover_registry('https://registry.example', 'reg1')
    assert '\x1b' not in str(e.value)
