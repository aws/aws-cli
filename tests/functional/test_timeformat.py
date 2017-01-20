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
import datetime
from dateutil.tz import tzlocal
from awscli.testutils import unittest, FileCreator
from awscli.clidriver import create_clidriver


class TestParsers(unittest.TestCase):
    def setUp(self):
        self.environ = {
            'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
            'AWS_DEFAULT_REGION': 'us-east-1',
            'AWS_ACCESS_KEY_ID': 'access_key',
            'AWS_SECRET_ACCESS_KEY': 'secret_key',
            'AWS_CONFIG_FILE': '',
            'AWS_SHARED_CREDENTIALS_FILE': '',
        }
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()

        self.files = FileCreator()
        config_contents = (
            '[default]\n'
            'cli_timestamp_format = iso8601\n'
        )
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'myconfig', config_contents)
        self.driver = create_clidriver()
        self.driver.session.emit('session-initialized',
                                 session=self.driver.session)

    def test_iso_parser(self):
        response_dict = {
            'headers': '',
            'status_code': 200,
            'body': b'0'
        }
        factory = self.driver.session.get_component('response_parser_factory')
        parser = factory.create_parser('json')
        mock_shape = mock.MagicMock()
        mock_shape.type_name = 'timestamp'

        parsed_response = parser.parse(
            response_dict, mock_shape)
        self.assertEqual(parsed_response,
                         datetime.datetime.fromtimestamp(
                             0.0,
                             tzlocal()).isoformat())
