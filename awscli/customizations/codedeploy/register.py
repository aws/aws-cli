# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import re
import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.codedeploy.utils import \
    validate_region, validate_instance_name, create_config_file, config_file, \
    validate_iam_user_arn, INSTANCE_NAME_ARG, REGION_ARG, IAM_USER_ARN_ARG


MAX_TAGS_PER_INSTANCE = 10
MAX_TAG_KEY_LENGTH = 128
MAX_TAG_VALUE_LENGTH = 256


class Register(BasicCommand):
    NAME = 'register'

    DESCRIPTION = (
        'The AWS CodeDeploy register command creates an IAM user for the '
        'on-premises instance, if not provided; registers the on-premises '
        'instance with AWS CodeDeploy; and optionally, adds tags to the '
        'on-premises instance.'
    )

    TAGS_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "Key": {
                    "description": "The tag key.",
                    "type": "string",
                    "required": True
                },
                "Value": {
                    "description": "The tag value.",
                    "type": "string",
                    "required": True
                }
            }
        }
    }

    ARG_TABLE = [
        INSTANCE_NAME_ARG,
        {
            'name': 'tags',
            'synopsis': '--tags <value>',
            'required': False,
            'nargs': '+',
            'schema': TAGS_SCHEMA,
            'help_text': (
                'Optional. The list of key/value pairs to tag the on-premises '
                'instance.'
            )
        },
        IAM_USER_ARN_ARG,
        REGION_ARG,
        {
            'name': 'create-config',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Optional. Specify --create-config flag to create the '
                'on-premises config file.'
            )
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        parsed_args.region = validate_region(parsed_globals, self._session)
        validate_instance_name(parsed_args)
        self._validate_tags(parsed_args)
        validate_iam_user_arn(parsed_args)
        params = parsed_args

        self.codedeploy = self._session.create_client(
            'codedeploy',
            region_name=parsed_args.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl
        )
        self.iam = self._session.create_client(
            'iam',
            region_name=parsed_args.region
        )

        try:
            if not params.iam_user_arn:
                self._create_iam_user(params)
                self._create_access_key(params)
                self._create_user_policy(params)
            self._register_instance(params)
            if params.tags:
                self._add_tags(params)
            if params.create_config:
                self._create_config(params)
                sys.stdout.write(
                    'Please copy the {0} config file to the on-premises '
                    'instance; and execute the following command on the '
                    'on-premises instance to configure and install the '
                    'codedeploy-agent:\n'
                    'aws deploy install --config-file {0}\n'.format(
                        config_file()
                    )
                )
            else:
                sys.stdout.write(
                    'Please note the AccessKeyId and SecretAccessKey; and '
                    'execute the following command on the on-premises '
                    'instance to configure and install the codedeploy-agent:\n'
                    'aws deploy install'
                    ' --iam-user-arn {0}'
                    ' --region {1}\n'.format(
                        params.iam_user_arn,
                        params.region
                    )
                )
        except Exception as e:
            sys.stdout.write(
                'ERROR\n'
                '{0}\n'
                'Please manually register the on-premises instance by '
                'following the instructions at {1}\n'.format(
                    e,
                    'http://docs.aws.amazon.com/codedeploy/latest/userguide/how-to-configure-on-premises-host.html'
                )
            )

    @staticmethod
    def _validate_tags(parsed_args):
        if parsed_args.tags:
            if len(parsed_args.tags) > MAX_TAGS_PER_INSTANCE:
                raise RuntimeError(
                    'Instances can only have a maximum of {0} tags.'.format(
                        MAX_TAGS_PER_INSTANCE
                    )
                )
            for tag in parsed_args.tags:
                if len(tag['Key']) > MAX_TAG_KEY_LENGTH:
                    raise RuntimeError(
                        'Tag Key cannot be longer than {0} characters.'.format(
                            MAX_TAG_KEY_LENGTH
                        )
                    )
                if len(tag['Value']) > MAX_TAG_KEY_LENGTH:
                    raise RuntimeError(
                        'Tag Value cannot be longer than {0} '
                        'characters.'.format(
                            MAX_TAG_VALUE_LENGTH
                        )
                    )

    def _create_iam_user(self, params):
        sys.stdout.write('Creating the IAM user... ')
        params.user_name = params.instance_name
        response = self.iam.create_user(
            Path='/AWS/CodeDeploy/',
            UserName=params.user_name
        )
        params.iam_user_arn = response['User']['Arn']
        sys.stdout.write(
            'DONE\n'
            'IamUserArn: {0}\n'.format(
                params.iam_user_arn
            )
        )

    def _create_access_key(self, params):
        sys.stdout.write('Creating the IAM user access key... ')
        response = self.iam.create_access_key(
            UserName=params.user_name
        )
        params.access_key_id = response['AccessKey']['AccessKeyId']
        params.secret_access_key = response['AccessKey']['SecretAccessKey']
        sys.stdout.write(
            'DONE\n'
            'AccessKeyId: {0}\n'
            'SecretAccessKey: {1}\n'.format(
                params.access_key_id,
                params.secret_access_key
            )
        )

    def _create_user_policy(self, params):
        sys.stdout.write('Creating the IAM user policy... ')
        params.policy_name = 'codedeploy-agent'
        params.policy_document = (
            '{\n'
            '    "Version": "2012-10-17",\n'
            '    "Statement": [ {\n'
            '        "Action": [ "s3:Get*", "s3:List*" ],\n'
            '        "Effect": "Allow",\n'
            '        "Resource": "*"\n'
            '    } ]\n'
            '}'
        )
        self.iam.put_user_policy(
            UserName=params.user_name,
            PolicyName=params.policy_name,
            PolicyDocument=params.policy_document
        )
        sys.stdout.write(
            'DONE\n'
            'PolicyName: {0}\n'
            'PolicyDocument: {1}\n'.format(
                params.policy_name,
                params.policy_document
            )
        )

    def _register_instance(self, params):
        sys.stdout.write('Registering the on-premises instance... ')
        self.codedeploy.register_on_premises_instance(
            instanceName=params.instance_name,
            iamUserArn=params.iam_user_arn
        )
        sys.stdout.write('DONE\n')

    def _add_tags(self, params):
        sys.stdout.write('Adding tags to the on-premises instance... ')
        self.codedeploy.add_tags_to_on_premises_instances(
            tags=params.tags,
            instanceNames=[params.instance_name]
        )
        sys.stdout.write('DONE\n')

    @staticmethod
    def _create_config(params):
        sys.stdout.write('Creating {0} config file... '.format(config_file()))
        create_config_file(config_file(), params)
        sys.stdout.write('DONE\n')
