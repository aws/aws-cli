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
import re
import os
import random
import time

import pytest

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
    # Smoke test for timestamp parsing.
    'emr list-clusters --created-after 2014-11-24T00:00:00',
    'iam list-users',
    'kinesis list-streams',
    'kms generate-random --number-of-bytes 128',
    'logs describe-log-groups',
    # 'opsworks describe-stacks',
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
    ('swf list-open-workflow-executions --domain foo '
     '--start-time-filter oldestDate=1970-01-01'),

    # Verify waiters as well.  We're picking the
    # "resource does not exist" type waiters so we can
    # give an identifier that doesn't exist and verify we have
    # a 0 rc.
    'rds wait db-instance-deleted --db-instance-identifier foo-123',
]


# A list of commands that generate error messages.  The idea is to try to have
# at least one command for each service.
#
# This verifies that service errors are properly displayed to the user, as
# opposed to either silently failing or inproperly handling the error responses
# and not displaying something useful.  Each command tries to call an operation
# with an identifier that does not exist, and part of the identifier is also
# randomly generated to help ensure that is the case.
ERROR_COMMANDS = [
    'autoscaling attach-instances --auto-scaling-group-name %s',
    'cloudformation cancel-update-stack --stack-name %s',
    'cloudsearch describe-suggesters --domain-name %s',
    'cloudtrail get-trail-status --name %s',
    'cognito-identity delete-identity-pool --identity-pool-id %s',
    'datapipeline delete-pipeline --pipeline-id %s',
    'directconnect delete-connection --connection-id %s',
    'dynamodb delete-table --table-name %s',
    'ec2 terminate-instances --instance-ids %s',
    'elasticache delete-cache-cluster --cache-cluster-id %s',
    'elb describe-load-balancers --load-balancer-names %s',
    'emr list-instances --cluster-id %s',
    'iam delete-user --user-name %s',
    'kinesis delete-stream --stream-name %s',
    'logs delete-log-group --log-group-name %s',
    # 'opsworks delete-app --app-id %s',
    'rds delete-db-instance --db-instance-identifier %s',
    'redshift delete-cluster --cluster-identifier %s',
    'route53 delete-hosted-zone --id %s',
    'route53domains get-domain-detail --domain-name %s',
    's3api head-bucket --bucket %s',
    'ses set-identity-dkim-enabled --identity %s --dkim-enabled',
    'sns delete-endpoint --endpoint-arn %s',
    'sqs delete-queue --queue-url %s',
    # --gateway-arn has min length client side validation
    # so we have to generate an identifier that's long enough.
    ('storagegateway delete-gateway --gateway-arn '
     'foo-cli-test-foo-cli-test-foo-cli-test-%s'),
    'swf deprecate-domain --name %s',
]


# These services require a particular region to run.
REGION_OVERRIDES = {
    'route53domains': 'us-east-1'
}


def _aws(command_string, max_attempts=1, delay=5, target_rc=0):
    service = command_string.split()[0]
    env = None
    if service in REGION_OVERRIDES:
        env = os.environ.copy()
        env['AWS_DEFAULT_REGION'] = REGION_OVERRIDES[service]

    for _ in range(max_attempts - 1):
        result = aws(command_string, env_vars=env)
        if result.rc == target_rc:
            return result
        time.sleep(delay)
    return aws(command_string, env_vars=env)


@pytest.mark.parametrize(
    "cmd",
    COMMANDS
)
def test_can_make_success_request(cmd):
    result = _aws(cmd, max_attempts=5, delay=5, target_rc=0)
    assert result.rc == 0
    assert result.stderr == ''


ERROR_MESSAGE_RE = re.compile(
    r'An error occurred \(.+\) when calling the \w+ operation: \w+'
)


@pytest.mark.parametrize(
    "cmd",
    ERROR_COMMANDS
)
def test_display_error_message(cmd):
    identifier = 'foo-awscli-test-%s' % random.randint(1000, 100000)
    command_string = cmd % identifier
    result = _aws(command_string, target_rc=255)
    assert result.rc == 255

    match = ERROR_MESSAGE_RE.search(result.stderr)
    assert match is not None, (
        f'Error message was not displayed for command "{command_string}": {result.stderr}'
    )
