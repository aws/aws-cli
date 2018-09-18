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
import logging

from mock import patch, ANY

from awscli.testutils import FileCreator, BaseAWSCommandParamsTest
from awscli.clidriver import create_clidriver

logger = logging.getLogger(__name__)


class FakeResponse(object):
    def __init__(self, content):
        self.status_code = 200
        self.text = content


class BaseTestCLIFollowParamURL(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseTestCLIFollowParamURL, self).setUp()
        self.files = FileCreator()
        self.prefix = 'lambda get-function --function-name'

    def tearDown(self):
        super(BaseTestCLIFollowParamURL, self).tearDown()
        self.files.remove_all()

    def assert_param_expansion_is_correct(self, provided_param, expected_param):
        cmd = '%s %s' % (self.prefix, provided_param)
        # We do not care about the return code here. All that is of interest
        # is what happened to the arguments before they were passed to botocore
        # which we get from the params={} key. For binary types we will fail in
        # python 3 with an rc of 255 and get an rc of 0 in python 2 where it
        # can't tell the difference, so we pass ANY here to ignore the rc.
        self.assert_params_for_cmd(cmd,
                                   params={'FunctionName': expected_param},
                                   expected_rc=ANY)


class TestCLIFollowParamURLDefault(BaseTestCLIFollowParamURL):
    def test_does_not_prefixes_when_none_in_param(self):
        self.assert_param_expansion_is_correct(
            provided_param='foobar',
            expected_param='foobar'
        )

    @patch('awscli.paramfile.URLLib3Session.send')
    def test_does_use_http_prefix(self, mock_send):
        content = 'http_content'
        mock_send.return_value = FakeResponse(content=content)
        param = 'http://foobar.com'
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=content
        )

    @patch('awscli.paramfile.URLLib3Session.send')
    def test_does_use_https_prefix(self, mock_send):
        content = 'https_content'
        mock_send.return_value = FakeResponse(content=content)
        param = 'https://foobar.com'
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=content
        )

    def test_does_use_file_prefix(self):
        path = self.files.create_file('foobar.txt', 'file content')
        param = 'file://%s' % path
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param='file content'
        )

    def test_does_use_fileb_prefix(self):
        # The command will fail with error code 255 since bytes type does
        # not work for this parameter, however we still record the raw
        # parameter that we passed, which is all this test is concerend about.
        path = self.files.create_file('foobar.txt', b'file content', mode='wb')
        param = 'fileb://%s' % path
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=b'file content'
        )


class TestCLIFollowParamURLDisabled(BaseTestCLIFollowParamURL):
    def setUp(self):
        super(TestCLIFollowParamURLDisabled, self).setUp()
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config',
            '[default]\ncli_follow_urlparam = false\n')
        self.driver = create_clidriver()

    def test_does_not_prefixes_when_none_in_param(self):
        param = 'foobar'
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=param
        )

    @patch('awscli.paramfile.URLLib3Session.send')
    def test_does_not_use_http_prefix(self, mock_send):
        param = 'http://foobar'
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=param
        )
        mock_send.assert_not_called()

    @patch('awscli.paramfile.URLLib3Session.send')
    def test_does_not_use_https_prefix(self, mock_send):
        param = 'https://foobar'
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=param
        )
        mock_send.assert_not_called()

    def test_does_use_file_prefix(self):
        path = self.files.create_file('foobar.txt', 'file content')
        param = 'file://%s' % path
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param='file content'
        )

    def test_does_use_fileb_prefix(self):
        # The command will fail with error code 255 since bytes type does
        # not work for this parameter, however we still record the raw
        # parameter that we passed, which is all this test is concerend about.
        path = self.files.create_file('foobar.txt', b'file content', mode='wb')
        param = 'fileb://%s' % path
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=b'file content'
        )


class TestCLIFollowParamURLEnabled(BaseTestCLIFollowParamURL):
    def setUp(self):
        super(TestCLIFollowParamURLEnabled, self).setUp()
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config',
            '[default]\ncli_follow_urlparam = true\n')
        self.driver = create_clidriver()

    def test_does_not_prefixes_when_none_in_param(self):
        self.assert_param_expansion_is_correct('foobar', 'foobar')

    @patch('awscli.paramfile.URLLib3Session.send')
    def test_does_use_http_prefix(self, mock_send):
        content = 'http_content'
        mock_send.return_value = FakeResponse(content=content)
        param = 'http://foobar.com'
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=content
        )

    @patch('awscli.paramfile.URLLib3Session.send')
    def test_does_use_https_prefix(self, mock_send):
        content = 'https_content'
        mock_send.return_value = FakeResponse(content=content)
        param = 'https://foobar.com'
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=content
        )

    def test_does_use_file_prefix(self):
        path = self.files.create_file('foobar.txt', 'file content')
        param = 'file://%s' % path
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param='file content'
        )

    def test_does_use_fileb_prefix(self):
        # The command will fail with error code 255 since bytes type does
        # not work for this parameter, however we still record the raw
        # parameter that we passed, which is all this test is concerend about.
        path = self.files.create_file('foobar.txt', b'file content', mode='wb')
        param = 'fileb://%s' % path
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param=b'file content'
        )
