#!/usr/bin/env python
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
from awscli.testutils import BaseAWSCommandParamsTest, unittest
from awscli.testutils import temporary_file

from awscli.customizations.datapipeline import QueryArgBuilder
from dateutil.parser import parse


# We're not interested in testing the def->api
# translation process (that has its own test suite),
# but we need something basic enough that shows us
# that we're serializing arguments properly.
TEST_JSON = """\
{"objects": [
{
  "id" : "S3ToS3Copy",
  "type" : "CopyActivity",
  "schedule" : { "ref" : "CopyPeriod" },
  "input" : { "ref" : "InputData" },
  "output" : { "ref" : "OutputData" }
}
]}"""


class TestPutPipelineDefinition(BaseAWSCommandParamsTest):

    prefix = 'datapipeline put-pipeline-definition'

    def test_put_pipeline_definition_with_json(self):
        with temporary_file('r+') as f:
            f.write(TEST_JSON)
            f.flush()
            cmdline = self.prefix
            cmdline += ' --pipeline-id name'
            cmdline += ' --pipeline-definition file://%s' % f.name
            result = {
                'pipelineId': 'name',
                'pipelineObjects': [
                    {"id": "S3ToS3Copy",
                     "name": "S3ToS3Copy",
                     "fields": [
                       {
                         "key": "input",
                         "refValue": "InputData"
                       },
                       {
                         "key": "output",
                         "refValue": "OutputData"
                       },
                       {
                         "key": "schedule",
                         "refValue": "CopyPeriod"
                       },
                       {
                         "key": "type",
                         "stringValue": "CopyActivity"
                       },
                     ]}]
            }
            self.assert_params_for_cmd(cmdline, result)


class TestErrorMessages(BaseAWSCommandParamsTest):
    prefix = 'datapipeline list-runs'

    def test_unknown_status(self):
        self.assert_params_for_cmd(
            self.prefix + ' --pipeline-id foo --status foo',
            expected_rc=255,
            stderr_contains=('Invalid status: foo, must be one of: waiting, '
                             'pending, cancelled, running, finished, '
                             'failed, waiting_for_runner, '
                             'waiting_on_dependencies'))


class FakeParsedArgs(object):
    def __init__(self, start_interval=None, schedule_interval=None,
                 status=None):
        self.start_interval = start_interval
        self.schedule_interval = schedule_interval
        self.status = status


class TestCLIArgumentSerialize(unittest.TestCase):
    maxDiff = None

    # These tests verify that we go from --cli-args
    # to the proper structure needed for the "Query"
    # argument to describe objects.
    def test_build_query_args_default(self):
        parsed_args = FakeParsedArgs()
        current_time = '2014-02-21T00:00:00'
        start_time = '2014-02-17T00:00:00'
        builder = QueryArgBuilder(current_time=parse(current_time))
        query = builder.build_query(parsed_args)
        self.assertEqual(query, {
            'selectors': [{
                'fieldName': '@actualStartTime',
                 'operator': {
                     'type': 'BETWEEN',
                     'values': [start_time, current_time]
                 }
            }]
        })

    def test_build_args_with_start_interval(self):
        parsed_args = FakeParsedArgs(
            start_interval=['2014-02-01T00:00:00',
                            '2014-02-04T00:00:00',]
        )
        builder = QueryArgBuilder()
        query = builder.build_query(parsed_args)
        self.assertEqual(query, {
            'selectors': [{
                'fieldName': '@actualStartTime',
                 'operator': {
                     'type': 'BETWEEN',
                     'values': ['2014-02-01T00:00:00',
                                '2014-02-04T00:00:00']
                 }
            }]
        })

    def test_build_args_with_end_interval(self):
        parsed_args = FakeParsedArgs(
            schedule_interval=['2014-02-01T00:00:00',
                               '2014-02-04T00:00:00',]
        )
        builder = QueryArgBuilder()
        query = builder.build_query(parsed_args)
        self.assertEqual(query, {
            'selectors': [{
                'fieldName': '@scheduledStartTime',
                 'operator': {
                     'type': 'BETWEEN',
                     'values': ['2014-02-01T00:00:00',
                                '2014-02-04T00:00:00']
                 }
            }]
        })

    def test_build_args_with_single_status(self):
        # --status pending
        parsed_args = FakeParsedArgs(
            status=['pending']
        )
        current_time = '2014-02-21T00:00:00'
        start_time = '2014-02-17T00:00:00'
        builder = QueryArgBuilder(current_time=parse(current_time))
        query = builder.build_query(parsed_args)
        self.assertEqual(query, {
            'selectors': [{
                'fieldName': '@actualStartTime',
                 'operator': {
                     'type': 'BETWEEN',
                     'values': [start_time, current_time]
                 }
            }, {
                'fieldName': '@status',
                 'operator': {
                     'type': 'EQ',
                     'values': ['PENDING']
                 }
            },
            ]
        })

    def test_build_args_with_csv_status(self):
        # --status pending,waiting_on_dependencies
        parsed_args = FakeParsedArgs(
            status=['pending', 'waiting_on_dependencies']
        )
        current_time = '2014-02-21T00:00:00'
        start_time = '2014-02-17T00:00:00'
        builder = QueryArgBuilder(current_time=parse(current_time))
        query = builder.build_query(parsed_args)
        self.assertEqual(query, {
            'selectors': [{
                'fieldName': '@actualStartTime',
                 'operator': {
                     'type': 'BETWEEN',
                     'values': [start_time, current_time]
                 }
            }, {
                'fieldName': '@status',
                 'operator': {
                     'type': 'EQ',
                     'values': ['PENDING', 'WAITING_ON_DEPENDENCIES']
                 }
            },
            ]
        })

    def test_build_args_with_all_values_set(self):
        # --status pending,waiting_on_dependencies
        # --start-interval pending,waiting_on_dependencies
        # --schedule-schedule pending,waiting_on_dependencies
        parsed_args = FakeParsedArgs(
            start_interval=['2014-02-01T00:00:00',
                            '2014-02-04T00:00:00',],
            schedule_interval=['2014-02-05T00:00:00',
                               '2014-02-09T00:00:00',],
            status=['pending', 'waiting_on_dependencies'],
        )
        builder = QueryArgBuilder()
        query = builder.build_query(parsed_args)
        self.assertEqual(query, {
            'selectors': [{
                'fieldName': '@actualStartTime',
                 'operator': {
                     'type': 'BETWEEN',
                     'values': ['2014-02-01T00:00:00',
                                '2014-02-04T00:00:00',],
                 }
            }, {
                'fieldName': '@scheduledStartTime',
                 'operator': {
                     'type': 'BETWEEN',
                     'values': ['2014-02-05T00:00:00',
                                '2014-02-09T00:00:00']
                 }
            }, {
                'fieldName': '@status',
                 'operator': {
                     'type': 'EQ',
                     'values': ['PENDING', 'WAITING_ON_DEPENDENCIES']
                 }
            },]
        })
