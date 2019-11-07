# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from awscli.testutils import mock
from awscli.testutils import create_clidriver
from awscli.testutils import FileCreator
from awscli.testutils import BaseAWSCommandParamsTest


class BaseSSOTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseSSOTest, self).setUp()
        self.files = FileCreator()
        self.start_url = 'https://mysigin.com'
        self.sso_region = 'us-west-2'
        self.account = '012345678912'
        self.role_name = 'SSORole'
        self.config_file = self.files.full_path('config')
        self.environ['AWS_CONFIG_FILE'] = self.config_file
        self.set_config_file_content()
        self.access_token = 'foo.token.string'

    def tearDown(self):
        super(BaseSSOTest, self).tearDown()
        self.files.remove_all()

    def set_config_file_content(self, content=None):
        if content is None:
            content = (
                '[default]\n'
                'sso_start_url=%s\n'
                'sso_region=%s\n'
                'sso_role_name=%s\n'
                'sso_account_id=%s\n' % (
                    self.start_url, self.sso_region, self.role_name,
                    self.account
                )
            )
        self.files.create_file(self.config_file, content)
        # We need to recreate the driver (which includes its session) in order
        # for the config changes to be pulled in by the session.
        self.driver = create_clidriver()
