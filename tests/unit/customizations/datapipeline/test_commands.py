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
import unittest

from awscli.testutils import BaseAWSHelpOutputTest, BaseAWSCommandParamsTest

from awscli.customizations.datapipeline import convert_described_objects
from awscli.customizations.datapipeline import ListRunsCommand


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

JSON_FORMATTER_PATH = 'awscli.formatter.JSONFormatter.__call__'
LIST_FORMATTER_PATH = 'awscli.customizations.datapipeline.listrunsformatter.ListRunsFormatter.__call__'  # noqa


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
        self.output = None
        self.query = None
        self.__dict__.update(kwargs)


class TestCommandsRunProperly(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestCommandsRunProperly, self).setUp()
        self.query_objects = mock.Mock()
        self.describe_objects = mock.Mock()
        self.client = mock.Mock()
        self.client.get_paginator.return_value = self.query_objects
        self.client.describe_objects = self.describe_objects

        self.driver.session = mock.Mock()
        self.driver.session.emit_first_non_none_response.return_value = None
        self.driver.session.create_client.return_value = self.client
        self.query_objects.paginate.return_value.build_full_result.\
            return_value = {'ids': ['object-ids']}
        self.describe_objects.return_value = \
            {'pipelineObjects': API_DESCRIBE_OBJECTS}
        self.expected_response = convert_described_objects(
            API_DESCRIBE_OBJECTS,
            sort_key_func=lambda x: (x['@scheduledStartTime'], x['name']))

    def test_list_runs(self):
        command = ListRunsCommand(self.driver.session)
        command(['--pipeline-id', 'my-pipeline-id'],
                parsed_globals=FakeParsedArgs(region='us-east-1'))
        self.assertTrue(self.query_objects.paginate.called)
        self.describe_objects.assert_called_with(
            pipelineId='my-pipeline-id', objectIds=['object-ids'])

    @mock.patch(JSON_FORMATTER_PATH)
    @mock.patch(LIST_FORMATTER_PATH)
    def test_list_runs_formatter_explicit_choice(
            self, list_formatter, json_formatter):
        command = ListRunsCommand(self.driver.session)
        command(['--pipeline-id', 'my-pipeline-id'],
                parsed_globals=FakeParsedArgs(
                    region='us-east-1', output='json'))
        json_formatter.assert_called_once_with(
            'list-runs', self.expected_response)
        self.assertFalse(list_formatter.called)

    @mock.patch(JSON_FORMATTER_PATH)
    @mock.patch(LIST_FORMATTER_PATH)
    def test_list_runs_formatter_implicit_choice(
            self, list_formatter, json_formatter):

        command = ListRunsCommand(self.driver.session)
        command(['--pipeline-id', 'my-pipeline-id'],
                parsed_globals=FakeParsedArgs(region='us-east-1'))
        list_formatter.assert_called_once_with(
            'list-runs', self.expected_response)
        self.assertFalse(json_formatter.called)


class TestHelpOutput(BaseAWSHelpOutputTest):
    def test_list_runs_help_output(self):
        self.driver.main(['datapipeline', 'get-pipeline-definition', 'help'])
        self.assert_contains('pipeline definition')
        # The previous API docs should not be in the output
        self.assert_not_contains('pipelineObjects')
