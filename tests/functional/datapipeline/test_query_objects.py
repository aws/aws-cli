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


class TestDataPipelineQueryObjects(BaseAWSCommandParamsTest):
    maxDiff = None

    prefix = 'datapipeline query-objects '

    def test_renamed_object_query_arg(self):
        # --query is renamed to --objects-query so we don't
        # conflict with the global --query argument.
        args = ('--pipeline-id foo '
                '--sphere INSTANCE '
                '--objects-query {"selectors":[{"fieldName":"@status",'
                '"operator":{"type":"EQ","values":["RUNNING"]}}]}')
        cmdline = self.prefix + args
        expected = {
            'pipelineId': 'foo',
            'query': {'selectors': [{'fieldName': '@status',
                                     'operator': {'type': 'EQ',
                                                  'values': ['RUNNING']}}]},
            'sphere': 'INSTANCE'
        }
        self.assert_params_for_cmd(cmdline, expected)
