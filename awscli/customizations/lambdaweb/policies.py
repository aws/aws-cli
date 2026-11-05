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

from awscli.customizations.lambdaweb import constants


def trust_policy_document():
    """Return a compact JSON trust policy allowing Lambda to assume the role."""
    policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {
                    'Service': constants.WEB_FUNCTION_SERVICE_PRINCIPAL
                },
                'Action': 'sts:AssumeRole',
            }
        ],
    }
    return json.dumps(policy, separators=(',', ':'))


def execution_role_inline_policy():
    """Return a compact policy that allows the runtime to publish logs."""
    policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': [
                    'logs:CreateLogGroup',
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                ],
                'Resource': '*',
            }
        ],
    }
    return json.dumps(policy, separators=(',', ':'))


def bucket_policy_document(partition, bucket, account_id):
    """Return a compact JSON bucket policy enforcing TLS and Lambda access."""
    bucket_arn = f'arn:{partition}:s3:::{bucket}'
    policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': 'HttpsOnly',
                'Effect': 'Deny',
                'Principal': '*',
                'Action': 's3:*',
                'Resource': [bucket_arn, f'{bucket_arn}/*'],
                'Condition': {'Bool': {'aws:SecureTransport': 'false'}},
            },
            {
                'Sid': 'AllowLambdaServiceAccess',
                'Effect': 'Allow',
                'Principal': {
                    'Service': constants.WEB_FUNCTION_SERVICE_PRINCIPAL
                },
                'Action': ['s3:GetObject', 's3:GetObjectVersion'],
                'Resource': f'{bucket_arn}/*',
                'Condition': {
                    'StringEquals': {'aws:SourceAccount': account_id}
                },
            },
        ],
    }
    return json.dumps(policy, separators=(',', ':'))
