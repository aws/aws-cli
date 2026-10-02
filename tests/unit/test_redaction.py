# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

from awscli import redaction
from awscli.redaction import redact, register_redaction

REDACTED = '<redacted private key>'


@pytest.mark.parametrize(
    'value, expected',
    [
        (
            '-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n'
            '-----END RSA PRIVATE KEY-----\n',
            REDACTED + '\n',
        ),
        (
            '--private-key=-----BEGIN PRIVATE KEY-----\nMIGHAg\n'
            '-----END PRIVATE KEY-----',
            '--private-key=' + REDACTED,
        ),
        (
            '-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIF\n'
            '-----END ENCRYPTED PRIVATE KEY-----',
            REDACTED,
        ),
        # An unterminated key is redacted up to the end of the text.
        ('-----BEGIN EC PRIVATE KEY-----\nMHcCAQ', REDACTED),
        (
            '-----BEGIN PRIVATE KEY-----\nA\n-----END PRIVATE KEY-----'
            '-----BEGIN PRIVATE KEY-----\nB\n-----END PRIVATE KEY-----',
            REDACTED + REDACTED,
        ),
    ],
)
def test_redacts_private_keys(value, expected):
    assert redact(value) == expected


def test_redacts_nested_values():
    key = '-----BEGIN PRIVATE KEY-----\nA\n-----END PRIVATE KEY-----'
    value = {
        'args': ['--private-key', key],
        'pair': ('x', key),
        'body': key.encode('utf-8'),
        'rc': 0,
    }
    assert redact(value) == {
        'args': ['--private-key', REDACTED],
        'pair': ('x', REDACTED),
        'body': REDACTED.encode('utf-8'),
        'rc': 0,
    }


@pytest.mark.parametrize(
    'value',
    [
        ['cloudfront', 'sign', '--private-key', 'file://key.pem'],
        '{"a": "-----BEGIN PUBLIC KEY-----"}',
        {'headers': {'a': 'b'}, 'body': b'\xff\xfe'},
        None,
        object(),
    ],
)
def test_returns_values_without_matches_unchanged(value):
    assert redact(value) == value


def test_register_redaction(monkeypatch):
    monkeypatch.setattr(redaction, '_REDACTIONS', list(redaction._REDACTIONS))
    register_redaction(r'secret-\w+', '<redacted secret>')
    assert redact(['a secret-abc123']) == ['a <redacted secret>']
