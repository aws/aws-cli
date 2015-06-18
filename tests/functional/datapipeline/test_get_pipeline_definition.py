# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestGetPipelineDefinition(BaseAWSCommandParamsTest):

    prefix = 'datapipeline get-pipeline-definition '

    def test_renamed_object_query_arg(self):
        # --version is renamed to --pipeline-version so we don't
        # conflict with the global --version argument.
        cmdline = self.prefix + '--pipeline-id foo --pipeline-version latest'
        expected = {
            'pipelineId': 'foo', 'version': 'latest'
        }
        self.assert_params_for_cmd(cmdline, expected)
