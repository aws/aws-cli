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
from awscli.clidriver import create_clidriver
from awscli.arguments import CLIArgument
from awscli.testutils import unittest
from awscli.customizations.configservice.putconfigurationrecorder import \
    extract_recording_group, ConfigurationRecorderArgument, \
    RecordingGroupArgument


class TestPutConfigurationRecorder(unittest.TestCase):
    def setUp(self):
        self.clidriver = create_clidriver()
        self.session = self.clidriver.session
        self.argument_table = {}
        self.service_model = self.session.get_service_model('config')
        self.operation_model = self.service_model.operation_model(
            'PutConfigurationRecorder')
        configuration_recorder_model = self.operation_model.\
            input_shape.members['ConfigurationRecorder']
        self.old_configuration_recorder_argument = CLIArgument(
            name='configuration-recorder',
            argument_model=configuration_recorder_model,
            operation_model=self.operation_model,
            is_required=True,
            event_emitter=self.session.get_component('event_emitter'),
            serialized_name='ConfigurationRecorder'
        )
        self.argument_table['configuration-recorder'] = \
            self.old_configuration_recorder_argument

    def test_extract_recording_group(self):
        extract_recording_group(self.session, self.argument_table)
        self.assertEqual(len(self.argument_table), 2)

        # Ensure the original argument was replaced with the updated argument.
        self.assertIn('configuration-recorder', self.argument_table)
        new_configuration_recorder_argument = self.argument_table[
            'configuration-recorder']
        self.assertIsNot(
            new_configuration_recorder_argument,
            self.old_configuration_recorder_argument
        )
        self.assertIsInstance(
            new_configuration_recorder_argument,
            ConfigurationRecorderArgument
        )

        # Ensure the recording group member was extracted to an argument
        self.assertIn('recording-group', self.argument_table)
        recording_group_argument = self.argument_table['recording-group']
        self.assertIsInstance(
            recording_group_argument,
            RecordingGroupArgument
        )

    def test_configuration_recorder_when_new_value(self):
        value = '{"name":"myname","roleARN":"myarn"}'
        parameters = {}
        extract_recording_group(self.session, self.argument_table)
        configuration_recorder_argument = self.argument_table[
            'configuration-recorder']
        configuration_recorder_argument.add_to_params(parameters, value)
        self.assertEqual(
            {'ConfigurationRecorder': {
                'name': 'myname',
                'roleARN': 'myarn'}},
            parameters)

    def test_configuration_recorder_when_update_value(self):
        value = '{"name":"myname","roleARN":"myarn"}'
        parameters = {
            'ConfigurationRecorder': {
                'recordingGroup': {
                    'allSupported': True,
                    'resourceTypes': ['AWS::EC2::Volume']
                }
            }
        }
        extract_recording_group(self.session, self.argument_table)
        configuration_recorder_argument = self.argument_table[
            'configuration-recorder']
        configuration_recorder_argument.add_to_params(parameters, value)
        self.assertEqual(
            {'ConfigurationRecorder': {
                'name': 'myname',
                'roleARN': 'myarn',
                'recordingGroup': {
                    'allSupported': True,
                    'resourceTypes': ['AWS::EC2::Volume']}}},
            parameters)

    def test_recording_group_when_new_value(self):
        value = '{"allSupported":true,"resourceTypes":["AWS::EC2::Volume"]}'
        parameters = {}
        extract_recording_group(self.session, self.argument_table)
        recording_group_argument = self.argument_table['recording-group']
        recording_group_argument.add_to_params(parameters, value)
        self.assertEqual(
            {'ConfigurationRecorder': {
                'recordingGroup': {
                    'allSupported': True,
                    'resourceTypes': ['AWS::EC2::Volume']}}},
            parameters)

    def test_recording_group_when_update_value(self):
        value = '{"allSupported":true,"resourceTypes":["AWS::EC2::Volume"]}'
        parameters = {
            'ConfigurationRecorder': {
                'name': 'myname',
                'roleARN': 'myarn',
            }
        }
        extract_recording_group(self.session, self.argument_table)
        recording_group_argument = self.argument_table['recording-group']
        recording_group_argument.add_to_params(parameters, value)
        self.assertEqual(
            {'ConfigurationRecorder': {
                'name': 'myname',
                'roleARN': 'myarn',
                'recordingGroup': {
                    'allSupported': True,
                    'resourceTypes': ['AWS::EC2::Volume']}}},
            parameters)
