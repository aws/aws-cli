# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


def register_sms_voice_hide(event_emitter):
    event_emitter.register('building-command-table.main',
                           hide_sms_voice)


def hide_sms_voice(command_table, session, **kwargs):
    command_table['sms-voice']._UNDOCUMENTED = True
