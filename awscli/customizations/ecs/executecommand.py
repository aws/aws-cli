# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from subprocess import check_call, check_output
from awscli.compat import ignore_user_entered_signals
from awscli.clidriver import ServiceOperation, CLIOperationCaller
from awscli.customizations.sessionmanager import VersionRequirement

logger = logging.getLogger(__name__)

ERROR_MESSAGE = (
    'SessionManagerPlugin is not found. ',
    'Please refer to SessionManager Documentation here: ',
    'http://docs.aws.amazon.com/console/systems-manager/',
    'session-manager-plugin-not-found'
)

TASK_NOT_FOUND = (
    'The task provided in the request was '
    'not found.'
)


class ECSExecuteCommand(ServiceOperation):

    def create_help_command(self):
        help_command = super(ECSExecuteCommand, self).create_help_command()
        # change the output shape because the command provides no output.
        self._operation_model.output_shape = None
        return help_command


def get_container_runtime_id(client, container_name, task_id, cluster_name):
    describe_tasks_params = {
        "cluster": cluster_name,
        "tasks": [task_id]
    }
    describe_tasks_response = client.describe_tasks(**describe_tasks_params)
    # need to fail here if task has failed in the intermediate time
    tasks = describe_tasks_response['tasks']
    if not tasks:
        raise ValueError(TASK_NOT_FOUND)
    response = describe_tasks_response['tasks'][0]['containers']
    for container in response:
        if container_name == container['name']:
            return container['runtimeId']


def build_ssm_request_paramaters(response, client):
    cluster_name = response['clusterArn'].split('/')[-1]
    task_id = response['taskArn'].split('/')[-1]
    container_name = response['containerName']
    # in order to get container run-time id
    # we need to make a call to describe-tasks
    container_runtime_id = \
        get_container_runtime_id(client, container_name,
                                 task_id, cluster_name)
    target = "ecs:{}_{}_{}".format(cluster_name, task_id,
                                   container_runtime_id)
    ssm_request_params = {"Target": target}
    return ssm_request_params


class ExecuteCommandCaller(CLIOperationCaller):
    LAST_PLUGIN_VERSION_WITHOUT_ENV_VAR = "1.2.497.0"
    DEFAULT_SSM_ENV_NAME = "AWS_SSM_START_SESSION_RESPONSE"

    def invoke(self, service_name, operation_name, parameters, parsed_globals):
        try:
            # making an execute-command call to connect to an
            # active session on a container would require
            # session-manager-plugin to be installed on the client machine.
            # Hence, making this empty session-manager-plugin call
            # before calling execute-command to ensure that
            # session-manager-plugin is installed
            # before execute-command-command is made
            plugin_version = check_output(
                ["session-manager-plugin", "--version"], text=True
            )
            client = self._session.create_client(
                service_name, region_name=parsed_globals.region,
                endpoint_url=parsed_globals.endpoint_url,
                verify=parsed_globals.verify_ssl)
            response = client.execute_command(**parameters)
            region_name = client.meta.region_name
            profile_name = self._session.profile \
                if self._session.profile is not None else ''
            endpoint_url = client.meta.endpoint_url
            ssm_request_params = build_ssm_request_paramaters(response, client)
            start_session_response = json.dumps(response['session'])
            ssm_env_name = self.DEFAULT_SSM_ENV_NAME
            env = os.environ.copy()
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
                            json.dumps(ssm_request_params),
                            endpoint_url], env=env)
            return 0
        except OSError as ex:
            if ex.errno == errno.ENOENT:
                logger.debug('SessionManagerPlugin is not present',
                             exc_info=True)
                raise ValueError(''.join(ERROR_MESSAGE))
