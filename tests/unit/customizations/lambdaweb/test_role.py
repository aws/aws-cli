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
import urllib.parse
from unittest import mock

import botocore.session
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from awscli.customizations.lambdaweb import naming, policies
from awscli.customizations.lambdaweb import role as role_module
from awscli.customizations.lambdaweb.exceptions import (
    IamPropagationTimeoutError,
    LambdaWebError,
    RoleNotFoundError,
    RoleTrustMismatchError,
)
from awscli.customizations.lambdaweb.role import (
    ensure_role,
    wait_for_iam_propagation,
)

REGION = 'us-east-1'
ACCOUNT_ID = '123456789012'
FUNCTION_NAME = 'my-fn'
ROLE_NAME = naming.role_name(FUNCTION_NAME)
ROLE_ARN = f'arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}'


def _make_iam_client():
    session = botocore.session.get_session()
    return session.create_client('iam', region_name=REGION)


def _encoded_trust(principal):
    document = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': principal,
                'Action': 'sts:AssumeRole',
            }
        ],
    }
    return urllib.parse.quote(json.dumps(document))


def _role_payload(arn, principal):
    return {
        'Role': {
            'Path': '/',
            'RoleName': arn.rsplit('/', 1)[-1],
            'RoleId': 'AROAEXAMPLEROLEIDXX',
            'Arn': arn,
            'CreateDate': '2026-01-01T00:00:00Z',
            'AssumeRolePolicyDocument': _encoded_trust(principal),
        }
    }


def test_ensure_role_user_override_no_mutation():
    override_arn = 'arn:aws:iam::123456789012:role/customer-role'
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_response(
        'get_role',
        _role_payload(override_arn, {'Service': 'ec2.amazonaws.com'}),
        expected_params={'RoleName': 'customer-role'},
    )
    with stubber:
        result = ensure_role(
            client,
            FUNCTION_NAME,
            override_arn=override_arn,
        )
    assert result == override_arn
    stubber.assert_no_pending_responses()


def test_ensure_role_user_override_NoSuchEntity_raises_RoleNotFound():
    override_arn = 'arn:aws:iam::123456789012:role/missing-role'
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'get_role',
        service_error_code='NoSuchEntity',
        service_message='Role missing-role does not exist',
        expected_params={'RoleName': 'missing-role'},
    )
    with stubber:
        with pytest.raises(RoleNotFoundError) as excinfo:
            ensure_role(
                client,
                FUNCTION_NAME,
                override_arn=override_arn,
            )
    assert override_arn in str(excinfo.value)
    stubber.assert_no_pending_responses()


def test_ensure_role_user_override_AccessDenied_warns_and_returns_arn():
    override_arn = 'arn:aws:iam::123456789012:role/customer-role'
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'get_role',
        service_error_code='AccessDenied',
        service_message='User is not authorized to perform iam:GetRole',
        expected_params={'RoleName': 'customer-role'},
    )
    with (
        stubber,
        mock.patch.object(role_module.LOG, 'warning') as warning,
    ):
        result = ensure_role(
            client,
            FUNCTION_NAME,
            override_arn=override_arn,
        )

    assert result == override_arn
    warning.assert_called_once()
    stubber.assert_no_pending_responses()


def test_ensure_role_get_200_matching_trust_reuses_without_mutation():
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_response(
        'get_role',
        _role_payload(ROLE_ARN, {'Service': 'lambda.amazonaws.com'}),
        expected_params={'RoleName': ROLE_NAME},
    )
    with stubber:
        result = ensure_role(client, FUNCTION_NAME)
    assert result == ROLE_ARN
    stubber.assert_no_pending_responses()


def test_ensure_role_get_200_list_form_service_principal_reuses():
    # IAM commonly returns the Service principal as a single-element
    # list; that trust policy DOES allow Lambda and must be accepted.
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_response(
        'get_role',
        _role_payload(ROLE_ARN, {'Service': ['lambda.amazonaws.com']}),
        expected_params={'RoleName': ROLE_NAME},
    )
    with stubber:
        result = ensure_role(client, FUNCTION_NAME)
    assert result == ROLE_ARN
    stubber.assert_no_pending_responses()


def test_ensure_role_get_200_composite_service_principal_reuses():
    # A role trusting a composite of several service principals is valid;
    # reuse as long as lambda.amazonaws.com is among them.
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_response(
        'get_role',
        _role_payload(
            ROLE_ARN,
            {'Service': ['edgelambda.amazonaws.com', 'lambda.amazonaws.com']},
        ),
        expected_params={'RoleName': ROLE_NAME},
    )
    with stubber:
        result = ensure_role(client, FUNCTION_NAME)
    assert result == ROLE_ARN
    stubber.assert_no_pending_responses()


def test_ensure_role_get_200_list_without_lambda_raises():
    # A composite that does NOT include lambda.amazonaws.com is still rejected.
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_response(
        'get_role',
        _role_payload(
            ROLE_ARN,
            {'Service': ['ec2.amazonaws.com', 'ecs.amazonaws.com']},
        ),
        expected_params={'RoleName': ROLE_NAME},
    )
    with stubber:
        with pytest.raises(RoleTrustMismatchError) as excinfo:
            ensure_role(client, FUNCTION_NAME)
    assert 'lambda.amazonaws.com' in str(excinfo.value)
    stubber.assert_no_pending_responses()


def test_ensure_role_get_200_different_trust_raises_no_mutation():
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_response(
        'get_role',
        _role_payload(ROLE_ARN, {'Service': 'ec2.amazonaws.com'}),
        expected_params={'RoleName': ROLE_NAME},
    )
    with stubber:
        with pytest.raises(RoleTrustMismatchError) as excinfo:
            ensure_role(client, FUNCTION_NAME)
    message = str(excinfo.value)
    assert 'lambda.amazonaws.com' in message
    assert 'ec2.amazonaws.com' in message
    stubber.assert_no_pending_responses()


def test_ensure_role_no_such_entity_creates_and_policies():
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'get_role',
        service_error_code='NoSuchEntity',
        service_message=f'Role {ROLE_NAME} does not exist',
        expected_params={'RoleName': ROLE_NAME},
    )
    stubber.add_response(
        'create_role',
        _role_payload(ROLE_ARN, {'Service': 'lambda.amazonaws.com'}),
        expected_params={
            'RoleName': ROLE_NAME,
            'AssumeRolePolicyDocument': policies.trust_policy_document(),
        },
    )
    stubber.add_response(
        'put_role_policy',
        {},
        expected_params={
            'RoleName': ROLE_NAME,
            'PolicyName': 'awscli-lambdaweb-logs',
            'PolicyDocument': policies.execution_role_inline_policy(),
        },
    )
    with stubber:
        result = ensure_role(client, FUNCTION_NAME)
    assert result == ROLE_ARN
    stubber.assert_no_pending_responses()


def test_ensure_role_policy_failure_reports_retained_role():
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'get_role',
        service_error_code='NoSuchEntity',
        service_message=f'Role {ROLE_NAME} does not exist',
        expected_params={'RoleName': ROLE_NAME},
    )
    stubber.add_response(
        'create_role',
        _role_payload(ROLE_ARN, {'Service': 'lambda.amazonaws.com'}),
        expected_params={
            'RoleName': ROLE_NAME,
            'AssumeRolePolicyDocument': policies.trust_policy_document(),
        },
    )
    stubber.add_client_error(
        'put_role_policy',
        service_error_code='AccessDenied',
        expected_params={
            'RoleName': ROLE_NAME,
            'PolicyName': 'awscli-lambdaweb-logs',
            'PolicyDocument': policies.execution_role_inline_policy(),
        },
    )

    with stubber, pytest.raises(LambdaWebError) as excinfo:
        ensure_role(client, FUNCTION_NAME)

    message = str(excinfo.value)
    assert ROLE_NAME in message
    assert 'Amazon CloudWatch Logs permissions' in message
    assert 'No Web Function was created' in message
    assert 'role was retained' in message
    assert "role's permissions" in message
    assert "delete the role if it isn't in use" in message
    assert '--execution-role-arn' in message
    stubber.assert_no_pending_responses()


def test_ensure_role_EntityAlreadyExists_refetches():
    client = _make_iam_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'get_role',
        service_error_code='NoSuchEntity',
        service_message='Role does not exist',
        expected_params={'RoleName': ROLE_NAME},
    )
    stubber.add_client_error(
        'create_role',
        service_error_code='EntityAlreadyExists',
        service_message=f'Role with name {ROLE_NAME} already exists',
        expected_params={
            'RoleName': ROLE_NAME,
            'AssumeRolePolicyDocument': policies.trust_policy_document(),
        },
    )
    stubber.add_response(
        'get_role',
        _role_payload(ROLE_ARN, {'Service': 'lambda.amazonaws.com'}),
        expected_params={'RoleName': ROLE_NAME},
    )
    with stubber:
        result = ensure_role(client, FUNCTION_NAME)
    assert result == ROLE_ARN
    stubber.assert_no_pending_responses()


def test_iam_propagation_retries_on_invalid_parameter():
    call_count = {'n': 0}

    def operation():
        call_count['n'] += 1
        if call_count['n'] <= 5:
            raise ClientError(
                {
                    'Error': {
                        'Code': 'ValidationException',
                        'Message': (
                            'The provided execution role '
                            '(arn:aws:iam::111:role/r) cannot be assumed by '
                            'lambda.amazonaws.com, verify its trust policy. '
                            'If the role was just created, retry in a few '
                            'seconds.'
                        ),
                    }
                },
                'CreateWebFunction',
            )
        return 'ok'

    with mock.patch('time.sleep') as sleep_mock:
        result = wait_for_iam_propagation(
            operation, retries=6, sleep_seconds=5
        )

    assert result == 'ok'
    assert call_count['n'] == 6
    assert sleep_mock.call_count == 5
    for call in sleep_mock.call_args_list:
        assert call.args == (5,)


def test_iam_propagation_raises_after_retries():
    call_count = {'n': 0}

    def operation():
        call_count['n'] += 1
        raise ClientError(
            {
                'Error': {
                    'Code': 'ValidationException',
                    'Message': (
                        'The provided execution role '
                        '(arn:aws:iam::111:role/r) cannot be assumed by '
                        'lambda.amazonaws.com, verify its trust policy.'
                    ),
                }
            },
            'CreateWebFunction',
        )

    with mock.patch('time.sleep'):
        with pytest.raises(IamPropagationTimeoutError) as excinfo:
            wait_for_iam_propagation(
                operation,
                retries=6,
                sleep_seconds=5,
            )

    assert call_count['n'] == 6
    assert isinstance(excinfo.value.__cause__, ClientError)
    # The reported wait is the time actually waited, (retries - 1) *
    # sleep_seconds = 25s, not the earlier over-stated retries * sleep = 30s.
    assert 'after 25 seconds' in str(excinfo.value)
    assert '30 seconds' not in str(excinfo.value)


def test_iam_propagation_does_not_catch_other_errors():
    call_count = {'n': 0}

    def operation():
        call_count['n'] += 1
        raise ClientError(
            {
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'not allowed',
                }
            },
            'CreateWebFunction',
        )

    with mock.patch('time.sleep') as sleep_mock:
        with pytest.raises(ClientError) as excinfo:
            wait_for_iam_propagation(operation)

    assert excinfo.value.response['Error']['Code'] == 'AccessDenied'
    assert call_count['n'] == 1
    assert sleep_mock.call_count == 0


# Only role-assumption ValidationExceptions are retried. Other validation
# failures must surface immediately with their original message.
@pytest.mark.parametrize(
    'message',
    [
        (
            'Lambda service principal lambda.amazonaws.com does not have '
            's3:GetObject and s3:GetObjectVersion permission on '
            's3://my-bucket/key.zip. Update the bucket policy to grant the '
            'Lambda service principal access and retry.'
        ),
        (
            'Lambda service principal lambda.amazonaws.com does not have '
            'kms:Decrypt permission on the KMS key used to encrypt '
            's3://my-bucket/key.zip. Grant the Lambda service principal '
            'kms:Decrypt on the KMS key policy and retry.'
        ),
        'Log group names starting with aws/ are reserved for AWS.',
    ],
)
def test_iam_propagation_does_not_retry_other_validation_exceptions(message):
    call_count = {'n': 0}

    def operation():
        call_count['n'] += 1
        raise ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': message}},
            'CreateWebFunction',
        )

    with mock.patch('time.sleep') as sleep_mock:
        with pytest.raises(ClientError) as excinfo:
            wait_for_iam_propagation(operation)

    # Surfaced immediately (no retry loop), and the ClientError -- carrying the
    # service's own message -- is what reaches the caller, NOT the generic
    # IamPropagationTimeoutError.
    assert call_count['n'] == 1
    assert sleep_mock.call_count == 0
    assert excinfo.value.response['Error']['Message'] == message
