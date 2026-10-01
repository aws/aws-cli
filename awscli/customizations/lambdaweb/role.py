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
"""IAM execution role helpers for ``lambda-web`` commands.

The orchestrator uses :func:`ensure_role` to reuse an existing role without
modification or create a managed role with a Lambda trust policy and an inline
CloudWatch Logs policy.

:func:`wait_for_iam_propagation` wraps any zero-arg callable that consumes
a freshly created IAM role and retries only the transient role-assumption
error.
"""

import json
import logging
import time
import urllib.parse

from botocore.exceptions import ClientError

from awscli.customizations.lambdaweb import constants, naming, policies
from awscli.customizations.lambdaweb.exceptions import (
    IamPropagationTimeoutError,
    LambdaWebError,
    RoleNotFoundError,
    RoleTrustMismatchError,
)

LOG = logging.getLogger(__name__)

_INLINE_POLICY_NAME = 'awscli-lambdaweb-logs'
_EXPECTED_SERVICE_PRINCIPAL = constants.WEB_FUNCTION_SERVICE_PRINCIPAL

# Only the role-assumption ValidationException is retried: it indicates IAM
# eventual consistency ("cannot be assumed ... retry in a few seconds"). Other
# ValidationException causes are permanent and surface immediately.
_ROLE_PROPAGATION_SIGNATURE = 'cannot be assumed'


def ensure_role(iam_client, function_name, override_arn=None):
    """Return the role ARN to use for the function, creating it if needed.

    When ``override_arn`` is provided, the role is verified read-only and
    returned verbatim; no IAM mutation occurs. Otherwise the canonical
    ``awscli-lambdaweb-<function>`` role is fetched and validated or created
    and configured. Existing roles are not modified.
    """
    if override_arn:
        return _require_role_exists(iam_client, override_arn)

    name = naming.role_name(function_name)
    role = _get_role_or_none(iam_client, name)
    if role is not None:
        _require_lambda_trust(name, role['AssumeRolePolicyDocument'])
        return role['Arn']

    role, created = _create_role(iam_client, name)
    if created:
        try:
            _put_execution_role_policy(iam_client, name)
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise LambdaWebError(
                'Unable to add Amazon CloudWatch Logs permissions to the '
                f"newly created AWS IAM role '{name}' (AWS error: {code}). "
                'No Web Function was created, and the role was retained. To '
                "continue without changing the role's permissions, rerun the "
                'command. To retry adding the permissions, delete the role if '
                "it isn't in use and rerun the command. You can also specify "
                'another role with --execution-role-arn.'
            ) from e
    return role['Arn']


def _put_execution_role_policy(iam_client, role_name):
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=_INLINE_POLICY_NAME,
        PolicyDocument=policies.execution_role_inline_policy(),
    )


def wait_for_iam_propagation(
    operation_callable, *, retries=None, sleep_seconds=None
):
    """Invoke ``operation_callable`` and retry IAM propagation failures.

    Only the transient role-not-yet-assumable ``ValidationException`` is
    retried. Other errors propagate unchanged.
    """
    if retries is None:
        retries = constants.IAM_PROPAGATION_RETRIES
    if sleep_seconds is None:
        sleep_seconds = constants.IAM_PROPAGATION_RETRY_SLEEP_SECONDS

    last_error = None
    for attempt in range(retries):
        try:
            return operation_callable()
        except ClientError as e:
            if not _is_role_propagation_error(e):
                raise
            last_error = e
            if attempt < retries - 1:
                time.sleep(sleep_seconds)
    # ``retries`` attempts have only ``retries - 1`` sleeps between them, so
    # the wall-clock time actually waited is (retries - 1) * sleep_seconds,
    # not retries * sleep_seconds. Report the honest elapsed time.
    waited = (retries - 1) * sleep_seconds
    raise IamPropagationTimeoutError(
        f"AWS Lambda couldn't assume the AWS IAM role after {waited} seconds. "
        "Verify the role's trust policy, or retry if the role was recently "
        'created.'
    ) from last_error


def _is_role_propagation_error(error):
    """Return True only for the transient role-not-yet-assumable error."""
    err = error.response.get('Error', {})
    if err.get('Code') != 'ValidationException':
        return False
    return _ROLE_PROPAGATION_SIGNATURE in (err.get('Message') or '')


def _require_role_exists(iam_client, override_arn):
    name = override_arn.rsplit('/', 1)[-1]
    try:
        iam_client.get_role(RoleName=name)
    except ClientError as e:
        code = e.response['Error']['Code']
        if code == 'NoSuchEntity':
            raise RoleNotFoundError(
                f"AWS IAM role '{override_arn}' wasn't found or isn't "
                'accessible. Verify the ARN and your permissions.'
            )
        if code == 'AccessDenied':
            LOG.warning(
                "Unable to verify role '%s' (iam:GetRole denied); continuing "
                "because AWS Lambda assumes the execution role.",
                override_arn,
            )
            return override_arn
        raise
    return override_arn


def _get_role_or_none(iam_client, name):
    try:
        return iam_client.get_role(RoleName=name)['Role']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            return None
        raise


def _create_role(iam_client, name):
    try:
        return (
            iam_client.create_role(
                RoleName=name,
                AssumeRolePolicyDocument=policies.trust_policy_document(),
            )['Role'],
            True,
        )
    except ClientError as e:
        if e.response['Error']['Code'] != 'EntityAlreadyExists':
            raise
    role = _get_role_or_none(iam_client, name)
    if role is None:
        # Should not happen: EntityAlreadyExists implies the role exists.
        raise RoleTrustMismatchError(
            f"AWS IAM reported that role '{name}' already exists, but the "
            'command could not retrieve it. Verify your permissions and '
            'retry.'
        )
    _require_lambda_trust(name, role['AssumeRolePolicyDocument'])
    return role, False


def _service_principals(principal):
    """Return the ``Service`` principals as a flat list of strings."""
    if not isinstance(principal, dict):
        return []
    service = principal.get('Service')
    if isinstance(service, str):
        return [service]
    if isinstance(service, list):
        return [s for s in service if isinstance(s, str)]
    return []


def _require_lambda_trust(name, raw_document):
    """Raise ``RoleTrustMismatchError`` unless the doc allows Lambda.

    Botocore typically auto-decodes ``AssumeRolePolicyDocument`` into a
    ``dict`` for IAM responses, but the raw API returns URL-encoded JSON.
    Accept either shape so the helper is robust against both code paths.

    A trust policy is accepted as long as any ``Allow`` statement lists the
    Lambda service principal, whether as a bare string, inside a list, or
    alongside other principals in a composite statement.
    """
    if isinstance(raw_document, str):
        document = json.loads(urllib.parse.unquote(raw_document))
    else:
        document = raw_document
    statements = document.get('Statement', [])
    if isinstance(statements, dict):
        statements = [statements]

    found_principals = []
    for statement in statements:
        if statement.get('Effect') != 'Allow':
            continue
        principal = statement.get('Principal')
        found_principals.append(principal)
        if _EXPECTED_SERVICE_PRINCIPAL in _service_principals(principal):
            return

    raise RoleTrustMismatchError(
        f"AWS IAM role '{name}' doesn't trust the Lambda service principal "
        f"'{_EXPECTED_SERVICE_PRINCIPAL}'. The current principals are "
        f'{found_principals}. Update the trust policy, specify a different '
        'role with --execution-role-arn, or delete the role so the command '
        'can create it again.'
    )
