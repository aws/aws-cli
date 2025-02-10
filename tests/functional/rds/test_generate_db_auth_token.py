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

from dateutil.tz import tzutc
from botocore.compat import urlparse, parse_qs

from awscli.testutils import mock, BaseAWSCommandParamsTest


class TestGenerateDBAuthToken(BaseAWSCommandParamsTest):

    prefix = 'rds generate-db-auth-token'

    def _urlparse(self, url):
        if isinstance(url, bytes):
            # Not really necessary, but it helps to reduce noise on Python 2.x
            url = url.decode('utf8')
        return urlparse(url)

    def assert_url_equal(self, url1, url2):
        parts1 = self._urlparse(url1)
        parts2 = self._urlparse(url2)

        # Because the query string ordering isn't relevant, we have to parse
        # every single part manually and then handle the query string.
        self.assertEqual(parts1.scheme, parts2.scheme)
        self.assertEqual(parts1.netloc, parts2.netloc)
        self.assertEqual(parts1.path, parts2.path)
        self.assertEqual(parts1.params, parts2.params)
        self.assertEqual(parts1.fragment, parts2.fragment)
        self.assertEqual(parts1.username, parts2.username)
        self.assertEqual(parts1.password, parts2.password)
        self.assertEqual(parts1.hostname, parts2.hostname)
        self.assertEqual(parts1.port, parts2.port)
        self.assertEqual(parse_qs(parts1.query), parse_qs(parts2.query))

    def test_generate_simple_token(self):
        command = self.prefix + ' --hostname host.us-east-1.amazonaws.com'
        command += ' --port 3306 --username mySQLUser'
        clock = datetime.datetime(2016, 11, 7, 17, 39, 33, tzinfo=tzutc())

        with mock.patch('datetime.datetime') as dt:
            dt.utcnow.return_value = clock
            stdout, _, _ = self.run_cmd(command, expected_rc=0)

        expected = (
            'host.us-east-1.amazonaws.com:3306/?DBUser=mySQLUser&'
            'Action=connect&X-Amz-Credential=access_key%2F20161107%2Fus-east-1'
            '%2Frds-db%2Faws4_request&X-Amz-Expires=900&X-Amz-Date=20161107T173'
            '933Z&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-SignedHeaders=host&'
            'X-Amz-Signature=87ab58107ef49f1c311a412f98b7f976b0b5152ffb559f0d'
            '36c6c9a0c5e0e362'
        )

        self.assert_url_equal(
            'https://' + stdout.strip('\n'), 'https://' + expected)
