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
from awscli.redaction import (
    redact,
    register_redacted_key,
    register_redaction,
)

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


CREDENTIAL = '<redacted credential>'


@pytest.mark.parametrize(
    'value, expected',
    [
        # STS XML responses.
        (
            '<Credentials><AccessKeyId>ASIAX</AccessKeyId>'
            '<SecretAccessKey>s/e+c</SecretAccessKey>'
            '<SessionToken>t/o+k==</SessionToken>'
            '<Expiration>2026-11-16T12:00:00Z</Expiration></Credentials>',
            '<Credentials><AccessKeyId>ASIAX</AccessKeyId>'
            f'<SecretAccessKey>{CREDENTIAL}</SecretAccessKey>'
            f'<SessionToken>{CREDENTIAL}</SessionToken>'
            '<Expiration>2026-11-16T12:00:00Z</Expiration></Credentials>',
        ),
        # IAM Identity Center JSON, camel case.
        (
            '{"accessKeyId":"ASIAX","secretAccessKey":"s/e+c",'
            '"sessionToken":"t/o+k==","expiration":1}',
            f'{{"accessKeyId":"ASIAX","secretAccessKey":"{CREDENTIAL}",'
            f'"sessionToken":"{CREDENTIAL}","expiration":1}}',
        ),
        # A Python dict's repr, as in a debug log.
        (
            "{'AccessKeyId': 'ASIAX', 'SessionToken': 't/o+k=='}",
            f"{{'AccessKeyId': 'ASIAX', 'SessionToken': '{CREDENTIAL}'}}",
        ),
        # JSON inside a JSON string, with escaped quotes and slashes.
        (
            '"{\\"SessionToken\\": \\"t\\/o+k==\\"}"',
            f'"{{\\"SessionToken\\": \\"{CREDENTIAL}\\"}}"',
        ),
        # Request headers, as logged before a request is sent.
        (
            "headers={'X-Amz-Date': b'20261116T000000Z', "
            "'X-Amz-Security-Token': b't/o+k==', 'Authorization': b'AWS4'}",
            "headers={'X-Amz-Date': b'20261116T000000Z', "
            f"'X-Amz-Security-Token': b'{CREDENTIAL}', 'Authorization': b'AWS4'}}",
        ),
        # The signature's canonical request.
        (
            'x-amz-date:20261116T000000Z\nx-amz-security-token:t/o+k==\n\n'
            'host;x-amz-date;x-amz-security-token',
            f'x-amz-date:20261116T000000Z\nx-amz-security-token:{CREDENTIAL}'
            '\n\nhost;x-amz-date;x-amz-security-token',
        ),
        # A namespace prefix or attributes on the XML element.
        (
            '<sts:SessionToken>t</sts:SessionToken>'
            '<SecretAccessKey xmlns="x">s</SecretAccessKey>',
            f'<sts:SessionToken>{CREDENTIAL}</sts:SessionToken>'
            f'<SecretAccessKey xmlns="x">{CREDENTIAL}</SecretAccessKey>',
        ),
        # Amazon Cognito GetCredentialsForIdentity.
        (
            '{"AccessKeyId": "ASIAX", "SecretKey": "s/e+c"}',
            f'{{"AccessKeyId": "ASIAX", "SecretKey": "{CREDENTIAL}"}}',
        ),
        # The SigV2 session token parameter.
        (
            'Action=ListDomains&SecurityToken=t%2Fo&Version=2009-04-15',
            f'Action=ListDomains&SecurityToken={CREDENTIAL}&Version=2009-04-15',
        ),
        # A presigned URL.
        (
            'https://b.s3.amazonaws.com/k?X-Amz-Security-Token=t%2Fo%2Bk'
            '&X-Amz-Signature=abc',
            f'https://b.s3.amazonaws.com/k?X-Amz-Security-Token={CREDENTIAL}'
            '&X-Amz-Signature=abc',
        ),
    ],
)
def test_redacts_temporary_credentials(value, expected):
    assert redact(value) == expected
    # The logger redacts its arguments and then the formatted message.
    assert redact(redact(value)) == expected


def test_redacts_temporary_credentials_in_bytes():
    value = b"b'<SessionToken>t/o+k==</SessionToken>'"
    assert redact(value) == (
        b"b'<SessionToken>" + CREDENTIAL.encode() + b"</SessionToken>'"
    )


def test_redacts_values_of_credential_keys():
    value = {
        'Credentials': {
            'AccessKeyId': 'ASIAX',
            'SecretAccessKey': 's/e+c',
            'SessionToken': 't/o+k==',
            'Expiration': 1,
        },
        'roleCredentials': {'secretAccessKey': 's', 'sessionToken': 't'},
        'headers': {'x-amz-security-token': b't', 'X-Amz-Date': b'2026'},
    }
    assert redact(value) == {
        'Credentials': {
            'AccessKeyId': 'ASIAX',
            'SecretAccessKey': CREDENTIAL,
            'SessionToken': CREDENTIAL,
            'Expiration': 1,
        },
        'roleCredentials': {
            'secretAccessKey': CREDENTIAL,
            'sessionToken': CREDENTIAL,
        },
        'headers': {
            'x-amz-security-token': CREDENTIAL.encode(),
            'X-Amz-Date': b'2026',
        },
    }


@pytest.mark.parametrize(
    'value',
    [
        '<AccessKeyId>ASIAX</AccessKeyId><Expiration>2026</Expiration>',
        '<SecretKeyId>abc</SecretKeyId>',
        '{"GameSessionToken": "abc"}',
        'SignedHeaders=host;x-amz-date;x-amz-security-token',
        {'SessionTokenCount': 'abc', 'Name': 'SessionToken'},
    ],
)
def test_leaves_other_credential_text_unchanged(value):
    assert redact(value) == value


def test_register_redacted_key(monkeypatch):
    monkeypatch.setattr(
        redaction, '_REDACTED_KEYS', dict(redaction._REDACTED_KEYS)
    )
    register_redacted_key('ApiKey', '<redacted key>')
    assert redact({'apikey': 'abc', 'other': 'abc'}) == {
        'apikey': '<redacted key>',
        'other': 'abc',
    }
