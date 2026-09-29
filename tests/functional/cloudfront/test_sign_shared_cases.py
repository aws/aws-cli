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
import hashlib
import json
import os

import pytest
from awscrt.crypto import EC, RSA, RSASignatureAlgorithm
from botocore.compat import urlsplit

from tests import CLIRunner

TEST_DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'testdata'
)

CLI_OPTIONAL_ARGS = {
    'expirationDate': '--date-less-than',
    'activeDate': '--date-greater-than',
    'ipRange': '--ip-address',
    'hashAlgorithm': '--hash-algorithm',
}

SIGNATURE_ALGORITHMS = {
    'RSA-SHA1': (RSASignatureAlgorithm.PKCS1_5_SHA1, hashlib.sha1),
    'RSA-SHA256': (RSASignatureAlgorithm.PKCS1_5_SHA256, hashlib.sha256),
    'ECDSA-SHA1': (None, hashlib.sha1),
    'ECDSA-SHA256': (None, hashlib.sha256),
}

PUBLIC_KEY_FILES = {
    'K1TESTKEY': 'test-rsa-key-public.pem',
    'K2ECDSATEST': 'test-ecdsa-key-public.pem',
}


def _load_test_cases(filename):
    with open(os.path.join(TEST_DATA_DIR, filename)) as f:
        return json.load(f)


def _is_error_case(case):
    return case['expected'].get('error', False)


SIGN_CASES = _load_test_cases('sign-test-cases.json')
SIGN_COOKIES_CASES = _load_test_cases('sign-cookies-test-cases.json')
URL_CASES = [c for c in SIGN_CASES if not _is_error_case(c)]
COOKIE_CASES = [c for c in SIGN_COOKIES_CASES if not _is_error_case(c)]
SIGN_ERROR_CASES = [c for c in SIGN_CASES if _is_error_case(c)]
SIGN_COOKIES_ERROR_CASES = [c for c in SIGN_COOKIES_CASES if _is_error_case(c)]


def _case_id(case):
    return case['id']


def _url_b64decode(value):
    # Reverse the CloudFront-specific base64 substitutions.
    restored = value.replace('-', '+').replace('_', '=').replace('~', '/')
    return base64.b64decode(restored)


def _pem_body_to_der(filename):
    with open(os.path.join(TEST_DATA_DIR, filename)) as f:
        lines = f.read().splitlines()
    return base64.b64decode(
        ''.join(line for line in lines if '-----' not in line)
    )


def _assert_signature_verifies(case, signature):
    # Verify the signature of the expected policy with the test key's public
    # key, using the hash of the case's signature algorithm.
    expected = case['expected']
    public_key_der = _pem_body_to_der(
        PUBLIC_KEY_FILES[case['input']['keyPairId']]
    )
    rsa_algorithm, hash_function = SIGNATURE_ALGORITHMS[
        expected['signatureAlgorithm']
    ]
    digest = hash_function(expected['policyJson'].encode('utf8')).digest()
    signature = _url_b64decode(signature)
    if rsa_algorithm is None:
        public_key = EC.new_key_from_der_data(public_key_der)
        is_valid = public_key.verify(digest, signature)
    else:
        public_key = RSA.new_public_key_from_der_data(public_key_der)
        is_valid = public_key.verify(rsa_algorithm, digest, signature)
    assert is_valid, 'Signature failed to verify against the public key'


def _assert_signature(case, signature, expected_signature):
    _assert_signature_verifies(case, signature)
    if not case['expected'].get('verifyCryptographically'):
        # RSA signatures are deterministic and also compared exactly, which
        # also validates the policy field order and formatting.
        assert expected_signature is not None
        assert signature == expected_signature


def _signing_args(case):
    case_input = case['input']
    args = [
        '--key-pair-id',
        case_input['keyPairId'],
        '--private-key',
        'file://' + os.path.join(TEST_DATA_DIR, case_input['privateKeyFile']),
    ]
    for name, cli_arg in CLI_OPTIONAL_ARGS.items():
        if name in case_input:
            args.extend([cli_arg, str(case_input[name])])
    return args


def _sign_url_command(case):
    resource = case['input']['resource']
    apply_to = case['expected'].get('applyTo')
    if apply_to is None:
        cmd = ['cloudfront', 'sign', '--url', resource]
    else:
        # Sign the wildcard resource and apply the signature to the URL.
        cmd = [
            'cloudfront',
            'sign',
            '--url',
            apply_to,
            '--policy-resource',
            resource,
        ]
    return cmd + _signing_args(case)


def _sign_cookies_command(case):
    return [
        'cloudfront',
        'sign-cookies',
        '--resource',
        case['input']['resource'],
        '--output',
        'json',
    ] + _signing_args(case)


def _parse_query(url):
    # The values are left undecoded because they are compared to the raw
    # values that CloudFront receives.
    params = [p.split('=', 1) for p in urlsplit(url).query.split('&')]
    names = [name for name, _ in params]
    assert len(names) == len(set(names)), f'Duplicate query params: {names}'
    return dict(params)


@pytest.fixture
def cli():
    return CLIRunner()


def _run(cli, cmdline):
    result = cli.run(cmdline)
    # Signing is done locally and never calls CloudFront.
    assert result.aws_requests == []
    return result


@pytest.mark.parametrize('case', URL_CASES, ids=_case_id)
def test_signed_url(cli, case):
    expected = case['expected']
    result = _run(cli, _sign_url_command(case))
    assert result.rc == 0, result.stderr
    stdout = result.stdout
    base_url = expected.get('applyTo', case['input']['resource'])
    separator = '&' if '?' in base_url else '?'
    assert stdout.startswith(base_url + separator)

    params = _parse_query(stdout)
    for name, value in expected['queryParams'].items():
        assert params[name] == value
    expected_names = set(expected['queryParams']) | {'Signature'}
    if 'Expires' in expected_names:
        # Canned policy: CloudFront rebuilds the policy from the URL.
        assert 'Policy' not in params
    else:
        # Custom policy: the signed policy is part of the URL.
        expected_names.add('Policy')
        policy = _url_b64decode(params['Policy']).decode('utf8')
        assert policy == expected['policyJson']
    assert set(params) == expected_names
    _assert_signature(case, params['Signature'], expected.get('signature'))


@pytest.mark.parametrize('case', COOKIE_CASES, ids=_case_id)
def test_signed_cookies(cli, case):
    expected = case['expected']
    result = _run(cli, _sign_cookies_command(case))
    assert result.rc == 0, result.stderr

    cookies = json.loads(result.stdout)
    for name, value in expected['cookies'].items():
        assert cookies[name] == value
    assert set(cookies) == set(expected['cookies']) | {'CloudFront-Signature'}
    if 'CloudFront-Expires' not in expected['cookies']:
        # Custom policy cookies never include CloudFront-Expires.
        assert 'CloudFront-Expires' not in cookies
        policy = _url_b64decode(cookies['CloudFront-Policy']).decode('utf8')
        assert policy == expected['policyJson']
    _assert_signature(
        case,
        cookies['CloudFront-Signature'],
        expected['cookies'].get('CloudFront-Signature'),
    )


@pytest.mark.parametrize(
    'build_command, case',
    [(_sign_url_command, c) for c in SIGN_ERROR_CASES]
    + [(_sign_cookies_command, c) for c in SIGN_COOKIES_ERROR_CASES],
    ids=[f'sign-{c["id"]}' for c in SIGN_ERROR_CASES]
    + [f'sign-cookies-{c["id"]}' for c in SIGN_COOKIES_ERROR_CASES],
)
def test_error(cli, case, build_command):
    result = _run(cli, build_command(case))
    assert result.rc == case['expected']['returnCode'], result.stderr
    assert 'Traceback' not in result.stderr
    assert result.stdout == ''
    for term in case['expected']['errorContains']:
        assert term.lower() in result.stderr.lower()
