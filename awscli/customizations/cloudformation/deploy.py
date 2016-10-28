# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import os
import sys
import logging

from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.deployer import Deployer
from awscli.customizations.cloudformation.yamlhelper import yaml_parse

from awscli.customizations.commands import BasicCommand

LOG = logging.getLogger(__name__)


class DeployCommand(BasicCommand):

    MSG_NO_EXECUTE_CHANGESET = \
        ("Changeset created successfully. Run the following command to "
         "review changes:"
         "\n"
         "aws cloudformation describe-change-set --change-set-name "
         "{changeset_id}"
         "\n")

    MSG_EXECUTE_SUCCESS = "Successfully created/updated stack - {stack_name}\n"

    PARAMETER_OVERRIDE_CMD = "parameter-overrides"

    NAME = 'deploy'
    DESCRIPTION = BasicCommand.FROM_FILE("cloudformation",
                                         "_deploy_description.rst")

    ARG_TABLE = [
        {
            'name': 'template-file',
            'required': True,
            'help_text': (
                'The path where your AWS CloudFormation'
                ' template is located.'
            )
        },
        {
            'name': 'stack-name',
            'action': 'store',
            'required': True,
            'help_text': (
                'The name of the AWS CloudFormation stack you\'re deploying to.'
                ' If you specify an existing stack, the command updates the'
                ' stack. If you specify a new stack, the command creates it.'
            )
        },
        {
            'name': PARAMETER_OVERRIDE_CMD,
            'action': 'store',
            'required': False,
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'string'
                }
            },
            'default': [],
            'help_text': (
                'A list of parameter structures that specify input parameters'
                ' for your stack template. If you\'re updating a stack and you'
                ' don\'t specify a parameter, the command uses the stack\'s'
                ' exisiting value. For new stacks, you must specify'
                ' parameters that don\'t have a default value.'
                ' Syntax: ParameterKey1=ParameterValue1'
                ' ParameterKey2=ParameterValue2 ...'
            )
        },
        {
            'name': 'capabilities',
            'action': 'store',
            'required': False,
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'enum': [
                        'CAPABILITY_IAM',
                        'CAPABILITY_NAMED_IAM'
                    ]
                }
            },
            'default': [],
            'help_text': (
                'A list of capabilities that you must specify before AWS'
                ' Cloudformation can create certain stacks. Some stack'
                ' templates might include resources that can affect'
                ' permissions in your AWS account, for example, by creating'
                ' new AWS Identity and Access Management (IAM) users. For'
                ' those stacks, you must explicitly acknowledge their'
                ' capabilities by specifying this parameter. '
                ' The only valid values are CAPABILITY_IAM and'
                ' CAPABILITY_NAMED_IAM. If you have IAM resources, you can'
                ' specify either capability. If you have IAM resources with'
                ' custom names, you must specify CAPABILITY_NAMED_IAM. If you'
                ' don\'t specify this parameter, this action returns an'
                ' InsufficientCapabilities error.'
            )

        },
        {
            'name': 'no-execute-changeset',
            'action': 'store_false',
            'dest': 'execute_changeset',
            'required': False,
            'help_text': (
                'Indicates whether to execute the change set. Specify this'
                ' flag if you want to view your stack changes before'
                ' executing the change set. The command creates an'
                ' AWS CloudFormation change set and then exits without'
                ' executing the change set. After you view the change set,'
                ' execute it to implement your changes.'
            )
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        cloudformation_client = \
            self._session.create_client(
                    'cloudformation', region_name=parsed_globals.region,
                    endpoint_url=parsed_globals.endpoint_url,
                    verify=parsed_globals.verify_ssl)

        template_path = parsed_args.template_file
        if not os.path.isfile(template_path):
            raise exceptions.InvalidTemplatePathError(
                    template_path=template_path)

        # Parse parameters
        with open(template_path, "r") as handle:
            template_str = handle.read()

        stack_name = parsed_args.stack_name
        parameter_overrides = self.parse_parameter_arg(
                parsed_args.parameter_overrides)

        template_dict = yaml_parse(template_str)

        parameters = self.merge_parameters(template_dict, parameter_overrides)

        deployer = Deployer(cloudformation_client)
        return self.deploy(deployer, stack_name, template_str,
                           parameters, parsed_args.capabilities,
                           parsed_args.execute_changeset)

    def deploy(self, deployer, stack_name, template_str,
               parameters, capabilities, execute_changeset):
        result = deployer.create_and_wait_for_changeset(
                stack_name=stack_name,
                cfn_template=template_str,
                parameter_values=parameters,
                capabilities=capabilities)

        if execute_changeset:
            deployer.execute_changeset(result.changeset_id, stack_name)
            deployer.wait_for_execute(stack_name, result.changeset_type)
            sys.stdout.write(self.MSG_EXECUTE_SUCCESS.format(
                    stack_name=stack_name))
        else:
            sys.stdout.write(self.MSG_NO_EXECUTE_CHANGESET.format(
                    changeset_id=result.changeset_id))

        sys.stdout.flush()
        return 0

    def merge_parameters(self, template_dict, parameter_overrides):
        """
        CloudFormation CreateChangeset requires a value for every parameter
        from the template, either specifying a new value or use previous value.
        For convenience, this method will accept new parameter values and
        generates a dict of all parameters in a format that ChangeSet API
        will accept

        :param parameter_overrides:
        :return:
        """
        parameter_values = []

        if not isinstance(template_dict.get("Parameters", None), dict):
            return parameter_values

        for key, value in template_dict["Parameters"].items():

            obj = {
                "ParameterKey": key
            }

            if key in parameter_overrides:
                obj["ParameterValue"] = parameter_overrides[key]
            else:
                obj["UsePreviousValue"] = True

            parameter_values.append(obj)

        return parameter_values

    def parse_parameter_arg(self, parameter_arg):
        result = {}
        for data in parameter_arg:

            # Split at first '=' from left
            key_value_pair = data.split("=", 1)

            if len(key_value_pair) != 2:
                raise exceptions.InvalidParameterOverrideArgumentError(
                        argname=self.PARAMETER_OVERRIDE_CMD,
                        value=key_value_pair)

            result[key_value_pair[0]] = key_value_pair[1]

        return result
