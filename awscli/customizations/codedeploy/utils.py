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

import platform
import re

import awscli.compat
from awscli.compat import urlopen, URLError
from awscli.customizations.codedeploy.systems import System, Ubuntu, Windows, RHEL
from socket import timeout


MAX_INSTANCE_NAME_LENGTH = 100
MAX_TAGS_PER_INSTANCE = 10
MAX_TAG_KEY_LENGTH = 128
MAX_TAG_VALUE_LENGTH = 256

INSTANCE_NAME_PATTERN = r'^[A-Za-z0-9+=,.@_-]+$'
IAM_USER_ARN_PATTERN = r'^arn:aws:iam::[0-9]{12}:user/[A-Za-z0-9/+=,.@_-]+$'

INSTANCE_NAME_ARG = {
    'name': 'instance-name',
    'synopsis': '--instance-name <instance-name>',
    'required': True,
    'help_text': (
        'Required. The name of the on-premises instance.'
    )
}

IAM_USER_ARN_ARG = {
    'name': 'iam-user-arn',
    'synopsis': '--iam-user-arn <iam-user-arn>',
    'required': False,
    'help_text': (
        'Optional. The IAM user associated with the on-premises instance.'
    )
}


def validate_region(params, parsed_globals):
    if parsed_globals.region:
        params.region = parsed_globals.region
    else:
        params.region = params.session.get_config_variable('region')
    if not params.region:
        raise RuntimeError('Region not specified.')


def validate_instance_name(params):
    if params.instance_name:
        if not re.match(INSTANCE_NAME_PATTERN, params.instance_name):
            raise ValueError('Instance name contains invalid characters.')
        if params.instance_name.startswith('i-'):
            raise ValueError('Instance name cannot start with \'i-\'.')
        if len(params.instance_name) > MAX_INSTANCE_NAME_LENGTH:
            raise ValueError(
                'Instance name cannot be longer than {0} characters.'.format(
                    MAX_INSTANCE_NAME_LENGTH
                )
            )


def validate_tags(params):
    if params.tags:
        if len(params.tags) > MAX_TAGS_PER_INSTANCE:
            raise ValueError(
                'Instances can only have a maximum of {0} tags.'.format(
                    MAX_TAGS_PER_INSTANCE
                )
            )
        for tag in params.tags:
            if len(tag['Key']) > MAX_TAG_KEY_LENGTH:
                raise ValueError(
                    'Tag Key cannot be longer than {0} characters.'.format(
                        MAX_TAG_KEY_LENGTH
                    )
                )
            if len(tag['Value']) > MAX_TAG_VALUE_LENGTH:
                raise ValueError(
                    'Tag Value cannot be longer than {0} characters.'.format(
                        MAX_TAG_VALUE_LENGTH
                    )
                )


def validate_iam_user_arn(params):
    if params.iam_user_arn and \
            not re.match(IAM_USER_ARN_PATTERN, params.iam_user_arn):
        raise ValueError('Invalid IAM user ARN.')


def validate_instance(params):
    if platform.system() == 'Linux':
        distribution = awscli.compat.linux_distribution()[0]
        if 'Ubuntu' in distribution:
            params.system = Ubuntu(params)
        if 'Red Hat Enterprise Linux Server' in distribution:
            params.system = RHEL(params)
    elif platform.system() == 'Windows':
        params.system = Windows(params)
    if 'system' not in params:
        raise RuntimeError(
            System.UNSUPPORTED_SYSTEM_MSG
        )
    try:
        urlopen('http://169.254.169.254/latest/meta-data/', timeout=1)
        raise RuntimeError('Amazon EC2 instances are not supported.')
    except (URLError, timeout):
        pass


def validate_s3_location(params, arg_name):
    arg_name = arg_name.replace('-', '_')
    if arg_name in params:
        s3_location = getattr(params, arg_name)
        if s3_location:
            matcher = re.match('s3://(.+?)/(.+)', str(s3_location))
            if matcher:
                params.bucket = matcher.group(1)
                params.key = matcher.group(2)
            else:
                raise ValueError(
                    '--{0} must specify the Amazon S3 URL format as '
                    's3://<bucket>/<key>.'.format(
                        arg_name.replace('_', '-')
                    )
                )
