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
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator


class BaseS3TransferCommandTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseS3TransferCommandTest, self).setUp()
        self.files = FileCreator()

    def tearDown(self):
        super(BaseS3TransferCommandTest, self).tearDown()
        self.files.remove_all()

    def assert_operations_called(self, expected_operations_with_params):
        actual_operations_with_params = [
            (operation_called[0].name, operation_called[1])
            for operation_called in self.operations_called
        ]
        self.assertEqual(
            actual_operations_with_params, expected_operations_with_params)
