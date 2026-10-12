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
from awscli.customizations.lambdaweb import constants, model
from awscli.customizations.lambdaweb.exceptions import (
    LambdaWebError,
    WebFunctionRevisionNotFoundError,
)
from awscli.customizations.lambdaweb.utils import strip_empty


def resolve_latest_revision(lambda_web, function_name):
    """Return the ``GetWebFunctionRevision`` response for the latest revision.

    Prefers the most recent ``Active`` revision, else the most recent overall.
    ``GetWebFunction`` returns only identity members, so everything inherited
    on redeploy has to come from the revision-level API.

    Revision creation does not accept an expected base revision. Another
    revision can be created after this function returns, and repeating the
    read would shorten, but not eliminate, that window.
    """
    response = lambda_web.list_web_function_revisions(
        functionName=function_name
    )
    revisions = response.get('revisions') or []
    if not revisions:
        raise WebFunctionRevisionNotFoundError(
            f"Web Function '{function_name}' has no revisions to inherit from. "
            'Pass --runtime and --execution-role-arn explicitly, or use '
            f'{constants.CONFIRM_CREATE_FLAG} to create a new Web Function.'
        )
    # ``createdAt`` is a tz-aware datetime, so it cannot be sorted against a
    # scalar fallback; sort the dated ones and treat any undated as oldest.
    undated = [r for r in revisions if r.get('createdAt') is None]
    sorted_revisions = (
        sorted(
            (r for r in revisions if r.get('createdAt') is not None),
            key=lambda r: r['createdAt'],
            reverse=True,
        )
        + undated
    )
    active = next(
        (r for r in sorted_revisions if r.get('state') == 'Active'), None
    )
    chosen = active if active is not None else sorted_revisions[0]
    return lambda_web.get_web_function_revision(
        functionName=function_name,
        revisionId=chosen['revisionId'],
    )


def resolve_auto_deployment_mode(parsed_args):
    """Return the autoDeploymentMode for the create endpoint config.

    An explicit --auto-deployment-mode always wins. When omitted, a
    region-required endpoint type defaults to ``Disabled`` because the service
    accepts nothing else for it; every other type keeps the global default.
    """
    if parsed_args.auto_deployment_mode:
        return parsed_args.auto_deployment_mode
    endpoint_type = (
        parsed_args.endpoint_type or constants.DEFAULT_ENDPOINT_TYPE
    )
    if endpoint_type in constants.REGION_REQUIRED_ENDPOINT_TYPES:
        return constants.DISABLED_AUTO_DEPLOYMENT_MODE
    return constants.DEFAULT_AUTO_DEPLOYMENT_MODE


def _resolve_regions(parsed_args, norm, current_region):
    """Return the ordered, deduped region list for the endpoint config."""
    if parsed_args.regions:
        return list(norm.regions)
    endpoint_type = (
        parsed_args.endpoint_type or constants.DEFAULT_ENDPOINT_TYPE
    )
    if endpoint_type in constants.REGION_REQUIRED_ENDPOINT_TYPES:
        raise LambdaWebError(
            f'--regions is required for --endpoint-type {endpoint_type}.'
        )
    return [current_region]


def _endpoint_tuning(parsed_args):
    """Return the endpoint ``scalingConfig`` / ``throttleConfig`` structures.

    Both carry a single member, so deploy exposes them as flat scalars and
    rebuilds the nested shape here. ``strip_empty`` drops either structure
    when its member is unset, and keeps a legal ``--rate-limit 0``.
    """
    return {
        'scalingConfig': {'maxEnvironments': parsed_args.max_environments},
        'throttleConfig': {'rateLimit': parsed_args.rate_limit},
    }


def _endpoint_shape(parsed_args, norm, region):
    """Return the endpoint members shared by the two endpoint-create paths."""
    return {
        'endpointType': (
            parsed_args.endpoint_type or constants.DEFAULT_ENDPOINT_TYPE
        ),
        'authType': parsed_args.auth_type or constants.DEFAULT_AUTH_TYPE,
        'autoDeploymentMode': resolve_auto_deployment_mode(parsed_args),
        'regions': _resolve_regions(parsed_args, norm, region),
        'description': parsed_args.description,
        **_endpoint_tuning(parsed_args),
    }


def _s3_object(replacement, existing=None):
    """Merge replacement S3 coordinates into inherited modeled fields."""
    merged = dict(existing or {})
    merged['bucket'] = replacement['bucket']
    merged['key'] = replacement['key']
    version_id = replacement.get('versionId')
    if version_id:
        merged['versionId'] = version_id
    else:
        merged.pop('versionId', None)
    return merged


def _revision_weights(revision_id):
    return [{'revisionId': revision_id, 'weight': 100}]


def _service_config(role_arn, timeout, concurrency, env_vars, telemetry):
    return {
        'executionRoleArn': role_arn,
        'timeoutSeconds': timeout,
        'maxConcurrencyPerEnvironment': concurrency,
        'environmentVariables': env_vars,
        'telemetryConfig': telemetry,
    }


def _build_create_logging_config(app_log, sys_log):
    """Build create-time telemetry configuration from log-level options."""
    if not app_log and not sys_log:
        return None
    config = {}
    if app_log:
        config['applicationLogLevel'] = app_log
    if sys_log:
        config['systemLogLevel'] = sys_log
    return {'loggingConfig': config}


def build_create_request(parsed_args, norm, tags, role_arn, s3_obj, region):
    """Return the kwargs for ``create_web_function``.

    Optional fields that are unset (``None`` / empty) are omitted via
    :func:`strip_empty` so the request never sends placeholders.
    """
    request = {
        'functionName': parsed_args.name,
        'revisionConfig': {
            'description': parsed_args.revision_description,
            'kmsKeyArn': parsed_args.kms_key_arn,
            'buildConfig': {
                'codeConfig': {'s3Object': _s3_object(s3_obj)},
                'runtimeConfig': {
                    'runtime': parsed_args.runtime or constants.DEFAULT_RUNTIME
                },
            },
            'serviceConfig': _service_config(
                role_arn,
                parsed_args.timeout_seconds,
                parsed_args.max_concurrency_per_environment,
                norm.env,
                # leave logGroup unset so the service applies its own default
                # rather than the CLI pinning one.
                _build_create_logging_config(
                    parsed_args.application_log_level,
                    parsed_args.system_log_level,
                ),
            ),
        },
        'endpointConfig': {
            'endpointName': (
                parsed_args.endpoint_name or constants.DEFAULT_ENDPOINT_NAME
            ),
            **_endpoint_shape(parsed_args, norm, region),
        },
    }
    request = strip_empty(request)
    # Tag values may be empty, so add the validated map after generic cleanup.
    if tags:
        request['tags'] = tags
    return request


# Revision-scoped metadata that does not carry forward unless the caller
# supplies a new value.
_REVISION_FIELDS_NOT_INHERITED = frozenset({'description'})


def build_revision_request(
    session, parsed_args, norm, role_arn, s3_obj, existing
):
    """Return the kwargs for ``create_web_function_revision``.

    Start with every field shared by the previous revision response and the
    current operation input model, then apply the requested changes.
    """
    request = model.copy_input_fields(
        session, 'CreateWebFunctionRevision', existing
    )
    for field in _REVISION_FIELDS_NOT_INHERITED:
        request.pop(field, None)
    request['functionName'] = parsed_args.name
    if parsed_args.revision_description:
        request['description'] = parsed_args.revision_description
    # Treat an empty value as omitted so the inherited AWS KMS key is
    # preserved.
    if parsed_args.kms_key_arn:
        request['kmsKeyArn'] = parsed_args.kms_key_arn

    model.update_input_member(
        session,
        'CreateWebFunctionRevision',
        ('buildConfig', 'codeConfig', 's3Object'),
        request,
        lambda existing: _s3_object(s3_obj, existing),
    )
    build_config = request['buildConfig']
    runtime_config = build_config.setdefault('runtimeConfig', {})
    runtime = parsed_args.runtime or runtime_config.get('runtime')
    if not runtime:
        raise LambdaWebError(
            'The command could not determine the runtime. Specify --runtime.'
        )
    runtime_config['runtime'] = runtime

    service_config = request.setdefault('serviceConfig', {})
    service_config['executionRoleArn'] = role_arn
    if parsed_args.timeout_seconds is not None:
        service_config['timeoutSeconds'] = parsed_args.timeout_seconds
    if parsed_args.max_concurrency_per_environment is not None:
        service_config['maxConcurrencyPerEnvironment'] = (
            parsed_args.max_concurrency_per_environment
        )
    if norm.env or norm.unset_env:
        service_config['environmentVariables'] = _resolve_env_vars(
            norm, service_config
        )

    if (
        parsed_args.application_log_level is not None
        or parsed_args.system_log_level is not None
    ):
        telemetry = service_config.setdefault('telemetryConfig', {})
        logging_config = telemetry.setdefault('loggingConfig', {})
        if parsed_args.application_log_level is not None:
            logging_config['applicationLogLevel'] = (
                parsed_args.application_log_level
            )
        if parsed_args.system_log_level is not None:
            logging_config['systemLogLevel'] = parsed_args.system_log_level
    return request


def _resolve_env_vars(norm, service_config):
    """Merge CLI environment changes into the projected service configuration.

    Start from the projected ``environmentVariables`` map, overlay the
    ``--env`` entries (add or override), then drop any keys named by
    ``--unset-env``. Unset is applied last, so ``--unset-env K`` wins even if
    ``K`` is also passed via ``--env``. Omitting both inherits the existing
    environment unchanged.
    """
    merged = dict(service_config.get('environmentVariables') or {})
    merged.update(norm.env)
    for key in norm.unset_env:
        merged.pop(key, None)
    return merged


def build_create_endpoint_request(parsed_args, norm, region, revision_id):
    """Return kwargs for ``create_web_function_endpoint`` (add-endpoint path).

    The new endpoint serves the revision just deployed. A ``LatestRevision``
    endpoint must omit ``revisionWeights`` and auto-follows the latest Active
    revision; a ``Disabled`` one requires them, so pin the new revision. The
    service rejects the request if either rule is broken.
    """
    shape = _endpoint_shape(parsed_args, norm, region)
    request = {
        'functionName': parsed_args.name,
        'endpointName': parsed_args.endpoint_name,
        **shape,
    }
    if shape['autoDeploymentMode'] == constants.DISABLED_AUTO_DEPLOYMENT_MODE:
        request['revisionWeights'] = _revision_weights(revision_id)
    return strip_empty(request)


def build_update_endpoint_request(parsed_args, target, revision_id):
    """Return ``(request_or_None, note)`` for pointing/reconfiguring endpoint.

    The request is ``None`` when no update is needed, and only mutable fields
    are ever sent. A ``LatestRevision`` endpoint already follows the latest
    revision, so it is updated only for a differing shape arg; a pinned one is
    repointed, unless it splits traffic across revisions, which is left alone
    with an explanatory ``note``.
    """
    current_mode = target.get('autoDeploymentMode')
    desired_mode = parsed_args.auto_deployment_mode or current_mode
    note = None
    request = {
        'functionName': parsed_args.name,
        'endpointName': target['endpointName'],
    }
    changed = False

    if parsed_args.auth_type and parsed_args.auth_type != target.get(
        'authType'
    ):
        request['authType'] = parsed_args.auth_type
        changed = True
    if parsed_args.description is not None and parsed_args.description != (
        target.get('description') or ''
    ):
        request['description'] = parsed_args.description
        changed = True
    if desired_mode != current_mode:
        request['autoDeploymentMode'] = desired_mode
        changed = True

    # Endpoint tuning: send a structure only when the caller asked for a value
    # that differs from the live endpoint, so a plain redeploy never rewrites
    # limits somebody tuned out of band.
    for value, config_key, member in (
        (parsed_args.max_environments, 'scalingConfig', 'maxEnvironments'),
        (parsed_args.rate_limit, 'throttleConfig', 'rateLimit'),
    ):
        if value is None:
            continue
        if value != (target.get(config_key) or {}).get(member):
            request[config_key] = {member: value}
            changed = True

    # Decide the revision pin. Only Disabled endpoints carry explicit weights;
    # LatestRevision auto-follows and MUST NOT receive weights.
    if desired_mode == constants.DISABLED_AUTO_DEPLOYMENT_MODE:
        existing_weights = target.get('revisionWeights') or []
        if desired_mode != current_mode:
            # Switching TO Disabled: the service would silently keep stale
            # weights, so we must supply them. Pin the new revision.
            request['revisionWeights'] = _revision_weights(revision_id)
            changed = True
        elif len(existing_weights) > 1:
            # A deliberate multi-revision canary split: don't collapse it.
            note = (
                f"The command preserved endpoint '{target['endpointName']}' "
                f"because it splits traffic across {len(existing_weights)} "
                'revisions. To replace the traffic split, point the endpoint '
                f'at revision {revision_id} with '
                "'aws lambda-web update-web-function-endpoint'."
            )
        elif existing_weights != _revision_weights(revision_id):
            # Single-pin (or empty): repoint to the freshly deployed revision.
            request['revisionWeights'] = _revision_weights(revision_id)
            changed = True

    if not changed:
        return None, note
    return request, note
