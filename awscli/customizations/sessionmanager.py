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


def register_ssm_session(event_handlers):
    event_handlers.register('building-command-table.ssm',
                            add_custom_start_session)


def add_custom_start_session(session, command_table, **kwargs):
    command_table['start-session'] = StartSessionCommand(
        name='start-session',
        parent_name='ssm',
        session=session,
        operation_model=session.get_service_model(
            'ssm').operation_model('StartSession'),
        operation_caller=StartSessionCaller(session),
    )


class StartSessionCommand(ServiceOperation):

    def create_help_command(self):
        help_command = super(
            StartSessionCommand, self).create_help_command()
        # Change the output shape because the command provides no output.
        self._operation_model.output_shape = None
        return help_command


class StartSessionCaller(CLIOperationCaller):
    def invoke(self, service_name, operation_name, parameters,
               parsed_globals):
        client = self._session.create_client(
            service_name, region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl)
        response = client.start_session(**parameters)
        session_id = response['SessionId']
        region_name = client.meta.region_name

        try:
            # ignore_user_entered_signals ignores these signals
            # because if signals which kills the process are not
            # captured would kill the foreground process but not the
            # background one. Capturing these would prevents process
            # from getting killed and these signals are input to plugin
            # and handling in there
            with ignore_user_entered_signals():
                # call executable with necessary input
                check_call(["session-manager-plugin",
                            json.dumps(response),
                            region_name,
                            "StartSession"])
            return 0
        except OSError as ex:
            if ex.errno == errno.ENOENT:
                logger.debug('SessionManagerPlugin is not present',
                             exc_info=True)
                # start-session api call returns response and starts the
                # session on ssm-agent and response is forwarded to
                # session-manager-plugin. If plugin is not present, terminate
                # is called so that service and ssm-agent terminates the
                # session to avoid zombie session active on ssm-agent for
                # default self terminate time
                client.terminate_session(SessionId=session_id)
                raise ValueError(''.join(ERROR_MESSAGE))
