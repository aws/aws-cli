# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestRegisterType(BaseAWSCommandParamsTest):
    prefix = 'cloudformation register-type'

    def test_schema_handler_package_during_register_url(self):
        cmdline = self.prefix
        cmdline += ' --type-name test-type-name '
        cmdline += '--schema-handler-package s3://bucket-name/my-organization-resource_name.zip'
        result = {
            'TypeName': 'test-type-name',
            'SchemaHandlerPackage': 's3://bucket-name/my-organization-resource_name.zip',
        }
        self.assert_params_for_cmd(cmdline, result)
