# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json

from awscli.customizations.lambdaweb.policies import (
    bucket_policy_document,
    execution_role_inline_policy,
    trust_policy_document,
)


def test_trust_policy_uses_web_function_service():
    result = trust_policy_document()
    assert '"Service":"lambda.amazonaws.com"' in result
    parsed = json.loads(result)
    assert (
        parsed['Statement'][0]['Principal']['Service']
        == 'lambda.amazonaws.com'
    )


def test_execution_role_policy_allows_cloudwatch_logs():
    result = execution_role_inline_policy()
    parsed = json.loads(result)
    assert parsed['Statement'] == [
        {
            'Effect': 'Allow',
            'Action': [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
            ],
            'Resource': '*',
        },
    ]


def test_bucket_policy_partition_aware():
    result = bucket_policy_document('aws', 'my-bucket', '111122223333')
    assert 'arn:aws:s3:::my-bucket' in result
    parsed = json.loads(result)
    sids = [s['Sid'] for s in parsed['Statement']]
    assert 'HttpsOnly' in sids
    assert 'AllowLambdaServiceAccess' in sids
    lambda_statement = next(
        statement
        for statement in parsed['Statement']
        if statement['Sid'] == 'AllowLambdaServiceAccess'
    )
    assert lambda_statement['Condition'] == {
        'StringEquals': {'aws:SourceAccount': '111122223333'}
    }
