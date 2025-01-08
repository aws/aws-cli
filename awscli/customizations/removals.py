# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""
Remove deprecated commands
--------------------------

This customization removes commands that are either deprecated or not
yet fully supported.

"""
import logging
from functools import partial

LOG = logging.getLogger(__name__)


def register_removals(event_handler):
    cmd_remover = CommandRemover(event_handler)
    cmd_remover.remove(on_event='building-command-table.ses',
                       remove_commands=['delete-verified-email-address',
                                        'list-verified-email-addresses',
                                        'verify-email-address'])
    cmd_remover.remove(on_event='building-command-table.ec2',
                       remove_commands=['import-instance', 'import-volume'])
    cmd_remover.remove(on_event='building-command-table.emr',
                       remove_commands=['run-job-flow', 'describe-job-flows',
                                        'add-job-flow-steps',
                                        'terminate-job-flows',
                                        'list-bootstrap-actions',
                                        'list-instance-groups',
                                        'set-termination-protection',
                                        'set-keep-job-flow-alive-when-no-steps',
                                        'set-visible-to-all-users',
                                        'set-unhealthy-node-replacement'])
    cmd_remover.remove(on_event='building-command-table.kinesis',
                       remove_commands=['subscribe-to-shard'])
    cmd_remover.remove(on_event='building-command-table.lexv2-runtime',
                         remove_commands=['start-conversation'])
    cmd_remover.remove(on_event='building-command-table.lambda',
                         remove_commands=['invoke-with-response-stream'])
    cmd_remover.remove(on_event='building-command-table.sagemaker-runtime',
                         remove_commands=['invoke-endpoint-with-response-stream'])
    cmd_remover.remove(on_event='building-command-table.bedrock-runtime',
                         remove_commands=['invoke-model-with-response-stream',
                                          'converse-stream'])
    cmd_remover.remove(on_event='building-command-table.bedrock-agent-runtime',
                         remove_commands=['invoke-agent',
                                          'invoke-flow',
                                          'invoke-inline-agent',
                                          'optimize-prompt',
                                          'retrieve-and-generate-stream'])
    cmd_remover.remove(on_event='building-command-table.qbusiness',
                        remove_commands=['chat'])
    cmd_remover.remove(on_event='building-command-table.iotsitewise',
                        remove_commands=['invoke-assistant'])


class CommandRemover(object):
    def __init__(self, events):
        self._events = events

    def remove(self, on_event, remove_commands):
        self._events.register(on_event,
                              self._create_remover(remove_commands))

    def _create_remover(self, commands_to_remove):
        return partial(_remove_commands, commands_to_remove=commands_to_remove)


def _remove_commands(command_table, commands_to_remove, **kwargs):
    # Hooked up to building-command-table.<service>
    for command in commands_to_remove:
        try:
            LOG.debug("Removing operation: %s", command)
            del command_table[command]
        except KeyError:
            LOG.warning("Attempting to delete command that does not exist: %s",
                        command)
