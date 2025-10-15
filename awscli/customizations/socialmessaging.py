# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.utils import make_hidden_command_alias


def register_alias_socialmessaging_command(event_emitter):
    event_emitter.register(
        'building-command-table.socialmessaging',
        alias_socialmessaging_command
    )


def alias_socialmessaging_command(command_table, **kwargs):
    make_hidden_command_alias(
        command_table,
        existing_name='delete-whatsapp-message-media',
        alias_name='delete-whatsapp-media-message',
    )
