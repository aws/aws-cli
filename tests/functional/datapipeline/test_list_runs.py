# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

    prefix = 'datapipeline list-runs '

    def _generate_pipeline_objects(self, object_ids):
        objects = []
        for object_id in object_ids:
            objects.append({
                'id': object_id,
                'name': object_id,
                'fields': [
                    {'key': '@componentParent', 'stringValue': object_id}
                ]
            })
        return objects

    def test_list_more_than_one_hundred_runs(self):
        start_date = '2017-10-22T00:37:21'
        end_date = '2017-10-26T00:37:21'
        pipeline_id = 'pipeline-id'
        args = '--pipeline-id %s --start-interval %s,%s' % (
            pipeline_id, start_date, end_date
        )
        command = self.prefix + args
        object_ids = ['object-id-%s' % i for i in range(150)]
        objects = self._generate_pipeline_objects(object_ids)

        self.parsed_responses = [
            {
                'ids': object_ids[:100],
                'hasMoreResults': True,
                'marker': 'marker'
            },
            {
                'ids': object_ids[100:],
                'hasMoreResults': False
            },
            {'pipelineObjects': objects[:100]},
            {'pipelineObjects': objects[100:]}
        ]

        self.run_cmd(command, expected_rc=None)

        query = {
            'selectors': [{
                'fieldName': '@actualStartTime',
                'operator': {
                    'type': 'BETWEEN',
                    'values': [start_date, end_date]
                }
            }]
        }

        expected_operations_called = [
            ('QueryObjects', {
                'pipelineId': pipeline_id,
                'query': query, 'sphere': 'INSTANCE'
            }),
            ('QueryObjects', {
                'pipelineId': pipeline_id,
                'marker': 'marker', 'query': query, 'sphere': 'INSTANCE'
            }),
            ('DescribeObjects', {
                'objectIds': object_ids[:100],
                'pipelineId': pipeline_id
            }),
            ('DescribeObjects', {
                'objectIds': object_ids[100:],
                'pipelineId': pipeline_id
            })
        ]
        operations_called = [(op.name, params)
                             for op, params in self.operations_called]
        self.assertEqual(expected_operations_called, operations_called)
