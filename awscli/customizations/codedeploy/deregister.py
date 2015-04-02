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

import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.codedeploy.utils import \
    validate_region, validate_instance_name, INSTANCE_NAME_ARG
from awscli.errorhandler import ClientError, ServerError


class Deregister(BasicCommand):
    NAME = 'deregister'

    DESCRIPTION = (
        'Removes any tags from the on-premises instance; deregisters the '
        'on-premises instance from AWS CodeDeploy; and, unless requested '
        'otherwise, deletes the IAM user for the on-premises instance.'
    )

    ARG_TABLE = [
        INSTANCE_NAME_ARG,
        {
            'name': 'no-delete-iam-user',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Optional. Do not delete the IAM user for the registered '
                'on-premises instance.'
            )
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        params = parsed_args
        params.session = self._session
        validate_region(params, parsed_globals)
        validate_instance_name(params)

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
            self._get_instance_info(params)
            if params.tags:
                self._remove_tags(params)
            self._deregister_instance(params)
            if not params.no_delete_iam_user:
                self._delete_user_policy(params)
                self._delete_access_key(params)
                self._delete_iam_user(params)
            sys.stdout.write(
                'Run the following command on the on-premises instance to '
                'uninstall the codedeploy-agent:\n'
                'aws deploy uninstall\n'
            )
        except Exception as e:
            sys.stdout.flush()
            sys.stderr.write(
                'ERROR\n'
                '{0}\n'
                'Deregister the on-premises instance by following the '
                'instructions in "Configure Existing On-Premises Instances by '
                'Using AWS CodeDeploy" in the AWS CodeDeploy User '
                'Guide.\n'.format(e)
            )

    def _get_instance_info(self, params):
        sys.stdout.write('Retrieving on-premises instance information... ')
        response = self.codedeploy.get_on_premises_instance(
            instanceName=params.instance_name
        )
        params.iam_user_arn = response['instanceInfo']['iamUserArn']
        start = params.iam_user_arn.rfind('/') + 1
        params.user_name = params.iam_user_arn[start:]
        params.tags = response['instanceInfo']['tags']
        sys.stdout.write(
            'DONE\n'
            'IamUserArn: {0}\n'.format(
                params.iam_user_arn
            )
        )
        if params.tags:
            sys.stdout.write('Tags:')
            for tag in params.tags:
                sys.stdout.write(
                    ' Key={0},Value={1}'.format(tag['Key'], tag['Value'])
                )
            sys.stdout.write('\n')

    def _remove_tags(self, params):
        sys.stdout.write('Removing tags from the on-premises instance... ')
        self.codedeploy.remove_tags_from_on_premises_instances(
            tags=params.tags,
            instanceNames=[params.instance_name]
        )
        sys.stdout.write('DONE\n')

    def _deregister_instance(self, params):
        sys.stdout.write('Deregistering the on-premises instance... ')
        self.codedeploy.deregister_on_premises_instance(
            instanceName=params.instance_name
        )
        sys.stdout.write('DONE\n')

    def _delete_user_policy(self, params):
        sys.stdout.write('Deleting the IAM user policies... ')
        list_user_policies = self.iam.get_paginator('list_user_policies')
        try:
            for response in list_user_policies.paginate(
                    UserName=params.user_name):
                for policy_name in response['PolicyNames']:
                    self.iam.delete_user_policy(
                        UserName=params.user_name,
                        PolicyName=policy_name
                    )
        except (ServerError, ClientError) as e:
            if e.error_code != 'NoSuchEntity':
                raise e
        sys.stdout.write('DONE\n')

    def _delete_access_key(self, params):
        sys.stdout.write('Deleting the IAM user access keys... ')
        list_access_keys = self.iam.get_paginator('list_access_keys')
        try:
            for response in list_access_keys.paginate(
                    UserName=params.user_name):
                for access_key in response['AccessKeyMetadata']:
                    self.iam.delete_access_key(
                        UserName=params.user_name,
                        AccessKeyId=access_key['AccessKeyId']
                    )
        except (ServerError, ClientError) as e:
            if e.error_code != 'NoSuchEntity':
                raise e
        sys.stdout.write('DONE\n')

    def _delete_iam_user(self, params):
        sys.stdout.write('Deleting the IAM user ({0})... '.format(
            params.user_name
        ))
        try:
            self.iam.delete_user(UserName=params.user_name)
        except (ServerError, ClientError) as e:
            if e.error_code != 'NoSuchEntity':
                raise e
        sys.stdout.write('DONE\n')
