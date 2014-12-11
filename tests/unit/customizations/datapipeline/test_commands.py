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
import copy
import mock

from awscli.compat import six
from awscli.testutils import BaseAWSHelpOutputTest, BaseAWSCommandParamsTest, \
        unittest

from awscli.customizations.datapipeline import convert_described_objects
from awscli.customizations.datapipeline import ListRunsCommand
from awscli.customizations.datapipeline import ListRunsFormatter


API_DESCRIBE_OBJECTS = [
    {"fields": [
         {
             "key": "@componentParent",
             "refValue": "S3Input"
         },
         {
             "key": "@scheduledStartTime",
             "stringValue": "2013-08-19T20:00:00"
         },
         {
             "key": "parent",
             "refValue": "S3Input"
         },
         {
             "key": "@sphere",
             "stringValue": "INSTANCE"
         },
         {
             "key": "type",
             "stringValue": "S3DataNode"
         },
         {
             "key": "@version",
             "stringValue": "1"
         },
         {
             "key": "@status",
             "stringValue": "FINISHED"
         },
         {
             "key": "@actualEndTime",
             "stringValue": "2014-02-19T19:44:44"
         },
         {
             "key": "@actualStartTime",
             "stringValue": "2014-02-19T19:44:43"
         },
         {
             "key": "output",
             "refValue": "@MyCopyActivity_2013-08-19T20:00:00"
         },
         {
             "key": "@scheduledEndTime",
             "stringValue": "2013-08-19T21:00:00"
         }
        ],
        "id": "@S3Input_2013-08-19T20:00:00",
        "name": "@S3Input_2013-08-19T20:00:00"
    },
    {"fields": [
         {
             "key": "@componentParent",
             "refValue": "MyEC2Resource"
         },
         {
             "key": "@resourceId",
             "stringValue": "i-12345"
         },
         {
             "key": "@scheduledStartTime",
             "stringValue": "2013-08-19T23:00:00"
         },
         {
             "key": "parent",
             "refValue": "MyEC2Resource"
         },
         {
             "key": "@sphere",
             "stringValue": "INSTANCE"
         },
         {
             "key": "@attemptCount",
             "stringValue": "1"
         },
         {
             "key": "type",
             "stringValue": "Ec2Resource"
         },
         {
             "key": "@version",
             "stringValue": "1"
         },
         {
             "key": "@status",
             "stringValue": "CREATING"
         },
         {
             "key": "input",
             "refValue": "@MyCopyActivity_2013-08-19T23:00:00"
         },
         {
             "key": "@triesLeft",
             "stringValue": "2"
         },
         {
             "key": "@actualStartTime",
             "stringValue": "2014-02-19T19:59:45"
         },
         {
             "key": "@headAttempt",
             "refValue": "@MyEC2Resource_2013-08-19T23:00:00_Attempt=1"
         },
         {
             "key": "@scheduledEndTime",
             "stringValue": "2013-08-20T00:00:00"
         }
        ],
        "id": "@MyEC2Resource_2013-08-19T23:00:00",
        "name": "@MyEC2Resource_2013-08-19T23:00:00"
    }
]

EMPTY_RUNS = """\
       Name                                                Scheduled Start      Status
       ID                                                  Started              Ended
---------------------------------------------------------------------------------------------------
"""

SINGLE_ROW_RUN = """\
       Name                                                Scheduled Start      Status
       ID                                                  Started              Ended
---------------------------------------------------------------------------------------------------
   1.  parent                                              now                  status
       id                                                  actualStartTime      actualEndTime
"""

class TestConvertObjects(unittest.TestCase):

    def test_convert_described_objects(self):
        converted = convert_described_objects(API_DESCRIBE_OBJECTS)
        self.assertEqual(len(converted), 2)
        # This comes from a "refValue" value.
        self.assertEqual(converted[0]['@componentParent'], 'S3Input')
        # Should also merge in @id and name.
        self.assertEqual(converted[0]['@id'], "@S3Input_2013-08-19T20:00:00")
        self.assertEqual(converted[0]['name'], "@S3Input_2013-08-19T20:00:00")
        # This comes from a "stringValue" value.
        self.assertEqual(converted[0]['@sphere'], "INSTANCE")

    def test_convert_objects_are_sorted(self):
        describe_objects = copy.deepcopy(API_DESCRIBE_OBJECTS)
        # Change the existing @scheduledStartTime from
        # 20:00:00 to 23:59:00
        describe_objects[0]['fields'][1]['stringValue'] = (
            "2013-08-19T23:59:00")
        converted = convert_described_objects(
            describe_objects,
            sort_key_func=lambda x: (x['@scheduledStartTime'], x['name']))
        self.assertEqual(converted[0]['@scheduledStartTime'],
                         '2013-08-19T23:00:00')
        self.assertEqual(converted[1]['@scheduledStartTime'],
                         '2013-08-19T23:59:00')


class FakeParsedArgs(object):
    def __init__(self, **kwargs):
        self.endpoint_url = None
        self.region = None
        self.verify_ssl = None
        self.__dict__.update(kwargs)


class TestCommandsRunProperly(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestCommandsRunProperly, self).setUp()
        self.query_objects = mock.Mock()
        self.describe_objects = mock.Mock()

    def get_service(self, name):
        if name == 'QueryObjects':
            return self.query_objects
        elif name== 'DescribeObjects':
            return self.describe_objects

    def test_list_runs(self):
        self.driver.session = mock.Mock()
        self.driver.session.emit_first_non_none_response.return_value = None
        self.driver.session.get_service.return_value.get_endpoint.return_value = \
                mock.sentinel.endpoint
        self.driver.session.get_service.return_value.get_operation = self.get_service
        self.query_objects.paginate.return_value.build_full_result.return_value = {
            'ids': ['object-ids']}
        self.describe_objects.call.return_value = (
            None, {'pipelineObjects': [
                {'fields': [], 'id': 'id', 'name': 'name'}]})

        command = ListRunsCommand(self.driver.session, formatter=mock.Mock())
        command(['--pipeline-id', 'my-pipeline-id'],
                parsed_globals=FakeParsedArgs(region='us-east-1'))
        self.assertTrue(self.query_objects.paginate.called)
        self.describe_objects.call.assert_called_with(
            mock.sentinel.endpoint, pipeline_id='my-pipeline-id',
            object_ids=['object-ids'])


class TestHelpOutput(BaseAWSHelpOutputTest):
    def test_list_runs_help_output(self):
        self.driver.main(['datapipeline', 'get-pipeline-definition', 'help'])
        self.assert_contains('pipeline definition')
        # The previous API docs should not be in the output
        self.assert_not_contains('pipelineObjects')


class TestListRunsFormatter(BaseAWSCommandParamsTest):
    def test_no_runs_available(self):
        stream = six.StringIO()
        formatter = ListRunsFormatter(stream)
        objects = []
        formatter.display_objects_to_user(objects)
        self.assertEqual(
            [line.strip() for line in stream.getvalue().splitlines()],
            [line.strip() for line in EMPTY_RUNS.splitlines()])

    def test_single_row(self):
        objects = [
            {'@componentParent': 'parent',
             '@id': 'id',
             '@scheduledStartTime': 'now',
             '@status': 'status',
             '@actualStartTime': 'actualStartTime',
             '@actualEndTime': 'actualEndTime',
            }
        ]
        stream = six.StringIO()
        formatter = ListRunsFormatter(stream)
        formatter.display_objects_to_user(objects)
        # Rather than stream.getvalue() == SINGLE_ROW_RUN
        # we compare equality like this to avoid test failures
        # for differences in leading/trailing whitespace and empty lines.
        self.assertEqual(
            [line.strip() for line in stream.getvalue().splitlines()
             if line.strip()],
            [line.strip() for line in SINGLE_ROW_RUN.splitlines()
             if line.strip()])
