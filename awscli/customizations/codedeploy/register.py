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

import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.codedeploy.systems import DEFAULT_CONFIG_FILE
from awscli.customizations.codedeploy.utils import \
    validate_region, validate_instance_name, validate_tags, \
    validate_iam_user_arn, INSTANCE_NAME_ARG, IAM_USER_ARN_ARG


class Register(BasicCommand):
    NAME = 'register'

    DESCRIPTION = (
        "Creates an IAM user for the on-premises instance, if not provided, "
        "and saves the user's credentials to an on-premises instance "
        "configuration file; registers the on-premises instance with AWS "
        "CodeDeploy; and optionally adds tags to the on-premises instance."
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
        IAM_USER_ARN_ARG
    ]

    def _run_main(self, parsed_args, parsed_globals):
        params = parsed_args
        params.session = self._session
        validate_region(params, parsed_globals)
        validate_instance_name(params)
        validate_tags(params)
        validate_iam_user_arn(params)

        self.codedeploy = self._session.create_client(
            'codedeploy',
            region_name=params.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl
        )
        self.iam = self._session.create_client(
            'iam',
            region_name=params.region
        )

        try:
            if not params.iam_user_arn:
                self._create_iam_user(params)
                self._create_access_key(params)
                self._create_user_policy(params)
                self._create_config(params)
            self._register_instance(params)
            if params.tags:
                self._add_tags(params)
            sys.stdout.write(
                'Copy the on-premises configuration file named {0} to the '
                'on-premises instance, and run the following command on the '
                'on-premises instance to install and configure the AWS '
                'CodeDeploy Agent:\n'
                'aws deploy install --config-file {0}\n'.format(
                    DEFAULT_CONFIG_FILE
                )
            )
        except Exception as e:
            sys.stdout.flush()
            sys.stderr.write(
                'ERROR\n'
                '{0}\n'
                'Register the on-premises instance by following the '
                'instructions in "Configure Existing On-Premises Instances by '
                'Using AWS CodeDeploy" in the AWS CodeDeploy User '
                'Guide.\n'.format(e)
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

    def _create_config(self, params):
        sys.stdout.write(
            'Creating the on-premises instance configuration file named {0}'
            '...'.format(DEFAULT_CONFIG_FILE)
        )
        with open(DEFAULT_CONFIG_FILE, 'w') as f:
            f.write(
                '---\n'
                'region: {0}\n'
                'iam_user_arn: {1}\n'
                'aws_access_key_id: {2}\n'
                'aws_secret_access_key: {3}\n'.format(
                    params.region,
                    params.iam_user_arn,
                    params.access_key_id,
                    params.secret_access_key
                )
            )
        sys.stdout.write('DONE\n')

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
