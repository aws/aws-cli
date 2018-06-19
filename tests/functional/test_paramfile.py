# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json
import logging

from mock import patch, Mock, mock_open

from awscli.testutils import FileCreator, BaseCLIWireResponseTest
from awscli.clidriver import create_clidriver
from botocore.vendored import requests

logger = logging.getLogger(__name__)


class FakeResponse(object):
    def __init__(self, *args, **kwargs):
        self.status_code = 200
        self.text = 'function-name'


class BaseTestCLIFollowParamURL(BaseCLIWireResponseTest):
    def setUp(self):
        super(BaseTestCLIFollowParamURL, self).setUp()
        self.wire_response = json.dumps({}).encode('utf-8')
        self.patch_send(content=self.wire_response)
        self.files = FileCreator()
        self.command_prefix = ['lambda', 'get-function', '--function-name']
        self.start_patches()

    def tearDown(self):
        super(BaseTestCLIFollowParamURL, self).tearDown()
        self.files.remove_all()
        self.stop_patches()

    def start_patches(self):
        self.mock_open = mock_open(read_data='function-name')
        self.open_patch = patch(
            'awscli.paramfile.compat_open', self.mock_open
        )
        self.open_patch.start()

        self.mock_get = Mock(spec=requests.get, side_effect=FakeResponse)
        self.requests_patch = patch(
            'awscli.paramfile.requests.get', self.mock_get
        )
        self.requests_patch.start()

    def stop_patches(self):
        self.requests_patch.stop()
        self.open_patch.stop()

    def run_cmd_with_arg(self, argument):
        command = self.command_prefix + [argument]
        self.run_cmd(command)


class TestCLIFollowParamURLDefault(BaseTestCLIFollowParamURL):
    def test_does_not_prefixes_when_none_in_param(self):
        self.run_cmd_with_arg('foobar')

        self.assertFalse(self.mock_get.called)
        self.assertFalse(self.mock_open.called)

    def test_does_use_http_prefix(self):
        param = 'http://foobar.com'
        self.run_cmd_with_arg(param)

        self.assertTrue(self.mock_get.called)
        self.mock_get.assert_called_once_with(param)

    def test_does_use_https_prefix(self):
        param = 'https://foobar.com'
        self.run_cmd_with_arg(param)

        self.assertTrue(self.mock_get.called)
        self.mock_get.assert_called_once_with(param)

    def test_does_use_file_prefix(self):
        param = 'file://foobar.txt'
        self.run_cmd_with_arg(param)

        self.assertFalse(self.mock_get.called)
        self.mock_open.assert_called_once_with('foobar.txt', 'r')

    def test_does_use_fileb_prefix(self):
        param = 'fileb://foobar.txt'
        self.run_cmd_with_arg(param)

        self.assertFalse(self.mock_get.called)
        self.mock_open.assert_called_once_with('foobar.txt', 'rb')


class TestCLIFollowParamURLDisabled(BaseTestCLIFollowParamURL):
    def setUp(self):
        super(TestCLIFollowParamURLDisabled, self).setUp()
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config',
            '[default]\ncli_follow_urlparam = false\n')
        self.driver = create_clidriver()

    def test_does_not_prefixes_when_none_in_param(self):
        self.run_cmd_with_arg('foobar')

        self.assertFalse(self.mock_get.called)
        self.assertFalse(self.mock_open.called)

    def test_does_not_use_http_prefix(self):
        param = 'http://foobar.com'
        self.run_cmd_with_arg(param)

        self.assertFalse(self.mock_get.called)
        self.assertFalse(self.mock_open.called)

    def test_does_not_use_https_prefix(self):
        param = 'https://foobar.com'
        self.run_cmd_with_arg(param)

        self.assertFalse(self.mock_get.called)
        self.assertFalse(self.mock_open.called)

    def test_does_use_file_prefix(self):
        param = 'file://foobar.txt'
        self.run_cmd_with_arg(param)

        self.assertFalse(self.mock_get.called)
        self.mock_open.assert_called_once_with('foobar.txt', 'r')

    def test_does_not_disable_fileb(self):
        param = 'fileb://foobar.txt'
        self.run_cmd_with_arg(param)

        self.assertFalse(self.mock_get.called)
        self.mock_open.assert_called_once_with('foobar.txt', 'rb')


class TestCLIFollowParamURLEnabled(BaseTestCLIFollowParamURL):
    def setUp(self):
        super(TestCLIFollowParamURLEnabled, self).setUp()
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config',
            '[default]\ncli_follow_urlparam = true\n')
        self.driver = create_clidriver()

    def test_does_not_prefixes_when_none_in_param(self):
        self.run_cmd_with_arg('foobar')

        self.assertFalse(self.mock_get.called)
        self.assertFalse(self.mock_open.called)

    def test_does_use_http_prefix(self):
        param = 'http://foobar.com'
        self.run_cmd_with_arg(param)

        self.assertTrue(self.mock_get.called)
        self.assertFalse(self.mock_open.called)

    def test_does_use_https_prefix(self):
        param = 'https://foobar.com'
        self.run_cmd_with_arg(param)

        self.assertTrue(self.mock_get.called)
        self.assertFalse(self.mock_open.called)

    def test_does_use_file_prefix(self):
        param = 'file://foobar.txt'
        self.run_cmd_with_arg(param)

        self.assertFalse(self.mock_get.called)
        self.mock_open.assert_called_once_with('foobar.txt', 'r')

    def test_does_use_fileb_prefix(self):
        param = 'fileb://foobar.txt'
        self.run_cmd_with_arg(param)

        self.assertFalse(self.mock_get.called)
        self.mock_open.assert_called_once_with('foobar.txt', 'rb')
