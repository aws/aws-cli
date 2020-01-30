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
import mock

from awscli.testutils import BaseAWSCommandParamsTest


class TestCreateInvalidation(BaseAWSCommandParamsTest):

    prefix = 'cloudfront create-invalidation --distribution-id my_id '

    def test_invalidation_batch_only(self):
        batch = "Paths={Quantity=2,Items=[foo.txt,bar.txt]},CallerReference=ab"
        cmdline = self.prefix + '--invalidation-batch ' + batch
        result = {
            'DistributionId': 'my_id',
            'InvalidationBatch': {
                'Paths': {'Items': ['foo.txt', 'bar.txt'], 'Quantity': 2},
                'CallerReference': 'ab',
                },
            }
        self.assert_params_for_cmd(cmdline, result)

    def test_paths_only(self):
        cmdline = self.prefix + '--paths index.html foo.txt'
        result = {
            'DistributionId': 'my_id',
            'InvalidationBatch': {
                'Paths': {'Items': ['index.html', 'foo.txt'], 'Quantity': 2},
                'CallerReference': mock.ANY,
                },
            }
        self.run_cmd(cmdline)
        self.assertEqual(self.last_kwargs, result)

    def test_invalidation_batch_and_paths(self):
        cmdline = self.prefix + '--invalidation-batch {} --paths foo'
        self.run_cmd(cmdline, expected_rc=252)

    def test_neither_invalidation_batch_or_paths(self):
        self.run_cmd(self.prefix, expected_rc=252)
