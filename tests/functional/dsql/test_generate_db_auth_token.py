# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from dateutil.tz import tzutc

from awscli.botocore.compat import parse_qs, urlparse
from awscli.testutils import BaseAWSCommandParamsTest, mock


class BaseTestGenerateDBConnectAuthToken(BaseAWSCommandParamsTest):
    hostname = 'test.dsql.us-east-1.on.aws'

    def _urlparse(self, url):
        if isinstance(url, bytes):
            # Not really necessary, but it helps to reduce noise on Python 2.x
            url = url.decode('utf8')
        return urlparse(url)

    def assert_url_equal(self, generated_url, expected_url):
        parts1 = self._urlparse(generated_url)
        parts2 = self._urlparse(expected_url)

        # Because the query string ordering isn't relevant, we have to parse
        # every single part manually and then handle the query string.
        self.assertEqual(parts1.scheme, parts2.scheme)
        self.assertEqual(parts1.netloc, parts2.netloc)
        self.assertEqual(parts1.path, parts2.path)
        self.assertEqual(parts1.password, parts2.password)
        self.assertEqual(parts1.hostname, parts2.hostname)
        self.assertEqual(parse_qs(parts1.query), parse_qs(parts2.query))


class TestGenerateDBConnectAuthToken(BaseTestGenerateDBConnectAuthToken):
    prefix = 'dsql generate-db-connect-auth-token'

    def test_generate_simple_token(self):
        region = "us-east-1"
        command = f"{self.prefix} --hostname {self.hostname} --region {region}"
        clock = datetime.datetime(2024, 11, 7, 17, 39, 33, tzinfo=tzutc())

        with mock.patch('datetime.datetime') as dt:
            dt.utcnow.return_value = clock
            stdout, _, _ = self.run_cmd(command, expected_rc=0)

        # Expected hashes are always the same as session variables come from the BaseAwsCommandParamsTest class
        expected = (
            'test.dsql.us-east-1.on.aws/?'
            'Action=DbConnect&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential='
            'access_key%2F20241107%2Fus-east-1%2Fdsql%2Faws4_request&'
            'X-Amz-Date=20241107T173933Z&X-Amz-Expires=900&'
            'X-Amz-SignedHeaders=host&X-Amz-Signature='
            'e319d85380261f643d78a558f76257f05aacea758a6ccd42a2510e2ae0854a47'
        )

        # A scheme needs to be appended to the beginning or urlsplit may fail
        # on certain systems.
        self.assert_url_equal(
            'https://' + stdout.strip('\n'), 'https://' + expected
        )

    def test_missing_hostname_raises_exception(self):
        region = "us-east-1"
        action = "DbConnectSuperuser"
        expires_in = "3600"

        command = self.prefix + ' --region ' + region + ' --action ' + action
        command += ' --expires-in ' + expires_in
        clock = datetime.datetime(2024, 11, 7, 17, 39, 33, tzinfo=tzutc())

        with mock.patch('datetime.datetime') as dt:
            dt.utcnow.return_value = clock
            stdout, _, _ = self.run_cmd(command, expected_rc=252)


class TestGenerateDBConnectAdminAuthToken(BaseTestGenerateDBConnectAuthToken):
    prefix = 'dsql generate-db-connect-admin-auth-token'

    def test_generate_simple_token(self):
        region = "us-east-1"
        command = f"{self.prefix} --hostname {self.hostname} --region {region}"
        clock = datetime.datetime(2024, 11, 7, 17, 39, 33, tzinfo=tzutc())

        with mock.patch('datetime.datetime') as dt:
            dt.utcnow.return_value = clock
            stdout, _, _ = self.run_cmd(command, expected_rc=0)

        # Expected hashes are always the same as session variables come from the BaseAwsCommandParamsTest class
        expected = (
            'test.dsql.us-east-1.on.aws/?'
            'Action=DbConnectAdmin&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential='
            'access_key%2F20241107%2Fus-east-1%2Fdsql%2Faws4_request'
            '&X-Amz-Date=20241107T173933Z&X-Amz-Expires=900&X-Amz-SignedHeaders=host&'
            'X-Amz-Signature=a08adc4c84a490014ce374b90c98ba9ed015b77b451c0d9f9fb3f8ca8c6f9c36'
        )

        # A scheme needs to be appended to the beginning or urlsplit may fail
        # on certain systems.
        self.assert_url_equal(
            'https://' + stdout.strip('\n'), 'https://' + expected
        )
