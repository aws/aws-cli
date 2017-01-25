# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import mock
import json
import datetime
from dateutil.tz import tzlocal
from awscli.testutils import unittest, FileCreator, capture_output
from awscli.clidriver import create_clidriver


class TestCLITimestampParser(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()
        self.environ = {
            'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
            'AWS_DEFAULT_REGION': 'us-east-1',
            'AWS_ACCESS_KEY_ID': 'access_key',
            'AWS_SECRET_ACCESS_KEY': 'secret_key',
            'AWS_CONFIG_FILE': ''
        }
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()

        self.wire_response = json.dumps({
            'builds': [{
                'startTime': 0,
            }]
        }).encode()

    def tearDown(self):
        self.environ_patch.stop()
        self.files.remove_all()

    def test_iso(self):
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'iso',
            '[default]\ncli_timestamp_format = iso8601\n')
        self.driver = create_clidriver()
        expected_time = datetime.datetime.fromtimestamp(0).replace(
            tzinfo=tzlocal()).isoformat()

        with capture_output() as captured:
            with mock.patch('botocore.endpoint.Session.send') as _send:
                _send.return_value = mock.Mock(status_code=200, headers={},
                                               content=self.wire_response)
                self.driver.main(['codebuild', 'batch-get-builds',
                                  '--ids', 'foo'])
                json_response = json.loads(captured.stdout.getvalue())
                start_time = json_response["builds"][0]["startTime"]
                self.assertEqual(expected_time, start_time)

    def test_none(self):
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'none',
            '[default]\ncli_timestamp_format = none\n')
        self.driver = create_clidriver()
        expected_time = 0

        with capture_output() as captured:
            with mock.patch('botocore.endpoint.Session.send') as _send:
                _send.return_value = mock.Mock(status_code=200, headers={},
                                               content=self.wire_response)
                self.driver.main(['codebuild', 'batch-get-builds',
                                  '--ids', 'foo'])
                json_response = json.loads(captured.stdout.getvalue())
                start_time = json_response["builds"][0]["startTime"]
                self.assertEqual(expected_time, start_time)

    def test_default(self):
        self.driver = create_clidriver()
        expected_time = 0

        with capture_output() as captured:
            with mock.patch('botocore.endpoint.Session.send') as _send:
                _send.return_value = mock.Mock(status_code=200, headers={},
                                               content=self.wire_response)
                self.driver.main(['codebuild', 'batch-get-builds',
                                  '--ids', 'foo'])
                json_response = json.loads(captured.stdout.getvalue())
                start_time = json_response["builds"][0]["startTime"]
                self.assertEqual(expected_time, start_time)
