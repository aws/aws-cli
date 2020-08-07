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

import functools
import json
import os
import sys
import logging

from botocore.client import Config

from awscli.compat import compat_open
from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.deployer import Deployer
from awscli.customizations.s3uploader import S3Uploader
from awscli.customizations.cloudformation.yamlhelper import yaml_parse

from awscli.customizations.commands import BasicCommand
from awscli.compat import get_stdout_text_writer
from awscli.utils import write_exception

LOG = logging.getLogger(__name__)


class BaseParameterOverrideParser:
    def can_parse(self, data):
        # Returns true/false if it can parse
        raise NotImplementedError('can_parse')

    def parse(self, data):
        # Return the properly formatted parameter dictionary
        raise NotImplementedError('parse')


class CodePipelineLikeParameterOverrideParser(BaseParameterOverrideParser):
    def can_parse(self, data):
        return isinstance(data, dict) and 'Parameters' in data

    def parse(self, data):
        # Parse parameter_overrides if they were given in
        # CodePipeline params file format
        # {
        #     "Parameters": {
        #         "ParameterKey": "ParameterValue"
        #     }
        # }
        return data['Parameters']


class CloudFormationLikeParameterOverrideParser(BaseParameterOverrideParser):
    def can_parse(self, data):
        for param_pair in data:
            if ('ParameterKey' not in param_pair or
                    'ParameterValue' not in param_pair):
                return False
            if len(param_pair.keys()) > 2:
                return False
        return True

    def parse(self, data):
        # Parse parameter_overrides if they were given in
        # CloudFormation params file format
        # [{
        #   "ParameterKey": "string",
        #   "ParameterValue": "string",
        # }]
        return {
            param['ParameterKey']: param['ParameterValue']
            for param in data
        }


class StringEqualsParameterOverrideParser(BaseParameterOverrideParser):
    def can_parse(self, data):
        return all(
            isinstance(param, str) and len(param.split("=", 1)) == 2
            for param in data
        )

    def parse(self, data):
        result = {}
        for param in data:
            # Split at first '=' from left
            key_value_pair = param.split("=", 1)
            result[key_value_pair[0]] = key_value_pair[1]
        return result


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
    TAGS_CMD = "tags"

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
            'name': 's3-bucket',
            'required': False,
            'help_text': (
                'The name of the S3 bucket where this command uploads your '
                'CloudFormation template. This is required the deployments of '
                'templates sized greater than 51,200 bytes'
            )
        },
        {
            "name": "force-upload",
            "action": "store_true",
            "help_text": (
                'Indicates whether to override existing files in the S3 bucket.'
                ' Specify this flag to upload artifacts even if they '
                ' match existing artifacts in the S3 bucket.'
            )
        },
        {
            'name': 's3-prefix',
            'help_text': (
                'A prefix name that the command adds to the'
                ' artifacts\' name when it uploads them to the S3 bucket.'
                ' The prefix name is a path name (folder name) for'
                ' the S3 bucket.'
            )
        },

        {
            'name': 'kms-key-id',
            'help_text': (
                'The ID of an AWS KMS key that the command uses'
                ' to encrypt artifacts that are at rest in the S3 bucket.'
            )
        },
        {
            'name': PARAMETER_OVERRIDE_CMD,
            'action': 'store',
            'required': False,
            'nargs': '+',
            'default': [],
            'help_text': (
                'A list of parameter structures that specify input parameters'
                ' for your stack template. If you\'re updating a stack and you'
                ' don\'t specify a parameter, the command uses the stack\'s'
                ' existing value. For new stacks, you must specify'
                ' parameters that don\'t have a default value.'
                ' Syntax: ParameterKey1=ParameterValue1'
                ' ParameterKey2=ParameterValue2 ... or JSON file (see Examples)'
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
        },
        {
            'name': 'role-arn',
            'required': False,
            'help_text': (
                'The Amazon Resource Name (ARN) of an AWS Identity and Access '
                'Management (IAM) role that AWS CloudFormation assumes when '
                'executing the change set.'
            )
        },
        {
            'name': 'notification-arns',
            'required': False,
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'string'
                }
            },
            'help_text': (
                'Amazon Simple Notification Service topic Amazon Resource Names'
                ' (ARNs) that AWS CloudFormation associates with the stack.'
            )
        },
        {
            'name': 'fail-on-empty-changeset',
            'required': False,
            'action': 'store_true',
            'group_name': 'fail-on-empty-changeset',
            'dest': 'fail_on_empty_changeset',
            'default': False,
            'help_text': (
                'Specify if the CLI should return a non-zero exit code if '
                'there are no changes to be made to the stack. The default '
                'behavior is to return a zero exit code.'
            )
        },
        {
            'name': 'no-fail-on-empty-changeset',
            'required': False,
            'action': 'store_false',
            'group_name': 'fail-on-empty-changeset',
            'dest': 'fail_on_empty_changeset',
            'default': False,
            'help_text': (
                'Causes the CLI to return an exit code of 0 if there are no '
                'changes to be made to the stack.'
            )
        },
        {
            'name': TAGS_CMD,
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
                'A list of tags to associate with the stack that is created'
                ' or updated. AWS CloudFormation also propagates these tags'
                ' to resources in the stack if the resource supports it.'
                ' Syntax: TagKey1=TagValue1 TagKey2=TagValue2 ...'
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
        with compat_open(template_path, "r") as handle:
            template_str = handle.read()

        stack_name = parsed_args.stack_name
        parameter_overrides = self.parse_parameter_overrides(
            parsed_args.parameter_overrides
        )
        tags_dict = self.parse_key_value_arg(parsed_args.tags, self.TAGS_CMD)
        tags = [{"Key": key, "Value": value}
                for key, value in tags_dict.items()]

        template_dict = yaml_parse(template_str)

        parameters = self.merge_parameters(template_dict, parameter_overrides)

        template_size = os.path.getsize(parsed_args.template_file)
        if template_size > 51200 and not parsed_args.s3_bucket:
            raise exceptions.DeployBucketRequiredError()

        bucket = parsed_args.s3_bucket
        if bucket:
            s3_client = self._session.create_client(
                "s3",
                config=Config(signature_version='s3v4'),
                region_name=parsed_globals.region,
                verify=parsed_globals.verify_ssl)

            s3_uploader = S3Uploader(s3_client,
                                      bucket,
                                      parsed_args.s3_prefix,
                                      parsed_args.kms_key_id,
                                      parsed_args.force_upload)
        else:
            s3_uploader = None

        deployer = Deployer(cloudformation_client)
        return self.deploy(deployer, stack_name, template_str,
                           parameters, parsed_args.capabilities,
                           parsed_args.execute_changeset, parsed_args.role_arn,
                           parsed_args.notification_arns, s3_uploader,
                           tags,
                           parsed_args.fail_on_empty_changeset)

    def deploy(self, deployer, stack_name, template_str,
               parameters, capabilities, execute_changeset, role_arn,
               notification_arns, s3_uploader, tags,
               fail_on_empty_changeset=False):
        try:
            result = deployer.create_and_wait_for_changeset(
                stack_name=stack_name,
                cfn_template=template_str,
                parameter_values=parameters,
                capabilities=capabilities,
                role_arn=role_arn,
                notification_arns=notification_arns,
                s3_uploader=s3_uploader,
                tags=tags
            )
        except exceptions.ChangeEmptyError as ex:
            if fail_on_empty_changeset:
                raise
            write_exception(ex, outfile=get_stdout_text_writer())
            return 0

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

    def _parse_input_as_json(self, arg_value):
        # In case of reading from file it'll be string and in case
        # of inline json input it'll be list where json string
        # will be the first element
        if arg_value:
            if isinstance(arg_value, str):
                return json.loads(arg_value)
            try:
                return json.loads(arg_value[0])
            except json.JSONDecodeError:
                return None

    def parse_parameter_overrides(self, arg_value):
        data = self._parse_input_as_json(arg_value)
        if data is not None:
            parsers = [
                CloudFormationLikeParameterOverrideParser(),
                CodePipelineLikeParameterOverrideParser(),
                StringEqualsParameterOverrideParser()
            ]
            for parser in parsers:
                if parser.can_parse(data):
                    return parser.parse(data)
            raise ParamValidationError(
                'JSON passed to --parameter-overrides must be one of '
                'the formats: ["Key1=Value1","Key2=Value2", ...] , '
                '[{"ParameterKey": "Key1", "ParameterValue": "Value1"}, ...] , '
                '["Parameters": {"Key1": "Value1", "Key2": "Value2", ...}]')
        else:
            # In case it was in deploy command format
            # and was input via command line
            return self.parse_key_value_arg(
                arg_value,
                self.PARAMETER_OVERRIDE_CMD
            )

    def parse_key_value_arg(self, arg_value, argname):
        """
        Converts arguments that are passed as list of "Key=Value" strings
        into a real dictionary.

        :param arg_value list: Array of strings, where each string is of
            form Key=Value
        :param argname string: Name of the argument that contains the value
        :return dict: Dictionary representing the key/value pairs
        """
        result = {}
        for data in arg_value:

            # Split at first '=' from left
            key_value_pair = data.split("=", 1)

            if len(key_value_pair) != 2:
                raise exceptions.InvalidKeyValuePairArgumentError(
                        argname=argname,
                        value=key_value_pair)

            result[key_value_pair[0]] = key_value_pair[1]

        return result
