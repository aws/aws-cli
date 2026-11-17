# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.ec2instanceconnect.opentunnel import (
    OpenTunnelCommand,
)
from awscli.customizations.ec2instanceconnect.ssh import (
    SshCommand,
)


def register_ec2_instance_connect_commands(event_handlers):
    """
    The entry point for EC2 Instance Connect high level commands.
    """
    event_handlers.register(
        "building-command-table.ec2-instance-connect", inject_commands
    )


def inject_commands(command_table, session, **kwargs):
    """
    Called when the EC2 Instance Connect command table is being built.
    Used to inject new high level commands into the command list.
    """
    command_table["open-tunnel"] = OpenTunnelCommand(session)
    command_table["ssh"] = SshCommand(session)
