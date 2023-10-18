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
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import FileCreator


class BaseQuickSightAssetBundleTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseQuickSightAssetBundleTest, self).setUp()
        self.files = FileCreator()
        self.temp_file = self.files.create_file(
            'foo', 'mycontents')
        with open(self.temp_file, 'rb') as f:
            self.temp_file_bytes = f.read()

    def tearDown(self):
        super(BaseQuickSightAssetBundleTest, self).tearDown()
        self.files.remove_all()


class TestStartAssetBundleImportJob(BaseQuickSightAssetBundleTest):
    prefix = 'quicksight start-asset-bundle-import-job ' \
             '--aws-account-id 123456789012 ' \
             '--asset-bundle-import-job-id import-job-1 '

    def test_can_provide_source_body_as_top_level_param(self):
        cmdline = self.prefix
        cmdline += f' --asset-bundle-import-source-bytes fileb://{self.temp_file}'
        result = {
            'AwsAccountId': '123456789012',
            'AssetBundleImportJobId': 'import-job-1',
            'AssetBundleImportSource': {'Body': self.temp_file_bytes},
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_can_provide_source_body_as_nested_param(self):
        cmdline = self.prefix
        cmdline += ' --asset-bundle-import-source Body=aGVsbG8gd29ybGQ='
        result = {
            'AwsAccountId': '123456789012',
            'AssetBundleImportJobId': 'import-job-1',
            'AssetBundleImportSource': {'Body': 'aGVsbG8gd29ybGQ='},
        }
        self.assert_params_for_cmd(cmdline, result)
