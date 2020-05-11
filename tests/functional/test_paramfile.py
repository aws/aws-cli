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
import os

from mock import patch, ANY

from awscli.testutils import FileCreator, BaseAWSCommandParamsTest
from awscli.clidriver import create_clidriver

logger = logging.getLogger(__name__)


class BaseTestCLIFollowParamFile(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseTestCLIFollowParamFile, self).setUp()
        self.files = FileCreator()
        self.prefix = 'lambda get-function --function-name'

    def tearDown(self):
        super(BaseTestCLIFollowParamFile, self).tearDown()
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


class TestCLIFollowParamFileDefault(BaseTestCLIFollowParamFile):
    def test_does_not_prefixes_when_none_in_param(self):
        self.assert_param_expansion_is_correct(
            provided_param='foobar',
            expected_param='foobar'
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


class TestCLIUseEncodingFromEnv(BaseTestCLIFollowParamFile):

    def test_does_use_encoding_utf8(self):
        self.environ['AWS_CLI_FILE_ENCODING'] = 'utf-8'
        path = self.files.create_file('foobar.txt', '經理')
        param = 'file://%s' % path
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param='經理'
        )

    def test_does_use_encoding_cp1251(self):
        self.environ['AWS_CLI_FILE_ENCODING'] = 'cp1251'
        path = self.files.create_file('foobar.txt', '經理')
        param = 'file://%s' % path
        self.assert_param_expansion_is_correct(
            provided_param=param,
            expected_param='з¶“зђ†'
        )
