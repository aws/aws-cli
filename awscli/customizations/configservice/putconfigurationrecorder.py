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
import copy

from awscli.arguments import CLIArgument


def register_modify_put_configuration_recorder(cli):
    cli.register(
        'building-argument-table.configservice.put-configuration-recorder',
        extract_recording_group)


def extract_recording_group(session, argument_table, **kwargs):
    # The purpose of this customization is to extract the recordingGroup
    # member from ConfigurationRecorder into its own argument.
    # This customization is needed because the recordingGroup member
    # breaks the shorthand syntax as it is a structure and not a scalar value.
    configuration_recorder_argument = argument_table['configuration-recorder']

    configuration_recorder_model = copy.deepcopy(
        configuration_recorder_argument.argument_model)
    recording_group_model = copy.deepcopy(
        configuration_recorder_argument.argument_model.
        members['recordingGroup'])

    del configuration_recorder_model.members['recordingGroup']
    argument_table['configuration-recorder'] = ConfigurationRecorderArgument(
        name='configuration-recorder',
        argument_model=configuration_recorder_model,
        operation_model=configuration_recorder_argument._operation_model,
        is_required=True,
        event_emitter=session.get_component('event_emitter'),
        serialized_name='ConfigurationRecorder'
    )

    argument_table['recording-group'] = RecordingGroupArgument(
        name='recording-group',
        argument_model=recording_group_model,
        operation_model=configuration_recorder_argument._operation_model,
        is_required=False,
        event_emitter=session.get_component('event_emitter'),
        serialized_name='recordingGroup'
    )


class ConfigurationRecorderArgument(CLIArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        unpacked = self._unpack_argument(value)
        if 'ConfigurationRecorder' in parameters:
            current_value = parameters['ConfigurationRecorder']
            current_value.update(unpacked)
        else:
            parameters['ConfigurationRecorder'] = unpacked


class RecordingGroupArgument(CLIArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        unpacked = self._unpack_argument(value)
        if 'ConfigurationRecorder' in parameters:
            parameters['ConfigurationRecorder']['recordingGroup'] = unpacked
        else:
            parameters['ConfigurationRecorder'] = {}
            parameters['ConfigurationRecorder']['recordingGroup'] = unpacked
