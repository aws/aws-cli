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
from awscli.customizations.datapipeline.translator \
    import PipelineDefinitionError
from awscli.testutils import unittest

from botocore.compat import OrderedDict, json

from awscli.customizations.datapipeline import translator


# Thoughout these tests, 'df' refers to the condensed JSON definition format
# that the user provides and API refers to the format expected by the API.

class TestTranslatePipelineDefinitions(unittest.TestCase):
    maxDiff = None

    def load_def(self, json_string):
        return json.loads(json_string, object_pairs_hook=OrderedDict)

    def test_convert_schedule_df_to_api(self):
        definition = self.load_def("""{"objects": [
            {
              "id" : "S3ToS3Copy",
              "type" : "CopyActivity",
              "schedule" : { "ref" : "CopyPeriod" },
              "input" : { "ref" : "InputData" },
              "output" : { "ref" : "OutputData" }
            }
            ]}""")
        actual = translator.definition_to_api_objects(definition)
        api = [{"name": "S3ToS3Copy", "id": "S3ToS3Copy",
                "fields": [
                    {"key": "input", "refValue": "InputData"},
                    {"key": "output", "refValue": "OutputData"},
                    {"key": "schedule", "refValue": "CopyPeriod"},
                    {"key": "type", "stringValue": "CopyActivity"},
                ]}]
        self.assertEqual(actual, api)

    def test_convert_df_to_api_schedule(self):
        definition = self.load_def("""{
              "objects": [
                {
                  "id": "MySchedule",
                  "type": "Schedule",
                  "startDateTime": "2013-08-18T00:00:00",
                  "endDateTime": "2013-08-19T00:00:00",
                  "period": "1 day"
                }
            ]}""")
        actual = translator.definition_to_api_objects(definition)
        api = [{"name": "MySchedule", "id": "MySchedule",
                "fields": [
                    {"key": "endDateTime",
                     "stringValue": "2013-08-19T00:00:00"},
                    {"key": "period", "stringValue": "1 day"},
                    {"key": "startDateTime",
                     "stringValue": "2013-08-18T00:00:00"},
                    {"key": "type", "stringValue": "Schedule"},
                ]}]
        self.assertEqual(actual, api)

    def test_convert_df_to_api_with_name(self):
        definition = self.load_def("""{
              "objects": [
                {
                  "id": "MySchedule",
                  "name": "OVERRIDE-NAME",
                  "type": "Schedule",
                  "startDateTime": "2013-08-18T00:00:00",
                  "endDateTime": "2013-08-19T00:00:00",
                  "period": "1 day"
                }
            ]}""")
        actual = translator.definition_to_api_objects(definition)
        api = [{"name": "OVERRIDE-NAME", "id": "MySchedule",
                "fields": [
                    {"key": "endDateTime",
                     "stringValue": "2013-08-19T00:00:00"},
                    {"key": "period", "stringValue": "1 day"},
                    {"key": "startDateTime",
                     "stringValue": "2013-08-18T00:00:00"},
                    {"key": "type", "stringValue": "Schedule"},
                ]}]
        self.assertEqual(actual, api)

    def test_objects_key_is_missing_raise_error(self):
        definition = self.load_def("""{"not-objects": []}""")
        with self.assertRaises(translator.PipelineDefinitionError):
            translator.definition_to_api_objects(definition)

    def test_missing_id_field(self):
        # Note that the 'id' key is missing.
        definition = self.load_def("""{
              "objects": [
                {
                  "name": "OVERRIDE-NAME",
                  "type": "Schedule",
                  "startDateTime": "2013-08-18T00:00:00",
                  "endDateTime": "2013-08-19T00:00:00",
                  "period": "1 day"
                }
            ]}""")
        with self.assertRaises(translator.PipelineDefinitionError):
            translator.definition_to_api_objects(definition)

    def test_list_value_with_strings(self):
        definition = self.load_def("""{"objects": [
            {
              "id" : "emrActivity",
              "type" : "EmrActivity",
              "name" : "Foo",
              "step" : ["s3://foo1", "s3://foo2", "s3://foo3"]
            }
        ]}""")
        actual = translator.definition_to_api_objects(definition)
        api = [{"name": "Foo", "id": "emrActivity",
                "fields": [
                    {"key": "step", "stringValue": "s3://foo1"},
                    {"key": "step", "stringValue": "s3://foo2"},
                    {"key": "step", "stringValue": "s3://foo3"},
                    {"key": "type", "stringValue": "EmrActivity"}
                ]}]
        self.assertEqual(actual, api)

    def test_value_with_refs(self):
        definition = self.load_def("""{"objects": [
            {
              "id" : "emrActivity",
              "type" : "EmrActivity",
              "name" : "Foo",
              "step" : ["s3://foo1", {"ref": "otherValue"}, "s3://foo3"]
            }
        ]}""")
        actual = translator.definition_to_api_objects(definition)
        api = [{"name": "Foo", "id": "emrActivity",
                "fields": [
                    {"key": "step", "stringValue": "s3://foo1"},
                    {"key": "step", "refValue": "otherValue"},
                    {"key": "step", "stringValue": "s3://foo3"},
                    {"key": "type", "stringValue": "EmrActivity"}
                ]}]
        self.assertEqual(actual, api)

    # These tests check the API -> DF conversion.
    def test_api_to_df(self):
        api = {"pipelineObjects": [
            {"name": "S3ToS3Copy", "id": "S3ToS3Copy",
                "fields": [{"key": "type", "stringValue": "CopyActivity"},
                           {"key": "schedule", "refValue": "CopyPeriod"},
                           {"key": "input", "refValue": "InputData"},
                           {"key": "output", "refValue": "OutputData"}]}]}
        definition = translator.api_to_definition(api)
        self.assertEqual(definition, {
            'objects': [{
                'id': 'S3ToS3Copy',
                'name': 'S3ToS3Copy',
                'type': 'CopyActivity',
                'schedule': {'ref': 'CopyPeriod'},
                'input': {'ref': 'InputData'},
                'output': {'ref': 'OutputData'}
            }]
        })

    def test_api_to_df_with_dupe_keys(self):
        # Duplicate keys should be aggregated into a list.
        api = {"pipelineObjects": [
            {"name": "S3ToS3Copy", "id": "S3ToS3Copy",
                "fields": [{"key": "type", "stringValue": "CopyActivity"},
                           {"key": "schedule", "refValue": "CopyPeriod"},
                           {"key": "script", "stringValue": "value1"},
                           {"key": "script", "stringValue": "value2"}]}]}
        definition = translator.api_to_definition(api)
        self.assertEqual(definition, {
            'objects': [{
                'id': 'S3ToS3Copy',
                'name': 'S3ToS3Copy',
                'type': 'CopyActivity',
                'schedule': {'ref': 'CopyPeriod'},
                'script': ['value1', 'value2'],
            }]
        })

    def test_df_to_api_with_parameter_objects_missing(self):
        definition = self.load_def("""{"objects": [
            {
              "id" : "S3ToS3Copy",
              "type" : "CopyActivity",
              "schedule" : { "ref" : "CopyPeriod" },
              "input" : { "ref" : "InputData" },
              "output" : { "ref" : "OutputData" }
            }
            ]}""")
        try:
            parameters = translator.definition_to_api_parameters(definition)
            error = "Absence of parameter objects should not display anything"
            self.assertIsNone(parameters, error)
        except PipelineDefinitionError:
            self.fail("No exception should be thrown in absence of objects")

    def test_df_to_api_with_parameter_values_missing(self):
        definition = self.load_def("""{"objects": [
            {
              "id" : "S3ToS3Copy",
              "type" : "CopyActivity",
              "schedule" : { "ref" : "CopyPeriod" },
              "input" : { "ref" : "InputData" },
              "output" : { "ref" : "OutputData" }
            }
            ]}""")
        try:
            values = translator.definition_to_parameter_values(definition)
            error = "Absence of parameter values should not display anything"
            self.assertIsNone(values, error)
        except PipelineDefinitionError:
            self.fail("No exception should be thrown in absence of values")

    def test_df_to_api_with_parameter_objects(self):
        definition = self.load_def("""{"parameters": [
            {
              "id":"myOccurrenceNumber",
              "type":"Integer",
              "description":"Number of pipeline runs",
              "max":"24"
            }
            ]}""")
        actual = translator.definition_to_api_parameters(definition)
        api = [{"id": "myOccurrenceNumber",
                "attributes": [
                    {"key": "description",
                     "stringValue": "Number of pipeline runs"},
                    {"key": "max",
                     "stringValue": "24"},
                    {"key": "type",
                     "stringValue": "Integer"}
                ]}]
        self.assertEqual(actual, api)

    def test_df_to_api_with_parameter_values(self):
        definition = self.load_def("""{"values": {
              "myMaximumRetries":"2",
              "myOccurrenceNumber":"3"
            }
            }""")
        actual = translator.definition_to_parameter_values(definition)
        api = [{"id": "myMaximumRetries", "stringValue": "2"},
               {"id": "myOccurrenceNumber", "stringValue": "3"}]
        self.assertEqual(actual, api)

    def test_df_to_api_with_parameter_objects_array(self):
        definition = self.load_def("""{"parameters": [
            {
              "id":"myOccurrenceNumber",
              "type":"Integer",
              "description":["part1","part2"],
              "max":"24"
            }
            ]}""")
        actual = translator.definition_to_api_parameters(definition)
        api = [{"id": "myOccurrenceNumber",
                "attributes": [
                    {"key": "description",
                     "stringValue": "part1"},
                    {"key": "description",
                     "stringValue": "part2"},
                    {"key": "max",
                     "stringValue": "24"},
                    {"key": "type",
                     "stringValue": "Integer"}
                ]}]
        self.assertEqual(actual, api)

    def test_df_to_api_with_parameter_values_array(self):
        definition = self.load_def("""{"values": {
              "myMaximumRetries":["value1", "value2"],
              "myOccurrenceNumber":"3"
            }
            }""")
        actual = translator.definition_to_parameter_values(definition)
        api = [{"id": "myMaximumRetries", "stringValue": "value1"},
               {"id": "myMaximumRetries", "stringValue": "value2"},
               {"id": "myOccurrenceNumber", "stringValue": "3"}]
        self.assertEqual(actual, api)

    def test_api_to_df_with_parameter_objects_and_values(self):
        # Tests for proper handling of parameter value arrays as well
        api = {"parameterObjects": [
            {"attributes": [
                {"key": "max", "stringValue": "24"},
                {"key": "description",
                 "stringValue": "Number of pipeline runs"},
                {"key": "type", "stringValue": "Integer"}],
             "id": "myOccurrenceNumber"},
            {"attributes": [
                {"key": "max", "stringValue": "3"},
                {"key": "description", "stringValue": "number of retires"},
                {"key": "type", "stringValue": "Integer"}],
             "id": "myMaximumRetries"}],
            "parameterValues": [
                {"id": "myOccurrenceNumber", "stringValue": "4"},
                {"id": "myMaximumRetries", "stringValue": "2"},
                {"id": "myMaximumRetries", "stringValue": "3"}],
            "pipelineObjects": [
                {"fields": [
                    {"key": "startDateTime",
                        "stringValue": "2011-01-01T00:00:00"},
                    {"key": "occurrences",
                        "stringValue": "#{myOccurrenceNumber}"},
                    {"key": "period",
                        "stringValue": "1 YEAR"},
                    {"key": "type",
                        "stringValue": "Schedule"}],
                    "id": "CopyPeriod",
                    "name": "CopyPeriod"},
                {"fields": [
                    {"key": "schedule", "refValue": "CopyPeriod"},
                    {"key": "retryDelay", "stringValue": "1 MINUTE"},
                    {"key": "command", "stringValue": "false"},
                    {"key": "maximumRetries",
                        "stringValue": "#{myMaximumRetries}"},
                    {"key": "workerGroup", "stringValue": "$PIPELINE_ID"},
                    {"key": "type", "stringValue": "ShellCommandActivity"}],
                    "id": "ShellCommand",
                    "name": "ShellCommand"}]}
        expected = {"parameters": [
            {
                "max": "24",
                "type": "Integer",
                "id": "myOccurrenceNumber",
                "description": "Number of pipeline runs"},
            {
                "max": "3",
                "type": "Integer",
                "id": "myMaximumRetries",
                "description": "number of retires"}
        ], "objects": [
            {
                "name": "CopyPeriod",
                "period": "1 YEAR",
                "occurrences": "#{myOccurrenceNumber}",
                "startDateTime": "2011-01-01T00:00:00",
                "type": "Schedule",
                "id": "CopyPeriod"
            }, {
                "name": "ShellCommand",
                "schedule": {"ref": "CopyPeriod"},
                "retryDelay": "1 MINUTE",
                "workerGroup": "$PIPELINE_ID",
                "command": "false",
                "type": "ShellCommandActivity",
                "id": "ShellCommand",
                "maximumRetries": "#{myMaximumRetries}"
            }
        ], "values":
            {
                "myMaximumRetries": ["2", "3"],
                "myOccurrenceNumber": "4"
            }
        }
        actual = translator.api_to_definition(api)
        self.assertEqual(expected, actual)
