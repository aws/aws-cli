# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.autocomplete.serverside import servercomp


def add_log_completers(custom_completers):
    custom_completers.append(GroupNameCompleter())


class GroupNameCompleter(servercomp.BaseCustomServerSideCompleter):
    _PARAM_NAME = 'group_name'
    _LINEAGE = ['aws', 'logs']
    _COMMAND_NAMES = ['tail']

    def _get_remote_results(self, parsed):
        client = self._client_creator.create_client('logs')
        response = self._invoke_api(client, 'describe_log_groups', {})
        return [
            group['logGroupName'] for group in response.get('logGroups', [])
        ]
