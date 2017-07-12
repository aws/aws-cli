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
from awscli.testutils import BaseAWSCommandParamsTest
import mock
from awscli.customizations.configure.rotate import ConfigureRotateCommand
from awscli.compat import six
from botocore.credentials import Credentials
from . import FakeSession
import os


class TestRotateAccessKeys(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestRotateAccessKeys, self).setUp()
        config_file_vars = {
            'region': 'us-west-2'
        }
        self.mock_session = FakeSession(
            all_variables={'config_file': '/config/location'},
            config_file_vars=config_file_vars,
            credentials=Credentials('PLOP', 'SECRET'))
        self.mock_session.session_var_map = {'region': ('region', "AWS_REGION")}
        self.mock_session.full_config = {
            'profiles': {'default': {'region': 'AWS_REGION'}}}
        self.mock_iam = mock.Mock()
        self.mock_session.create_client = lambda name, **_: self.mock_iam

        self.mock_iam.list_access_keys.return_value = {
            "AccessKeyMetadata":
                [{"UserName": "Toto", "Status": "Active", "AccessKeyId": "PLOP"}]}

        self.mock_iam.create_access_key.return_value = {
            "AccessKey":
                {"AccessKeyId": "AKIAXXX", "SecretAccessKey": "foobarbaz"}}

    def test_rotate_access_key(self):
        stream = six.StringIO()
        config = mock.Mock()
        self.configure_list = ConfigureRotateCommand(self.mock_session, config_writer=config, stream=stream)
        self.configure_list(args=[], parsed_globals=None)
        self.mock_iam.create_access_key.assert_called_with(UserName="Toto")
        self.mock_iam.delete_access_key.assert_called_with(UserName="Toto", AccessKeyId="PLOP")
        fake_path = os.path.expanduser(self.mock_session.get_config_variable('credentials_file'))
        config.update_config.assert_called_with({"__section__": "default", "aws_access_key_id": "AKIAXXX",
                                                "aws_secret_access_key": "foobarbaz"}, fake_path)

    def test_rotate_access_key_two_keys(self):
        self.mock_iam.list_access_keys.return_value = {
            "AccessKeyMetadata":
                [{"UserName": "Toto", "Status": "Active", "AccessKeyId": "PLOP"},
                 {"UserName": "Toto", "Status": "Active", "AccessKeyId": "PLOP2"}]}
        stream = six.StringIO()
        config = mock.Mock()
        self.configure_list = ConfigureRotateCommand(self.mock_session, config_writer=config, stream=stream)
        self.configure_list(args=[], parsed_globals=None)
        self.assertTrue('Cannot rotate' in stream.getvalue())
        self.assertFalse(self.mock_iam.create_access_key.called)
        self.assertFalse(self.mock_iam.delete_access_key.called)
        self.assertFalse(config.update_config.called)

    def test_rotate_access_key_non_existing_key(self):
        self.mock_iam.list_access_keys.return_value = {
            "AccessKeyMetadata":
                [{"UserName": "Toto", "Status": "Active", "AccessKeyId": "PLOP3"}]}
        stream = six.StringIO()
        config = mock.Mock()
        self.configure_list = ConfigureRotateCommand(self.mock_session, config_writer=config, stream=stream)
        self.configure_list(args=[], parsed_globals=None)
        self.assertTrue('Cannot find key PLOP' in stream.getvalue())
        self.assertFalse(self.mock_iam.create_access_key.called)
        self.assertFalse(self.mock_iam.delete_access_key.called)
        self.assertFalse(config.update_config.called)