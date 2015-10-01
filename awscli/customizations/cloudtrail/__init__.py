# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from .subscribe import CloudTrailSubscribe, CloudTrailUpdate
from .validation import CloudTrailValidateLogs


def initialize(cli):
    """
    The entry point for CloudTrail high level commands.
    """
    cli.register('building-command-table.cloudtrail', inject_commands)


def inject_commands(command_table, session, **kwargs):
    """
    Called when the CloudTrail command table is being built. Used to inject new
    high level commands into the command list. These high level commands
    must not collide with existing low-level API call names.
    """
    command_table['create-subscription'] = CloudTrailSubscribe(session)
    command_table['update-subscription'] = CloudTrailUpdate(session)
    command_table['validate-logs'] = CloudTrailValidateLogs(session)
