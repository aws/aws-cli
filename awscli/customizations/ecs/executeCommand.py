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
import logging
import json
import errno

from subprocess import check_call
from awscli.compat import ignore_user_entered_signals
from awscli.clidriver import ServiceOperation, CLIOperationCaller

logger = logging.getLogger(__name__)

ERROR_MESSAGE = (
    'SessionManagerPlugin is not found. ',
    'Please refer to SessionManager Documentation here: ',
    'http://docs.aws.amazon.com/console/systems-manager/',
    'session-manager-plugin-not-found'
)


class EcsExecuteCommand(ServiceOperation):

    def create_help_command(self):
        help_command = super(EcsExecuteCommand, self).create_help_command()
        # change the output shape because the command provides no output.
        self._operation_model.output_shape = None
        return help_command


class ExecuteCommandCaller(CLIOperationCaller):
    def invoke(self, service_name, operation_name, parameters, parsed_globals):
        try:
            # making an execute-command call to connect to an active session on a container would require
            # session-manager-plugin to be installed on the client machine.
            # Hence, making this empty session-manager-plugin call before calling execute-command
            # to ensure that session-manager-plugin is installed before execute-command-command is made
            check_call(["session-manager-plugin"])
            client = self._session.create_client(
                service_name, region_name=parsed_globals.region,
                endpoint_url=parsed_globals.endpoint_url,
                verify=parsed_globals.verify_ssl)
            response = client.execute_command(**parameters)
            region_name = client.meta.region_name
            # ignore_user_entered_signals ignores these signals
            # because if signals which kills the process are not
            # captured would kill the foreground process but not the
            # background one. Capturing these would prevents process
            # from getting killed and these signals are input to plugin
            # and handling in there
            with ignore_user_entered_signals():
                # call executable with necessary input
                check_call(["session-manager-plugin",
                            json.dumps(response['session']),
                            region_name,
                            "StartSession"])
            return 0
        except OSError as ex:
            if ex.errno == errno.ENOENT:
                logger.debug('SessionManagerPlugin is not present',
                             exc_info=True)
                raise ValueError(''.join(ERROR_MESSAGE))
