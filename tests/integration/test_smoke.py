# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from nose.tools import assert_equal

from awscli.testutils import aws


# These are a list of commands that we should run.
# We're just verifying that we can properly send a no-arg request
# and that we can parse any response that comes back.
COMMANDS = [
    'autoscaling describe-account-limits',
    'autoscaling describe-adjustment-types',
    'cloudformation describe-stacks',
    'cloudformation list-stacks',
    'cloudsearch describe-domains',
    'cloudsearch list-domain-names',
    'cloudtrail describe-trails',
    'cloudwatch list-metrics',
    'cognito-identity list-identity-pools --max-results 1',
    'datapipeline list-pipelines',
    'directconnect describe-connections',
    'dynamodb list-tables',
    'ec2 describe-instances',
    'ec2 describe-regions',
    'elasticache describe-cache-clusters',
    'elb describe-load-balancers',
    'emr list-clusters',
    'iam list-users',
    'kinesis list-streams',
    'logs describe-log-groups',
    'opsworks describe-stacks',
    'rds describe-db-instances',
    'redshift describe-clusters',
    'route53 list-hosted-zones',
    'route53domains list-domains',
    's3api list-buckets',
    's3 ls',
    'ses list-identities',
    'sns list-topics',
    'sqs list-queues',
    'storagegateway list-gateways',
    'swf list-domains --registration-status REGISTERED',
]


def test_can_make_success_request():
    for cmd in COMMANDS:
        yield _run_aws_command, cmd


def _run_aws_command(command_string):
    result = aws(command_string)
    assert_equal(result.rc, 0)
    assert_equal(result.stderr, '')
