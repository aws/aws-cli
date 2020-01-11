# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import datetime

from botocore.compat import urlsplit
from awscli.testutils import BaseAWSCommandParamsTest, mock, temporary_file
from awscli.testutils import create_clidriver


# Values used to fix time.time() and datetime.datetime.utcnow()
# so we know the exact values of the signatures generated.
FROZEN_TIMESTAMP = 1471305652
DEFAULT_EXPIRES = 3600
FROZEN_TIME = mock.Mock(return_value=FROZEN_TIMESTAMP)
FROZEN_DATETIME = mock.Mock(
    return_value=datetime.datetime(2016, 8, 18, 14, 33, 3, 0))


class TestPresignCommand(BaseAWSCommandParamsTest):

    prefix = 's3 presign '

    def enable_addressing_mode_in_config(self, fileobj, mode):
        fileobj.write(
            "[default]\n"
            "s3 =\n"
            "    addressing_style = %s\n" % mode
        )
        fileobj.flush()
        self.environ['AWS_CONFIG_FILE'] = fileobj.name
        self.driver = create_clidriver()

    def enable_sigv4_from_config_file(self, fileobj):
        fileobj.write(
            "[default]\n"
            "s3 =\n"
            "    signature_version = s3v4\n"
        )
        fileobj.flush()
        self.environ['AWS_CONFIG_FILE'] = fileobj.name
        self.driver = create_clidriver()

    def assert_presigned_url_matches(self, actual_url, expected_match):
        """Verify generated presigned URL matches expected dict.

        This method compares an actual URL against a dict of expected
        values.  The reason that the "expected_match" is a dict instead
        of the expected presigned URL is because the query params
        are unordered so we can't guarantee an expected query param
        ordering.

        """
        parts = urlsplit(actual_url)
        self.assertEqual(parts.netloc, expected_match['hostname'])
        self.assertEqual(parts.path, expected_match['path'])
        query_params = self.parse_query_string(parts.query)
        self.assertEqual(query_params, expected_match['query_params'])

    def parse_query_string(self, query_string):
        pairs = []
        for part in query_string.split('&'):
            pairs.append(part.split('=', 1))
        return dict(pairs)

    def get_presigned_url_for_cmd(self, cmdline):
        with mock.patch('time.time', FROZEN_TIME):
            with mock.patch('datetime.datetime') as d:
                d.utcnow = FROZEN_DATETIME
                stdout = self.assert_params_for_cmd(cmdline, None)[0].strip()
                return stdout

    def test_generates_a_url(self):
        stdout = self.get_presigned_url_for_cmd(
            self.prefix + 's3://bucket/key')

        self.assert_presigned_url_matches(
            stdout, {
                'hostname': 'bucket.s3.us-east-1.amazonaws.com',
                'path': '/key',
                'query_params': {
                    'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
                    'X-Amz-Credential': (
                        'access_key%2F20160818%2Fus-east-1'
                        '%2Fs3%2Faws4_request'),
                    'X-Amz-Date': '20160818T143303Z',
                    'X-Amz-Expires': '3600',
                    'X-Amz-Signature': (
                        '1297528058f2c8b89cfa52c6a47d6c54890700a1da2470'
                        '2b06d53e774c0acc95'),
                    'X-Amz-SignedHeaders': 'host',
                }
            }
        )

    def test_handles_non_dns_compatible_buckets(self):
        stdout = self.get_presigned_url_for_cmd(
            self.prefix + 's3://bucket.dots/key')

        self.assert_presigned_url_matches(
            stdout, {
                'hostname': 's3.us-east-1.amazonaws.com',
                'path': '/bucket.dots/key',
                'query_params': {
                    'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
                    'X-Amz-Credential': (
                        'access_key%2F20160818%2Fus-east-1'
                        '%2Fs3%2Faws4_request'),
                    'X-Amz-Date': '20160818T143303Z',
                    'X-Amz-Expires': '3600',
                    'X-Amz-Signature': (
                        '5a032639cabfe3db0b4b87ba3b12c29f5e42fe74cbba8'
                        'a0eb69bfb30c6e2d277'),
                    'X-Amz-SignedHeaders': 'host',
                }
            }
        )

    def test_handles_expires_in(self):
        expires_in = 1000
        stdout = self.get_presigned_url_for_cmd(
            self.prefix + 's3://bucket/key --expires-in %s' % expires_in)

        self.assert_presigned_url_matches(
            stdout, {
                'hostname': 'bucket.s3.us-east-1.amazonaws.com',
                'path': '/key',
                'query_params': {
                    'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
                    'X-Amz-Credential': (
                        'access_key%2F20160818%2Fus-east-1'
                        '%2Fs3%2Faws4_request'),
                    'X-Amz-Date': '20160818T143303Z',
                    'X-Amz-Expires': '{}'.format(expires_in),
                    'X-Amz-Signature': (
                        '865fb61b021c3bf406c40d41353f584835fff1f158cf1b'
                        '3e6ec06260ecbb8937'),
                    'X-Amz-SignedHeaders': 'host',
                }
            }
        )

    def test_handles_sigv4(self):
        with temporary_file('w') as f:
            self.enable_sigv4_from_config_file(f)
            stdout = self.get_presigned_url_for_cmd(
                self.prefix + 's3://bucket/key')

        expected = {
            'hostname': 'bucket.s3.us-east-1.amazonaws.com',
            'path': '/key',
            'query_params': {
                'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
                'X-Amz-Credential': (
                    'access_key%2F20160818%2Fus-east-1'
                    '%2Fs3%2Faws4_request'),
                'X-Amz-Date': '20160818T143303Z',
                'X-Amz-Expires': '3600',
                'X-Amz-Signature': (
                    '1297528058f2c8b89cfa52c6a47d6c548907'
                    '00a1da24702b06d53e774c0acc95'
                ),
                'X-Amz-SignedHeaders': 'host'
            }
        }
        self.assert_presigned_url_matches(stdout, expected)

    def test_s3_prefix_not_needed(self):
        # Consistent with the 'ls' command.
        stdout = self.get_presigned_url_for_cmd(
            self.prefix + 'bucket/key')

        self.assert_presigned_url_matches(
            stdout, {
                'hostname': 'bucket.s3.us-east-1.amazonaws.com',
                'path': '/key',
                'query_params': {
                    'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
                    'X-Amz-Credential': (
                        'access_key%2F20160818%2Fus-east-1'
                        '%2Fs3%2Faws4_request'),
                    'X-Amz-Date': '20160818T143303Z',
                    'X-Amz-Expires': '3600',
                    'X-Amz-Signature': (
                        '1297528058f2c8b89cfa52c6a47d6c54890700a1da2470'
                        '2b06d53e774c0acc95'),
                    'X-Amz-SignedHeaders': 'host',
                }
            }
        )

    def test_can_support_addressing_mode_config(self):
        with temporary_file('w') as f:
            self.enable_addressing_mode_in_config(f, 'path')
            stdout = self.get_presigned_url_for_cmd(
                self.prefix + 's3://bucket/key')
        self.assert_presigned_url_matches(
            stdout, {
                'hostname': 's3.us-east-1.amazonaws.com',
                'path': '/bucket/key',
                'query_params': {
                    'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
                    'X-Amz-Credential': (
                        'access_key%2F20160818%2Fus-east-1'
                        '%2Fs3%2Faws4_request'),
                    'X-Amz-Date': '20160818T143303Z',
                    'X-Amz-Expires': '3600',
                    'X-Amz-Signature': (
                        'c6dab3560db76aded03e6268338ddb0a6dec00ebc82d6e'
                        '7abdc305529fcaba74'),
                    'X-Amz-SignedHeaders': 'host',
                }
            }
        )
