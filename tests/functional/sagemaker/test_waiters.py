# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestImageVersionWaiters(BaseAWSCommandParamsTest):
    # The image version waiters' ``Version`` parameter would otherwise be
    # exposed as ``--version``, which is shadowed by the global ``--version``
    # option.  It is renamed to ``--version-number`` to match the
    # corresponding image version operations.

    def test_image_version_created_uses_version_number(self):
        self.parsed_response = {'ImageVersionStatus': 'CREATED'}
        self.run_cmd(
            'sagemaker wait image-version-created '
            '--image-name my-image --version-number 3'
        )
        self.assertEqual(
            self.operations_called[0][1],
            {'ImageName': 'my-image', 'Version': 3},
        )

    def test_image_version_deleted_uses_version_number(self):
        # A terminal failure state makes the waiter return after one call.
        self.parsed_response = {'ImageVersionStatus': 'DELETE_FAILED'}
        self.run_cmd(
            'sagemaker wait image-version-deleted '
            '--image-name my-image --version-number 3',
            expected_rc=255,
        )
        self.assertEqual(
            self.operations_called[0][1],
            {'ImageName': 'my-image', 'Version': 3},
        )
