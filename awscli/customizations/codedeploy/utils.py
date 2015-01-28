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
import sys

from socket import timeout
from awscli.compat import urlopen, URLError

MAX_INSTANCE_NAME_LENGTH = 100

INSTANCE_NAME_PATTERN = r'^[A-Za-z0-9+=,.@_-]+$'
IAM_USER_ARN_PATTERN = r'^arn:aws:iam::[0-9]{12}:user/[A-Za-z0-9+=,.@_-]+$'

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

REGION_ARG = {
    'name': 'region',
    'synopsis': '--region <value>',
    'required': False,
    'help_text': (
        'Optional. The region where the on-premises instance is registered. '
        'Defaults to configured region, if not provided.'
    )
}


def validate_region(parsed_globals, session):
    if parsed_globals.region:
        region = parsed_globals.region
    else:
        region = session.get_config_variable('region')
    if not region:
        raise RuntimeError('Region not specified.')
    return region


def validate_instance_name(parsed_args):
    if parsed_args.instance_name:
        if not re.match(INSTANCE_NAME_PATTERN, parsed_args.instance_name):
            raise RuntimeError('Instance name contains invalid characters.')
        if parsed_args.instance_name.startswith('i-'):
            raise RuntimeError('Instance name cannot start with \'i-\'.')
        if len(parsed_args.instance_name) > MAX_INSTANCE_NAME_LENGTH:
            raise RuntimeError(
                'Instance name cannot be longer than {0} characters.'.format(
                    MAX_INSTANCE_NAME_LENGTH
                )
            )


def validate_s3_location(parsed_args, arg_name):
    arg_name = arg_name.replace('-', '_')
    if arg_name in parsed_args:
        s3_location = getattr(parsed_args, arg_name)
        if s3_location:
            matcher = re.match('s3://(.+?)/(.+)', s3_location)
            if matcher:
                parsed_args.bucket = matcher.group(1)
                parsed_args.key = matcher.group(2)
            else:
                raise RuntimeError(
                    '--{0} must specify the Amazon S3 URL format as '
                    's3://<bucket>/<key>'.format(
                        arg_name.replace('_', '-')
                    )
                )


def validate_iam_user_arn(parsed_args):
    if (
        parsed_args.iam_user_arn
        and not re.match(IAM_USER_ARN_PATTERN, parsed_args.iam_user_arn)
    ):
        raise RuntimeError('Invalid IAM user ARN.')


def validate_instance(parsed_args):
    if sys.platform == 'linux2':
        if 'Ubuntu' in platform.linux_distribution()[0]:
            parsed_args.system = 'ubuntu'
        elif 'Red Hat' in platform.linux_distribution()[0]:
            parsed_args.system = 'redhat'
    elif sys.platform == 'win32':
        parsed_args.system = 'windows'
    if (
        'system' not in parsed_args
        or parsed_args.system not in ['ubuntu', 'redhat', 'windows']
    ):
        raise RuntimeError(
            'Only Ubuntu, Red Hat or Windows systems are supported.'
        )
    try:
        urlopen('http://169.254.169.254/latest/meta-data/', timeout=1)
        raise RuntimeError('EC2 instances are not supported.')
    except (URLError, timeout):
        pass


def config_file():
    if sys.platform == 'win32':
        return 'conf.onpremises.yml'
    else:
        return 'codedeploy.onpremises.yml'


def config_path():
    if sys.platform == 'win32':
        return 'C:\\ProgramData\\Amazon\\CodeDeploy\\{0}'.format(config_file())
    else:
        return '/etc/codedeploy-agent/conf/{0}'.format(config_file())


def create_config_file(path, params):
    with open(path, 'w') as f:
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
