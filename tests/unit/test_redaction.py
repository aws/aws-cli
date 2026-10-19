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
import base64

import pytest

from awscli import redaction
from awscli.redaction import redact, register_redaction

REDACTED = '<redacted private key>'
KEY_PEM = (
    '-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----\n'
)
CERT_PEM = '-----BEGIN CERTIFICATE-----\nMIIC\n-----END CERTIFICATE-----\n'


def _b64(text):
    return base64.b64encode(text.encode('utf-8')).decode('ascii')


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
        f'{{"Certificate": "{_b64(CERT_PEM)}"}}',
        {'headers': {'a': 'b'}, 'body': b'\xff\xfe'},
        None,
        object(),
    ],
)
def test_returns_values_without_matches_unchanged(value):
    assert redact(value) == value


@pytest.mark.parametrize('pem', [KEY_PEM, CERT_PEM + KEY_PEM])
def test_redacts_base64_private_keys(pem):
    cert = _b64(CERT_PEM)
    value = f'{{"Certificate": "{cert}", "PrivateKey": "{_b64(pem)}"}}'
    assert redact(value) == (
        f'{{"Certificate": "{cert}", "PrivateKey": "{REDACTED}"}}'
    )


def test_redacts_truncated_base64_private_key():
    assert redact('body: ' + _b64(KEY_PEM)[:45] + '...') == (
        'body: ' + REDACTED + '...'
    )


@pytest.mark.parametrize('cls', [bytes, bytearray])
def test_redacts_non_utf8_bytes(cls):
    value = cls(b'\xff\xfe' + KEY_PEM.encode('ascii') + b'\x80')
    assert redact(value) == cls(b'\xff\xfe' + REDACTED.encode() + b'\n\x80')


def test_redacts_base64_private_key_bytes():
    value = b'{"PrivateKey": "' + _b64(KEY_PEM).encode('ascii') + b'"}'
    assert redact(value) == b'{"PrivateKey": "' + REDACTED.encode() + b'"}'


@pytest.mark.xfail(
    strict=True,
    reason='A key split across argv items, such as an unquoted $KEY, is '
    'not redacted',
)
def test_redacts_word_split_private_key():
    argv = ['--private-key'] + KEY_PEM.split()
    assert 'MIIEow' not in redact(argv)


@pytest.mark.xfail(
    strict=True,
    reason='Base64 PEM data that does not start with -----BEGIN is not '
    'redacted',
)
def test_redacts_base64_private_key_with_leading_text():
    encoded = _b64('Bag Attributes\n    localKeyID: 01\n' + KEY_PEM)
    assert encoded not in redact(f'{{"PrivateKey": "{encoded}"}}')


def test_register_redaction(monkeypatch):
    monkeypatch.setattr(redaction, '_REDACTIONS', list(redaction._REDACTIONS))
    register_redaction(r'secret-\w+', '<redacted secret>')
    assert redact(['a secret-abc123']) == ['a <redacted secret>']


@pytest.mark.parametrize('replacement', [r'\1', r'C:\x', r'C:\new'])
def test_register_redaction_uses_replacement_literally(
    monkeypatch, replacement
):
    monkeypatch.setattr(redaction, '_REDACTIONS', list(redaction._REDACTIONS))
    register_redaction(r'secret-\w+', replacement)
    assert redact('a secret-abc123') == 'a ' + replacement
