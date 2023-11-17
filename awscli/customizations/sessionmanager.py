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
import os
import re

from subprocess import check_call, check_output
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


class VersionRequirement:
    WHITESPACE_REGEX = re.compile(r"\s+")
    SSM_SESSION_PLUGIN_VERSION_REGEX = re.compile(r"^\d+(\.\d+){0,3}$")

    def __init__(self, min_version):
        self.min_version = min_version

    def meets_requirement(self, version):
        ssm_plugin_version = self._sanitize_plugin_version(version)
        if self._is_valid_version(ssm_plugin_version):
            norm_version, norm_min_version = self._normalize(
                ssm_plugin_version, self.min_version
            )
            return norm_version > norm_min_version
        else:
            return False

    def _sanitize_plugin_version(self, plugin_version):
        return re.sub(self.WHITESPACE_REGEX, "", plugin_version)

    def _is_valid_version(self, plugin_version):
        return bool(
            self.SSM_SESSION_PLUGIN_VERSION_REGEX.match(plugin_version)
        )

    def _normalize(self, v1, v2):
        v1_parts = [int(v) for v in v1.split(".")]
        v2_parts = [int(v) for v in v2.split(".")]
        while len(v1_parts) != len(v2_parts):
            if len(v1_parts) - len(v2_parts) > 0:
                v2_parts.append(0)
            else:
                v1_parts.append(0)
        return v1_parts, v2_parts


class StartSessionCommand(ServiceOperation):
    def create_help_command(self):
        help_command = super(
            StartSessionCommand, self).create_help_command()
        # Change the output shape because the command provides no output.
        self._operation_model.output_shape = None
        return help_command


class StartSessionCaller(CLIOperationCaller):
    LAST_PLUGIN_VERSION_WITHOUT_ENV_VAR = "1.2.497.0"
    DEFAULT_SSM_ENV_NAME = "AWS_SSM_START_SESSION_RESPONSE"

    def invoke(self, service_name, operation_name, parameters,
               parsed_globals):
        client = self._session.create_client(
            service_name, region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl)
        response = client.start_session(**parameters)
        session_id = response['SessionId']
        region_name = client.meta.region_name
        # profile_name is used to passed on to session manager plugin
        # to fetch same profile credentials to make an api call in the plugin.
        # If no profile is passed then pass on empty string
        profile_name = self._session.profile \
            if self._session.profile is not None else ''
        endpoint_url = client.meta.endpoint_url
        ssm_env_name = self.DEFAULT_SSM_ENV_NAME

        try:
            session_parameters = {
                "SessionId": response["SessionId"],
                "TokenValue": response["TokenValue"],
                "StreamUrl": response["StreamUrl"],
            }
            start_session_response = json.dumps(session_parameters)

            plugin_version = check_output(
                ["session-manager-plugin", "--version"], text=True
            )
            env = os.environ.copy()

            # Check if this plugin supports passing the start session response
            # as an environment variable name. If it does, it will set the
            # value to the response from the start_session operation to the env
            # variable defined in DEFAULT_SSM_ENV_NAME. If the session plugin
            # version is invalid or older than the version defined in
            # LAST_PLUGIN_VERSION_WITHOUT_ENV_VAR, it will fall back to
            # passing the start_session response directly.
            version_requirement = VersionRequirement(
                min_version=self.LAST_PLUGIN_VERSION_WITHOUT_ENV_VAR
            )
            if version_requirement.meets_requirement(plugin_version):
                env[ssm_env_name] = start_session_response
                start_session_response = ssm_env_name
            # ignore_user_entered_signals ignores these signals
            # because if signals which kills the process are not
            # captured would kill the foreground process but not the
            # background one. Capturing these would prevents process
            # from getting killed and these signals are input to plugin
            # and handling in there
            with ignore_user_entered_signals():
                # call executable with necessary input
                check_call(["session-manager-plugin",
                            start_session_response,
                            region_name,
                            "StartSession",
                            profile_name,
                            json.dumps(parameters),
                            endpoint_url], env=env)

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
