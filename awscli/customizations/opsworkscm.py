# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.utils import alias_command


def register_alias_opsworks_cm(event_emitter):
    event_emitter.register('building-command-table.main', alias_opsworks_cm)


def alias_opsworks_cm(command_table, **kwargs):
    alias_command(command_table, 'opsworkscm', 'opsworks-cm')
