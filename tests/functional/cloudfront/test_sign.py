# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import re

from awscrt.crypto import EC, RSA
from botocore.compat import parse_qs, urlparse
from botocore.history import HistoryRecorder

from awscli.customizations.history.db import (
    DatabaseHistoryHandler,
    DatabaseRecordWriter,
    RecordBuilder,
)
from awscli.testutils import (
    BaseAWSCommandParamsTest,
    FileCreator,
    mock,
    skip_if_windows,
)


def _pem_to_der(pem, label):
    # Decode the body of the PEM block with the given label.
    match = re.search(
        rf'-----BEGIN {label}-----(.*?)-----END {label}-----', pem, re.DOTALL
    )
    return base64.b64decode(''.join(match.group(1).split()))


def _url_b64decode(value):
    # Reverse the CloudFront-specific base64 substitutions applied by
    # CloudFrontSigner._url_b64encode.
    restored = value.replace('-', '+').replace('_', '=').replace('~', '/')
    return base64.b64decode(restored)


class TestSign(BaseAWSCommandParamsTest):
    # A private key only for testing purpose.
    private_key = (
        '-----BEGIN RSA PRIVATE KEY-----\n'
        'MIIEowIBAAKCAQEAu6o2+Jc8UINw2P/w2l7A1xXu3emQEZQ9diA3bmog8r9Dg+65\n'
        'fZgAqmuNWPqBivv7j3DGnLUdt8uCIr7PYUbK7wDa6n7U3ryOWtO2ZTc3StiJVcqT\n'
        'sokZ0qxGFtDRafjBuydXtcxh52vVTcHqH33nubyyZIzuhTwfmrIOnUXnLwbMrBBP\n'
        'bg/8mlgQooyo1XbrN1eO4XMs+UgQ9Mqc7KRJRinUJ+KYuCnM8f/nN4RjYdjTcghk\n'
        'xCPEHCeSt2luywWyYmfguWCBS2Mu1q0250wKyNazlgiiTJtAuuSeweb4NKPOJL9X\n'
        'hR6Ce6UuU4WYlli8gvQh3FAV3N3C1Rxo20k28QIDAQABAoIBAQCUEkP5dWrzpCJg\n'
        'NeHWizjg/L9SfT1dgXfVQqo6BqckoeElsjDNdifgT6hhcpbQEO52SWeMsiNWp85w\n'
        'l9mNSYxJdIVGzPgtHt27sJyT1DNebOg/tu0+y4qCfcd3rR/u24YQo4RDP5ZoQN82\n'
        '0TBn1LIIDWk8iS6SFdRh/OgnE8bLhNbK9IfZQFEEJrFkArrn/le/ro2mfJkC/imo\n'
        'QvqKmM0dGBXt5SCDSbUQAzKtEcR/4gf/qSjFe2YAwAvSA05WXMH6szdtx6/H/VbK\n'
        'Uck/WwTHvGObQDFEWmICxPK9AWT0qaFNjlUsi3bjQRdIlYYrXe+6nVMB/Jp1awq7\n'
        'tGBqIcWBAoGBAPtXCNuoQhKXqkjJgteQpB+wFav12XRZgpOciYdeviJrgWydpOOu\n'
        'O9wkiRUctUijRJbUuWCJF7SgYGoT2xTTp/COiOReqs7qXLMuuXCZcPKkMRJj5wmo\n'
        'Uc2AwUV/o3+PNz1NFK+2RgciXplac7qugIyuxIvBKuVFTBlCg0+if/0pAoGBAL8k\n'
        '845wKqOeiawwle/o9lKLGPy1T11GrE6l1A5jRuE1WTVM77jRrb0Hmo0mdfHaf5A0\n'
        'EjXGIX/fjcmQzBrEd78eCUsvI2Bgn6xXwhd4TTyWHGZfoQjFqAGkixuLN1oo2h1g\n'
        'bRreFKfAubFP8MC93z23vnH6tdY2VIA4h5ehUFyJAoGAJqxJrKLDJ+E2TmTTQR/8\n'
        'YPPTIdZ+UyzCrrvTXYTydJFeJLxM9suEYmcswJbePgMBNsQckgIGJ8DVlPzhJN88\n'
        'ZANKhPkcByKAiQGTfwPdITiqZE4C6rV/gMNi+bKeEa6TrVcC69Z8B/T94VLNo9fd\n'
        '58esbmSWmRiEkQ5u7f3u+6ECgYA8+6ANCLJB43nPCu07TpsP+LrvHTWF799XdEa0\n'
        'lG3vuiKNA8/TqmoAziU79VJZ6Dkcm9BXga/8aSmGboD/5UDDI+UZLJ/fxtQKmzEc\n'
        'ZdBWjRnge5AYCV+xrnqHPiJZzIDSMIp+sO3sG2vjKzsHc0x/F1lWagOLpWfORLrV\n'
        '4KyP6QKBgAafeSrfK3LM7idiCBuxckLCgFoHa7uXLUNJRS5iIU+bbZLPj2ozu/tk\n'
        'U0jp7sNk1CyMWI36lR3sujkSyH3lPIXVgrXMuGY3PJRGntN8WlWEsw4VUMGRj3h4\n'
        '5rB+y/UOS+nlEwQ6eOS09GByJDEXOXpcwjFcTr/f7V8mi0jH+gY/\n'
        '-----END RSA PRIVATE KEY-----\n'
    )
    prefix = 'cloudfront sign --key-pair-id my_id --url http://example.com/hi '

    def setUp(self):
        files = FileCreator()
        self.private_key_file = files.create_file('foo.pem', self.private_key)
        self.addCleanup(files.remove_all)
        super().setUp()

    def assertDesiredUrl(self, url, base, params):
        self.assertEqual(len(url.splitlines()), 1, "Expects only 1 line")
        self.assertTrue(url.startswith(base), "URL mismatch")
        url = url.strip()  # Otherwise the last param contains a trailing CRLF
        self.assertEqual(parse_qs(urlparse(url).query), params)

    def test_canned_policy(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1'
        )
        expected_signature = (
            "UiEmtMsInU-gXoa1O7-bTRJmZ~ocphB0ONMxyEHs2r8Y9dwzeB~DkbgzPMX3jbdb"
            "wIwVX3f4VcY4HBLdPSkbF~D6KbUlxPw1ju8mlXeu2C436XxZdrJrrJaiEDaTpKsl"
            "Xpn9ngaCzVfCVPfkC3a0NBWBySi5ezCG2yzb0c-djNgI1wkogwtmtZuOxAoKF1sR"
            "TyFX9ZitUiUIl~65nkJ94s~GGwxzTf1kMi7Wdm~9rFrJpx0O7nJEBy5O578s2UHr"
            "ejtwyedUR5BqXTkgu~A51NcjAN9LErATV7SVBYicoZ76AOfB-TKay7g6-MWCK6-T"
            "-4Q5x6XH4yzII3JpbCmVwA__"
        )
        expected_params = {
            'Key-Pair-Id': ['my_id'],
            'Expires': ['1451606400'],
            'Signature': [expected_signature],
        }
        self.assertDesiredUrl(
            self.run_cmd(cmdline)[0], 'http://example.com/hi', expected_params
        )

    def test_custom_policy(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1 --ip-address 12.34.56.78'
        )
        expected_signature = (
            "Vw-WG18WJJXim7YSGWS-zW~XmFB9MjCDOvgC~2Gz-1wiMQzCrXzYYbSE7-aF6JGO"
            "Ob5ewArpMqmu2g5mohnqgieZX1NY6IOteDoXYgqaNj1DafHWQD6UJ3IKVfkxISU9"
            "OmFPoG7H~VSPWEzOxdjOqdIPvAU2pW2mJ5oWu2aL62s0VVtLGCAm-DahiSQisl0J"
            "bzpPyG1pofvPbT75qc71r9uiqSAbPjUF5nmLCZazVnFjDkj3zIgMRYa5aV54VDa6"
            "-wEizzmjQ3-m6UMoYgcGHQXEjoFIWTfpZvbZBYkmK9lk3d16cgvaHafTJ-CPegn1"
            "bKxfgNEjSAoPWS0OvBkRmg__"
        )
        expected_params = {
            'Key-Pair-Id': ['my_id'],
            'Policy': [mock.ANY],
            'Signature': [expected_signature],
        }
        self.assertDesiredUrl(
            self.run_cmd(cmdline)[0], 'http://example.com/hi', expected_params
        )

    def test_raises_friendly_error_when_sha1_unavailable(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1'
        )
        
        crt_error = RuntimeError(
            '7174 (AWS_ERROR_CAL_UNSUPPORTED_ALGORITHM): The specified '
            'algorithm is unsupported on this platform.'
        )
        with mock.patch(
            'awscli.customizations.cloudfront.sign.RSA.sign',
            side_effect=crt_error,
        ):
            stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self.assertNotEqual(rc, 0)
        self.assertIn('SHA1', stderr)

    def test_unrelated_signing_error_is_not_reported_as_sha1(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1'
        )
        other_error = RuntimeError('some other signing failure')
        with mock.patch(
            'awscli.customizations.cloudfront.sign.RSA.sign',
            side_effect=other_error,
        ):
            stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self.assertNotEqual(rc, 0)
        self.assertNotIn('SHA1', stderr)
        self.assertIn('some other signing failure', stderr)


class TestSignECDSAWithECParameters(BaseAWSCommandParamsTest):
    # An EC (P-256) key as written by ``openssl ecparam -genkey``, which
    # prepends an EC PARAMETERS block. Only for testing purpose.
    private_key = (
        '-----BEGIN EC PARAMETERS-----\n'
        'BggqhkjOPQMBBw==\n'
        '-----END EC PARAMETERS-----\n'
        '-----BEGIN EC PRIVATE KEY-----\n'
        'MHcCAQEEIIn+jH+ABbyXBxAaGba29zfgklJlso8Uy/hTX87clMxYoAoGCCqGSM49\n'
        'AwEHoUQDQgAEcfEKhYahmRNFgp2LiNJf1Uy9TmWPgyuoAxKxXuS1Gtcxxs+39col\n'
        'Ty9YFvZvhsAcv6B3LwBJW/ah/AUD1BGTIg==\n'
        '-----END EC PRIVATE KEY-----\n'
    )
    pem_label = 'EC PRIVATE KEY'
    url = 'http://example.com/hi'
    prefix = 'cloudfront sign --key-pair-id MYID --url http://example.com/hi '

    def setUp(self):
        files = FileCreator()
        self.private_key_file = files.create_file('foo.pem', self.private_key)
        self.addCleanup(files.remove_all)
        super().setUp()

    def _run_and_parse(self, cmdline):
        url = self.run_cmd(cmdline)[0].strip()
        self.assertEqual(len(url.splitlines()), 1, "Expects only 1 line")
        self.assertTrue(url.startswith(self.url), "URL mismatch")
        return parse_qs(urlparse(url).query)

    def _assert_signature_verifies(self, params, policy):
        # ECDSA signatures are non-deterministic (a random nonce is used), so
        # rather than comparing against a fixed value we verify the signature
        # cryptographically against the policy that was signed.
        self.assertEqual(params['Key-Pair-Id'], ['MYID'])
        # ECDSA signatures are SHA-256; the URL must carry Hash-Algorithm=SHA256
        # so CloudFront's edge verifies with SHA-256 instead of its SHA-1
        # default (otherwise verification fails with AccessDenied).
        self.assertEqual(params['Hash-Algorithm'], ['SHA256'])
        key = EC.new_key_from_der_data(
            _pem_to_der(self.private_key, self.pem_label)
        )
        signature = _url_b64decode(params['Signature'][0])
        digest = hashlib.sha256(policy.encode('utf8')).digest()
        self.assertTrue(
            key.verify(digest, signature),
            "ECDSA signature failed to verify",
        )

    def test_custom_policy(self):
        cmdline = (
            self.prefix
            + '--private-key file://'
            + self.private_key_file
            + ' --date-less-than 2016-1-1 --ip-address 12.34.56.78'
        )
        params = self._run_and_parse(cmdline)
        self.assertNotIn('Expires', params)
        # The custom policy is emitted (base64url encoded) in the URL, so the
        # exact signed payload can be recovered and verified against.
        policy = _url_b64decode(params['Policy'][0]).decode('utf8')
        self._assert_signature_verifies(params, policy)


class BaseSigningCommandTest(BaseAWSCommandParamsTest):
    private_key = TestSign.private_key

    def setUp(self):
        self.files = FileCreator()
        self.private_key_file = self.files.create_file(
            'foo.pem', self.private_key
        )
        self.private_key_arg = 'file://' + self.private_key_file
        self.addCleanup(self.files.remove_all)
        super().setUp()

    def use_private_key(self, contents, scheme='file://'):
        mode = 'wb' if isinstance(contents, bytes) else 'w'
        path = self.files.create_file('key.pem', contents, mode=mode)
        self.private_key_arg = scheme + path

    def sign(self, *args, expected_rc=0):
        cmdline = [
            'cloudfront',
            'sign',
            '--key-pair-id',
            'myid',
            '--private-key',
            self.private_key_arg,
            '--date-less-than',
            '2016-1-1',
        ] + list(args)
        return self.run_cmd(cmdline, expected_rc=expected_rc)

    def sign_url(self, *args):
        url = self.sign(*args)[0].strip()
        return url, parse_qs(urlparse(url).query)

    def sign_cookies(self, *args, expected_rc=0):
        cmdline = [
            'cloudfront',
            'sign-cookies',
            '--key-pair-id',
            'myid',
            '--private-key',
            self.private_key_arg,
            '--date-less-than',
            '2016-1-1',
        ] + list(args)
        return self.run_cmd(cmdline, expected_rc=expected_rc)

    def assert_sign_error(self, message, *args, expected_rc=252):
        _, stderr, _ = self.sign(*args, expected_rc=expected_rc)
        self.assertIn(message, stderr)

    def assert_sign_cookies_error(self, message, *args):
        _, stderr, _ = self.sign_cookies(*args, expected_rc=252)
        self.assertIn(message, stderr)

    def assert_key_error(self, message):
        # Invalid keys have always been reported as an error with rc 255.
        self.assert_sign_error(
            message, '--url', 'http://example.com/hi', expected_rc=255
        )


class TestSignPolicySelection(BaseSigningCommandTest):
    def test_wildcard_url_uses_custom_policy(self):
        # CloudFront only matches wildcards in a custom policy.
        for url in ['http://example.com/*', 'http://example.com/a?x=*']:
            with self.subTest(url=url):
                _, params = self.sign_url('--url', url)
                self.assertNotIn('Expires', params)
                policy = json.loads(_url_b64decode(params['Policy'][0]))
                self.assertEqual(policy['Statement'][0]['Resource'], url)

    def test_wildcard_policy_resource_with_wildcard_url(self):
        _, params = self.sign_url(
            '--url',
            'http://example.com/videos/*',
            '--policy-resource',
            'http://example.com/*',
        )
        policy = json.loads(_url_b64decode(params['Policy'][0]))
        self.assertEqual(
            policy['Statement'][0]['Resource'], 'http://example.com/*'
        )

    def test_policy_resource_different_from_url_uses_custom_policy(self):
        # A canned policy is verified against the requested URL, so it can
        # not be used for a resource other than the URL.
        _, params = self.sign_url(
            '--url',
            'http://example.com/hi',
            '--policy-resource',
            'http://example.com/h?',
        )
        self.assertNotIn('Expires', params)
        policy = json.loads(_url_b64decode(params['Policy'][0]))
        self.assertEqual(
            policy['Statement'][0]['Resource'], 'http://example.com/h?'
        )

    def test_rejects_policy_resource_not_matching_url(self):
        for resource in [
            'http://example.com/other',
            'http://example.com/videos/*',
            'http://example.com/h??',
        ]:
            with self.subTest(resource=resource):
                self.assert_sign_error(
                    'does not match --policy-resource',
                    '--url',
                    'http://example.com/hi',
                    '--policy-resource',
                    resource,
                )

    def test_policy_resource_same_as_url_uses_canned_policy(self):
        _, params = self.sign_url(
            '--url',
            'http://example.com/hi',
            '--policy-resource',
            'http://example.com/hi',
        )
        self.assertEqual(params['Expires'], ['1451606400'])
        self.assertNotIn('Policy', params)


class TestSignQueryParameterOrder(BaseSigningCommandTest):
    def assert_query_parameter_order(self, url, expected_names, *args):
        signed_url = self.sign('--url', url, *args)[0].strip()
        base, _, query = signed_url.partition('?')
        self.assertEqual(
            [param.split('=', 1)[0] for param in query.split('&')],
            expected_names,
        )

    def test_canned_policy_sha256(self):
        self.assert_query_parameter_order(
            'http://example.com/hi',
            ['Expires', 'Signature', 'Key-Pair-Id', 'Hash-Algorithm'],
            '--hash-algorithm',
            'SHA256',
        )

    def test_custom_policy_sha256(self):
        self.assert_query_parameter_order(
            'http://example.com/hi',
            ['Policy', 'Signature', 'Key-Pair-Id', 'Hash-Algorithm'],
            '--ip-address',
            '12.34.56.78',
            '--hash-algorithm',
            'SHA256',
        )


class TestSignHashAlgorithm(BaseSigningCommandTest):
    def test_rsa_explicit_sha1_matches_default(self):
        default_url, _ = self.sign_url('--url', 'http://example.com/hi')
        sha1_url, _ = self.sign_url(
            '--url', 'http://example.com/hi', '--hash-algorithm', 'SHA1'
        )
        self.assertEqual(sha1_url, default_url)

    def test_unsupported_hash_algorithm(self):
        _, stderr, _ = self.sign(
            '--url',
            'http://example.com/hi',
            '--hash-algorithm',
            'MD5',
            expected_rc=252,
        )
        self.assertIn('--hash-algorithm', stderr)


class TestSignBackwardCompatibility(BaseSigningCommandTest):
    # Every URL that CloudFront could accept is still signed exactly as
    # before; only unusable input is rejected (see TestSignInputValidation).
    def test_signs_single_ip_address_as_before(self):
        _, params = self.sign_url(
            '--url', 'http://example.com/hi', '--ip-address', '12.34.56.78'
        )
        policy = json.loads(_url_b64decode(params['Policy'][0]))
        self.assertEqual(
            policy['Statement'][0]['Condition']['IpAddress'],
            {'AWS:SourceIp': '12.34.56.78/32'},
        )

    def test_invalid_date_error(self):
        for arg_name in ['--date-less-than', '--date-greater-than']:
            with self.subTest(arg_name=arg_name):
                _, stderr, _ = self.sign(
                    '--url',
                    'http://example.com/hi',
                    arg_name,
                    'not-a-date',
                    expected_rc=255,
                )
                self.assertIn('Invalid timestamp', stderr)
                self.assertIn(f'Invalid value for {arg_name}', stderr)
                self.assertIn('Supported formats include', stderr)


class TestSignPolicyResourceValidation(BaseSigningCommandTest):
    def sign_policy_resource(self, url, resource):
        return self.sign(
            '--url', url, '--policy-resource', resource, expected_rc=252
        )[1]

    def test_rejects_empty_policy_resource(self):
        self.assertIn(
            'must not be empty',
            self.sign_policy_resource('http://example.com/hi', ''),
        )

    def test_rejects_unsafe_policy_resource(self):
        for resource in ['http://example.com/\\*', 'http://example.com/"*']:
            with self.subTest(resource=resource):
                self.assertIn(
                    'Invalid value for --policy-resource',
                    self.sign_policy_resource(
                        'http://example.com/hi', resource
                    ),
                )

    def test_rejects_invalid_non_wildcard_policy_resource(self):
        self.assertIn(
            'Invalid value for --policy-resource',
            self.sign_policy_resource('http://example.com/hi', 'not-a-url'),
        )

    def test_rejects_policy_resource_fragment(self):
        self.assertIn(
            'URL fragment',
            self.sign_policy_resource(
                'http://example.com/hi', 'http://example.com/*#frag'
            ),
        )

    def test_validates_url_with_policy_resource(self):
        for url in ['example.com/hi', 'http://example.com/h#i']:
            with self.subTest(url=url):
                self.assertIn(
                    'Invalid value for --url',
                    self.sign_policy_resource(url, '*'),
                )

    def test_rejects_already_signed_url_with_policy_resource(self):
        self.assertIn(
            'already contains the CloudFront signing parameters',
            self.sign_policy_resource(
                'http://example.com/hi?Expires=1&Signature=a&Key-Pair-Id=K',
                'http://example.com/*',
            ),
        )

    def test_allows_wildcard_scheme_in_policy_resource(self):
        _, params = self.sign_url(
            '--url',
            'https://example.com/hi',
            '--policy-resource',
            'http*://example.com/*',
        )
        self.assertIn('Policy', params)


class BaseInputValidationTest(BaseSigningCommandTest):
    # Input that CloudFront can never accept is rejected by both commands
    # instead of producing a signed URL or cookies that cannot be used.
    # Concrete subclasses supply the command and its resource argument.
    __test__ = False
    resource_arg = None

    def assert_error(self, message, *args):
        raise NotImplementedError('assert_error')

    def test_rejects_unsafe_characters(self):
        for resource in [
            'http://example.com/hi"',
            'http://example.com/\\*',
            'http://example.com/h\ni',
        ]:
            with self.subTest(resource=resource):
                self.assert_error(
                    'must not contain double quotes',
                    self.resource_arg,
                    resource,
                )

    def test_rejects_url_fragment(self):
        for resource in [
            'http://example.com/hi#frag',
            'http://example.com/hi#',
            'http://example.com/*#frag',
        ]:
            with self.subTest(resource=resource):
                self.assert_error('URL fragment', self.resource_arg, resource)

    def test_rejects_malformed_urls(self):
        for resource in [
            '',
            'example.com/hi',
            'video.mp4',
            'ftp://example.com/hi',
            'rtmp://example.com/video.mp4',
            'https://[zz/a',
            'https://:80/a',
            'https://example.com:abc/a',
            'https://example.com:99999/a',
        ]:
            with self.subTest(resource=resource):
                self.assert_error(
                    f'Invalid value for {self.resource_arg}',
                    self.resource_arg,
                    resource,
                )

    def test_rejects_non_ascii_and_spaces(self):
        for resource in [
            'https://example.com/caf\u00e9.jpg',
            'https://b\u00fccher.example/a.jpg',
            'https://example.com/a b.jpg',
        ]:
            with self.subTest(resource=resource):
                self.assert_error(
                    'ASCII characters', self.resource_arg, resource
                )

    def test_rejects_active_date_not_before_expiration(self):
        # The result would never be valid, so it could never be used.
        for date_greater_than in ['2016-2-1', '2016-1-1']:
            with self.subTest(date_greater_than=date_greater_than):
                self.assert_error(
                    'must be before --date-less-than',
                    self.resource_arg,
                    'http://example.com/hi',
                    '--date-greater-than',
                    date_greater_than,
                )

    def test_rejects_ipv6_address(self):
        self.assert_error(
            'CloudFront only supports IPv4',
            self.resource_arg,
            'http://example.com/hi',
            '--ip-address',
            '2001:db8::/32',
        )

    def test_rejects_invalid_ip_address(self):
        for ip_address in [
            'foo',
            '1.2.3',
            '256.1.1.1',
            '300.1.2.3/40',
            '1.2.3.4/33',
            '1.2.3.4/a',
            '1.2.3.0/255.255.255.0',
            '01.2.3.4',
            '1.2.3.4","x":"y',
        ]:
            with self.subTest(ip_address=ip_address):
                self.assert_error(
                    'not a valid IPv4 address or CIDR range',
                    self.resource_arg,
                    'http://example.com/hi',
                    '--ip-address',
                    ip_address,
                )


class TestSignInputValidation(BaseInputValidationTest):
    __test__ = True
    resource_arg = '--url'

    def assert_error(self, message, *args):
        self.assert_sign_error(message, *args)

    def test_accepts_url_with_port_and_percent_encoding(self):
        url = 'https://example.com:8443/caf%C3%A9.jpg'
        signed_url, _ = self.sign_url('--url', url)
        self.assertTrue(signed_url.startswith(url + '?Expires=1451606400&'))

    def test_rejects_url_with_signing_params(self):
        # CloudFront denies URLs whose signing parameters appear twice.
        for url in [
            'http://example.com/hi?Expires=1',
            'http://example.com/hi?a=1&Signature=x',
            'http://example.com/hi?Key-Pair-Id=K1',
            'http://example.com/hi?Policy=x',
            'http://example.com/hi?Hash-Algorithm=SHA1',
        ]:
            with self.subTest(url=url):
                self.assert_sign_error(
                    'already contains the CloudFront signing parameters',
                    '--url',
                    url,
                )

    def test_accepts_query_params_that_are_not_signing_params(self):
        # Query parameter names are case-sensitive.
        url = 'http://example.com/hi?expires=1&size=large'
        signed_url, _ = self.sign_url('--url', url)
        self.assertTrue(signed_url.startswith(url + '&Expires=1451606400&'))


class TestSignCookiesInputValidation(BaseInputValidationTest):
    __test__ = True
    resource_arg = '--resource'

    def assert_error(self, message, *args):
        self.assert_sign_cookies_error(message, *args)

    def test_accepts_url_with_port_and_percent_encoding(self):
        stdout, _, _ = self.sign_cookies(
            '--resource',
            'https://example.com:8443/caf%C3%A9.jpg',
            '--output',
            'json',
        )
        self.assertEqual(
            json.loads(stdout)['CloudFront-Expires'], '1451606400'
        )

    def test_rejects_invalid_dates(self):
        for arg, value in [
            ('--date-less-than', 'not-a-date'),
            ('--date-greater-than', 'not-a-date'),
            # A millisecond epoch, e.g. from JavaScript's Date.now().
            ('--date-less-than', '1893456000000'),
        ]:
            with self.subTest(arg=arg, value=value):
                self.assert_error(
                    f'Invalid value for {arg}',
                    '--resource',
                    'http://example.com/hi',
                    arg,
                    value,
                )


class TestSignKeyErrors(BaseSigningCommandTest):
    def test_encrypted_pkcs8_private_key(self):
        self.use_private_key(
            '-----BEGIN ENCRYPTED PRIVATE KEY-----\n'
            'MIIC5TBfBgkqhkiG9w0BBQ0wUjAxBgkqhkiG9w0BBQwwJAQQ4VOg5sq9YVA9jnxg\n'
            '-----END ENCRYPTED PRIVATE KEY-----\n'
        )
        self.assert_key_error('Encrypted private keys are not supported')

    def test_encrypted_pkcs1_private_key(self):
        self.use_private_key(
            '-----BEGIN RSA PRIVATE KEY-----\n'
            'Proc-Type: 4,ENCRYPTED\n'
            'DEK-Info: AES-128-CBC,00000000000000000000000000000000\n'
            '\n'
            'AAAA\n'
            '-----END RSA PRIVATE KEY-----\n'
        )
        self.assert_key_error('Encrypted private keys are not supported')

    def test_malformed_key_bodies(self):
        for label in ['RSA PRIVATE KEY', 'EC PRIVATE KEY', 'PRIVATE KEY']:
            for body in ['MIIC5TBfBgkqhkiG9w0BBQ0w', 'not base64 !!']:
                with self.subTest(label=label, body=body):
                    self.use_private_key(
                        f'-----BEGIN {label}-----\n{body}\n'
                        f'-----END {label}-----\n'
                    )
                    self.assert_key_error(
                        'Unsupported key type or invalid private key'
                    )

    def test_error_does_not_expose_key_material(self):
        body = 'MIIC5TBfBgkqhkiG9w0BBQ0wUjAxBgkqhkiG9w0BBQwwJAQQ4VOg5sq9YVA9'
        for scheme in ['file://', 'fileb://']:
            with self.subTest(scheme=scheme):
                self.use_private_key(
                    f'-----BEGIN PRIVATE KEY-----\n{body}\n'
                    '-----END PRIVATE KEY-----\n',
                    scheme=scheme,
                )
                _, stderr, _ = self.sign(
                    '--url', 'http://example.com/hi', expected_rc=255
                )
                self.assertNotIn(body[:24], stderr)

    def test_non_utf8_private_key(self):
        self.use_private_key(b'\xff\xfe\x00', scheme='fileb://')
        self.assert_key_error('Unsupported private key')

    @skip_if_windows('The Windows CRT derives the missing EC public key.')
    def test_ec_private_key_without_public_key(self):
        # A P-256 key exported with ``openssl ec -no_public``.
        self.use_private_key(
            '-----BEGIN PRIVATE KEY-----\n'
            'MEECAQAwEwYHKoZIzj0CAQYIKoZIzj0DAQcEJzAlAgEBBCCtiWoCbDTjaVJiKBL+\n'
            'EfVrw1qbBKZkc6ch+SgM8yMdsg==\n'
            '-----END PRIVATE KEY-----\n'
        )
        self.assert_key_error('does not include its public key')

    def test_unsupported_pem_label(self):
        self.use_private_key(
            '-----BEGIN OPENSSH PRIVATE KEY-----\n'
            'b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtz\n'
            '-----END OPENSSH PRIVATE KEY-----\n'
        )
        self.assert_key_error('Unsupported key type')

    def test_non_p256_curve(self):
        # EC private keys on the P-384 curve, which CloudFront does not
        # support, in SEC1 and PKCS#8 format.
        for private_key in [
            '-----BEGIN EC PRIVATE KEY-----\n'
            'MIGkAgEBBDCIoGBIXHIpvlHWVTT+jka5Jpj1YR5rWIncoxf6VUxxhlHjEI7hqDto\n'
            'FajvDTKH5jSgBwYFK4EEACKhZANiAAT1i0QFJOMXeKxMx4VpZHw6OoKhEOB4nOXk\n'
            'h+Z9dhiQ4H6O2D84WS6ql+iyNIH2qux8jBUju3fc8NdbVwIqyfQZWRRo/Lg5ekDp\n'
            'M7re404ay7JYpiJXlCZP+RBCBn23NZU=\n'
            '-----END EC PRIVATE KEY-----\n',
            '-----BEGIN PRIVATE KEY-----\n'
            'MIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDBMuzkcdg39rdzENI+E\n'
            'T7PxexdQ6bSROnnxQAn+KTrCfDDfWjfhm/AxexdwTBnkffmhZANiAASbiECnsS42\n'
            'Bz5vDZrKGz5t6qtWa6KJdgSHyP75BEwY1Fq5mrrV/mzWRzisPvALUzx6OJyQ/inY\n'
            'mKeb0H9tA7BMjxTpT7GfYE9ySp1bsKqXwa725O6Kcl3pPz6JsiXNVs8=\n'
            '-----END PRIVATE KEY-----\n',
        ]:
            with self.subTest(private_key=private_key.splitlines()[0]):
                self.use_private_key(private_key)
                self.assert_key_error('Only P-256 EC keys are supported')

    def test_debug_output_does_not_expose_inline_key_material(self):
        # The key body must not be logged even when it is passed inline
        # instead of with file:// or fileb://.
        key_line = self.private_key.splitlines()[1]
        for command, resource_arg in [
            ('sign', '--url'),
            ('sign-cookies', '--resource'),
        ]:
            with self.subTest(command=command):
                cmdline = [
                    'cloudfront',
                    command,
                    resource_arg,
                    'http://example.com/hi',
                    '--key-pair-id',
                    'myid',
                    '--private-key',
                    self.private_key,
                    '--date-less-than',
                    '2016-1-1',
                    '--debug',
                ]
                # The debug log records the arguments from sys.argv.
                with mock.patch('sys.argv', ['aws'] + cmdline):
                    _, stderr, _ = self.run_cmd(cmdline)
                self.assertIn('<redacted private key>', stderr)
                self.assertNotIn(key_line, stderr)

    def test_history_does_not_record_inline_key_material(self):
        cmdline = [
            'cloudfront',
            'sign',
            '--url',
            'http://example.com/hi',
            '--key-pair-id',
            'myid',
            '--private-key',
            self.private_key,
            '--date-less-than',
            '2016-1-1',
        ]
        writer = mock.Mock(DatabaseRecordWriter)
        recorder = HistoryRecorder()
        recorder.add_handler(DatabaseHistoryHandler(writer, RecordBuilder()))
        recorder.enable()
        with mock.patch('awscli.clidriver.HISTORY_RECORDER', recorder):
            self.run_cmd(cmdline)
        payloads = {
            call.args[0]['event_type']: call.args[0]['payload']
            for call in writer.write_record.call_args_list
        }
        self.assertEqual(
            payloads['CLI_ARGUMENTS'],
            # Only the key is redacted, so its trailing newline is kept.
            cmdline[:7] + ['<redacted private key>\n'] + cmdline[8:],
        )


class TestSignPrivateKeyInputs(BaseSigningCommandTest):
    def assert_signs_like_file_key(self):
        expected_url = self.sign_url_with('file://' + self.private_key_file)
        self.assertEqual(
            self.sign_url_with(self.private_key_arg), expected_url
        )

    def sign_url_with(self, private_key_arg):
        self.private_key_arg, previous = private_key_arg, self.private_key_arg
        try:
            return self.sign('--url', 'http://example.com/hi')[0]
        finally:
            self.private_key_arg = previous

    def test_fileb_private_key(self):
        self.use_private_key(self.private_key.encode('ascii'), 'fileb://')
        self.assert_signs_like_file_key()

    def test_private_key_with_byte_order_mark(self):
        self.use_private_key(
            b'\xef\xbb\xbf' + self.private_key.encode('ascii'), 'fileb://'
        )
        self.assert_signs_like_file_key()

    def test_private_key_with_crlf_line_endings(self):
        self.use_private_key(self.private_key.replace('\n', '\r\n'))
        self.assert_signs_like_file_key()

    def test_private_key_after_certificate(self):
        self.use_private_key(
            '-----BEGIN CERTIFICATE-----\n'
            'MIIB9DCCAV2gAwIBAgIUVURURxQltJ3nilDhiDP37i2FhcAwDQYJKoZIhvcNAQEL\n'
            '-----END CERTIFICATE-----\n' + self.private_key
        )
        self.assert_signs_like_file_key()


class TestSignSigningFailures(BaseSigningCommandTest):
    signing_error = RuntimeError(
        '7179 (AWS_ERROR_CAL_CRYPTO_OPERATION_FAILED): Unknown error when '
        'calling underlying Crypto library.'
    )

    def assert_signing_failure(self, key_class):
        with mock.patch.object(
            key_class, 'sign', side_effect=self.signing_error
        ):
            self.assert_key_error('Failed to sign the CloudFront policy')

    def test_rsa_signing_failure(self):
        self.assert_signing_failure(RSA)

    def test_ecdsa_signing_failure(self):
        self.use_private_key(TestSignECDSAWithECParameters.private_key)
        self.assert_signing_failure(EC)

    def test_sign_cookies_signing_failure(self):
        with mock.patch.object(RSA, 'sign', side_effect=self.signing_error):
            _, stderr, _ = self.sign_cookies(
                '--resource', 'http://example.com/hi', expected_rc=255
            )
        self.assertIn('Failed to sign the CloudFront policy', stderr)


class TestSignCookies(BaseSigningCommandTest):
    def test_wildcard_resource_uses_custom_policy(self):
        stdout, _, _ = self.sign_cookies(
            '--resource', 'http://example.com/*', '--output', 'json'
        )
        cookies = json.loads(stdout)
        self.assertNotIn('CloudFront-Expires', cookies)
        policy = json.loads(_url_b64decode(cookies['CloudFront-Policy']))
        self.assertEqual(
            policy['Statement'][0]['Resource'], 'http://example.com/*'
        )

    def test_custom_policy_with_active_date_and_ip_address(self):
        stdout, _, _ = self.sign_cookies(
            '--resource',
            'http://example.com/hi',
            '--date-greater-than',
            '2015-12-1',
            '--ip-address',
            '10.0.0.0/8',
            '--output',
            'json',
        )
        cookies = json.loads(stdout)
        self.assertEqual(
            set(cookies),
            {
                'CloudFront-Policy',
                'CloudFront-Signature',
                'CloudFront-Key-Pair-Id',
            },
        )

        self.assertEqual(
            _url_b64decode(cookies['CloudFront-Policy']).decode('utf-8'),
            '{"Statement":[{"Resource":"http://example.com/hi","Condition":'
            '{"DateLessThan":{"AWS:EpochTime":1451606400},"IpAddress":'
            '{"AWS:SourceIp":"10.0.0.0/8"},"DateGreaterThan":'
            '{"AWS:EpochTime":1448928000}}}]}',
        )
        _, params = self.sign_url(
            '--url',
            'http://example.com/hi',
            '--date-greater-than',
            '2015-12-1',
            '--ip-address',
            '10.0.0.0/8',
        )
        self.assertEqual(
            cookies['CloudFront-Signature'], params['Signature'][0]
        )

    def test_default_output_from_config(self):
        self.environ['AWS_DEFAULT_OUTPUT'] = 'json'
        stdout, _, _ = self.sign_cookies('--resource', 'http://example.com/hi')
        self.assertEqual(
            json.loads(stdout)['CloudFront-Expires'], '1451606400'
        )

    def test_query(self):
        stdout, _, _ = self.sign_cookies(
            '--resource',
            'http://example.com/hi',
            '--query',
            '"CloudFront-Expires"',
            '--output',
            'text',
        )
        self.assertEqual(stdout.strip(), '1451606400')

    def test_question_mark_does_not_select_custom_policy(self):
        # ``?`` is ambiguous with the query string delimiter, so it is never
        # treated as a wildcard when choosing the policy type.
        for resource in [
            'http://example.com/image.jpg?size=large',
            'http://example.com/image?.jpg',
        ]:
            with self.subTest(resource=resource):
                stdout, _, _ = self.sign_cookies(
                    '--resource', resource, '--output', 'json'
                )
                cookies = json.loads(stdout)
                self.assertEqual(cookies['CloudFront-Expires'], '1451606400')
                self.assertNotIn('CloudFront-Policy', cookies)
