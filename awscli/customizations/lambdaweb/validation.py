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
import dataclasses
import os
import re

from awscli.customizations.lambdaweb import (
    args,
    constants,
    model,
    output,
    scaffold,
)
from awscli.customizations.lambdaweb.endpoint_plan import EndpointAction
from awscli.customizations.lambdaweb.exceptions import (
    InvalidArgumentValueError,
    InvalidKeyValueError,
    InvalidSourceError,
    LambdaWebError,
)
from awscli.customizations.lambdaweb.utils import (
    parse_kv,
    validate_int_in_model_range,
    validate_regions_against_model,
)

_ENVIRONMENT_VARIABLES_ATTRIBUTE = 'serviceConfig.environmentVariables'


@dataclasses.dataclass
class NormalizedArgs:
    """The repeatable / delimited args parsed once for the whole pipeline.

    Each of these is consumed by several validation gates and request
    builders, and parsing them once keeps every consumer looking at the same
    values.
    """

    env: dict
    """``--env`` entries as a KEY -> VAL map."""

    unset_env: list
    """``--unset-env`` keys, stripped, with empties dropped."""

    regions: list
    """``--regions`` entries in order, stripped and deduped."""


def normalize_args(session, parsed_args):
    """Parse the repeatable / delimited args, rejecting malformed values.

    Called at the point in the pipeline where the first of these values is
    needed, so a malformed one surfaces before any resource is created:
    botocore's own param validation runs inside the create/revision call,
    after the role and the upload, so a bad value caught there would leave
    both orphaned.
    """
    env = parse_kv(
        parsed_args.env,
        label='--env',
        reject_empty_values=True,
    )
    _validate_environment_variable_keys(session, env)
    return NormalizedArgs(
        env=env,
        unset_env=_unset_env_keys(parsed_args),
        regions=_split_regions(parsed_args.regions),
    )


def _validate_environment_variable_keys(session, env):
    if not env:
        return
    pattern = model.string_pattern(
        session,
        model.ENVIRONMENT_VARIABLE_KEY_SHAPE,
    )
    if not pattern:
        return
    matcher = re.compile(pattern)
    for key in env:
        if not matcher.fullmatch(key):
            raise InvalidKeyValueError(
                f"--env key '{key}' is not a valid environment variable name."
            )


def _unset_env_keys(parsed_args):
    raw = getattr(parsed_args, 'unset_env', None) or []
    return [key.strip() for key in raw if key.strip()]


def reject_unreadable_environment(function_name, revision):
    """Reject an update when the current environment cannot be inherited."""
    error = next(
        (
            item
            for item in revision.get('errors') or []
            if item.get('attribute') == _ENVIRONMENT_VARIABLES_ATTRIBUTE
        ),
        None,
    )
    if error is None:
        return
    code = error.get('errorCode') or 'UnknownError'
    message = (
        error.get('errorMessage')
        or 'The service could not read the environment variables.'
    ).rstrip()
    if not message.endswith(('.', '!', '?')):
        message += '.'
    raise LambdaWebError(
        f"The command can't safely deploy a new revision for Web Function "
        f"'{function_name}' because its environment variables aren't "
        f'readable. The service reported {code}: {message} Resolve the error '
        'and run the command again.'
    )


def _split_regions(value):
    if not value:
        return []
    return list(
        dict.fromkeys(r.strip() for r in value.split(',') if r.strip())
    )


def entrypoint_conflict_error():
    return InvalidArgumentValueError(
        'Use either --entry-point or the '
        f'{constants.ENTRYPOINT_ENV_VAR} environment variable, not both. '
        'Remove one of them and retry.'
    )


def verify_entrypoint_in_tree(source_dir, value):
    """Warn (or error) if a customer-set entry-point file is not bundled.

    A missing in-tree file is a hard error. A value whose on-disk mapping
    cannot be resolved with certainty only warns.
    """
    rel = value[2:] if value.startswith('./') else value
    uncertain = (
        os.path.isabs(rel)
        or rel.startswith('/')
        or '..' in rel.replace('\\', '/').split('/')
        or '#' in rel
        or '?' in rel
        or rel != rel.strip()
    )
    local = os.path.join(source_dir, *rel.split('/'))
    if os.path.isfile(local):
        return
    message = (
        f"{constants.ENTRYPOINT_ENV_VAR} points at '{value}', but no such "
        f"file exists under --code '{source_dir}'. Include the file in the "
        'deployment package or specify a different entry point.'
    )
    if uncertain:
        output.progress(f'Warning: {message}')
        return
    raise InvalidSourceError(message)


def validate_reuse_code_args(parsed_args, norm):
    """Reject bundling-only flags on the reuse-code path.

    Nothing is bundled or uploaded, so they have nothing to act on and are
    rejected rather than silently ignored.
    """
    offenders = []
    if parsed_args.entry_point:
        offenders.append('--entry-point')
    if parsed_args.include_hidden_files:
        offenders.append('--include-hidden-files')
    if parsed_args.force_include:
        offenders.append('--force-include')
    if parsed_args.bucket_name:
        offenders.append('--bucket-name')
    if constants.ENTRYPOINT_ENV_VAR in norm.env:
        offenders.append(f'--env {constants.ENTRYPOINT_ENV_VAR}')
    if offenders:
        raise LambdaWebError(
            f'{", ".join(offenders)} requires --code. When you omit --code, '
            'the command reuses the deployed code and updates only the '
            'Web Function configuration.'
        )


def validate_hello_world_args(parsed_args):
    """Validate ``--hello-world`` before any write or network call.

    The scaffold provides its own entry point, and
    :func:`scaffold.write_hello_world` re-checks that the path does not exist
    or identifies an empty directory.
    """
    if parsed_args.entry_point:
        raise LambdaWebError(
            'Do not use --entry-point with --hello-world. The starter '
            'application includes an entry point.'
        )
    if parsed_args.force_include:
        raise LambdaWebError(
            'Do not use --force-include with --hello-world. '
            '--force-include requires an existing file under --code. '
            '--hello-world accepts a path that does not exist or identifies '
            'an existing empty directory.'
        )
    if (
        parsed_args.runtime
        and parsed_args.runtime != constants.DEFAULT_RUNTIME
    ):
        raise LambdaWebError(
            f'--hello-world uses the {constants.DEFAULT_RUNTIME} runtime. '
            f'Remove --runtime, or set --runtime to '
            f'{constants.DEFAULT_RUNTIME}.'
        )
    if not scaffold.is_empty_dir(parsed_args.code):
        raise InvalidSourceError(
            '--hello-world requires a --code path that does not exist or '
            f"identifies an existing empty directory, but '{parsed_args.code}' "
            'contains files. The command does not overwrite files. Specify a '
            'different --code directory, or remove '
            '--hello-world to deploy the existing code.'
        )


def validate_bounded_args(session, parsed_args, norm):
    """Range-check integer and region args against the service model.

    The model is the source of truth for the bounds, and checking here
    runs before any resource is created.
    """
    for attr, (flag, shape) in args.INT_ARG_VALIDATION.items():
        validate_int_in_model_range(
            session,
            flag,
            shape,
            getattr(parsed_args, attr),
        )
    # --activation-timeout is a CLI-only poll timeout with no model shape,
    # and a non-positive value would put the deadline in the past.
    if (
        parsed_args.activation_timeout is not None
        and parsed_args.activation_timeout <= 0
    ):
        raise InvalidArgumentValueError(
            '--activation-timeout must be a positive number of seconds: '
            f'got {parsed_args.activation_timeout}. To return immediately '
            'without waiting for activation, use --no-wait.'
        )
    # --progress-frequency is likewise CLI-only.
    if (
        parsed_args.progress_frequency is not None
        and parsed_args.progress_frequency <= 0
    ):
        raise InvalidArgumentValueError(
            '--progress-frequency must be a positive number of seconds: '
            f'got {parsed_args.progress_frequency}.'
        )
    if parsed_args.regions:
        validate_regions_against_model(session, '--regions', norm.regions)


def reject_update_only_args(parsed_args, norm):
    """Raise if an update-only arg was supplied on the create path.

    ``--unset-env`` removes an inherited variable, and there is nothing to
    inherit on create, so ignoring it would hide a user mistake.
    """
    if norm.unset_env:
        raise InvalidArgumentValueError(
            '--unset-env can be used only when updating an existing Web '
            f"Function. Web Function '{parsed_args.name}' doesn't exist. To set "
            'environment variables when you create it, use --env.'
        )


def validate_create_endpoint_args(parsed_args, norm, current_region):
    """Validate endpoint-shape invariants before any resource is created.

    The service applies different AWS Region rules to ``HomeRegion`` and
    multi-Region endpoint types. Validate them before creating resources.
    """
    endpoint_type = (
        parsed_args.endpoint_type or constants.DEFAULT_ENDPOINT_TYPE
    )
    regions = norm.regions
    if endpoint_type in constants.REGION_REQUIRED_ENDPOINT_TYPES:
        if not regions:
            raise LambdaWebError(
                f'--regions is required when --endpoint-type is '
                f'{endpoint_type}.'
            )
        if all(region == current_region for region in regions):
            raise LambdaWebError(
                '--regions must include at least one AWS Region other than '
                f"the home Region '{current_region}' when --endpoint-type is "
                f'{endpoint_type}.'
            )
    elif any(region != current_region for region in regions):
        raise LambdaWebError(
            f"--regions can include only the home Region '{current_region}' "
            f'when --endpoint-type is {endpoint_type}.'
        )

    # MultiRegion and PerRegion endpoints always serve pinned revisions.
    mode = parsed_args.auto_deployment_mode
    if (
        endpoint_type in constants.REGION_REQUIRED_ENDPOINT_TYPES
        and mode is not None
        and mode != constants.DISABLED_AUTO_DEPLOYMENT_MODE
    ):
        raise LambdaWebError(
            f'--auto-deployment-mode {mode} is supported only for a '
            f'{constants.DEFAULT_ENDPOINT_TYPE} endpoint. For endpoint type '
            f'{endpoint_type}, omit --auto-deployment-mode. The command uses '
            f'{constants.DISABLED_AUTO_DEPLOYMENT_MODE}.'
        )


def validate_endpoint_plan_args(parsed_args, norm, current_region, plan):
    """Validate the endpoint-shape args against the resolved plan.

    Runs before any mutation so a bad combination fails fast rather than
    after the revision is deployed.
    """
    if plan.action is EndpointAction.ADD:
        validate_create_endpoint_args(parsed_args, norm, current_region)
    elif plan.action is EndpointAction.UPDATE:
        reject_non_active_endpoint(plan.target)
        reject_immutable_endpoint_args(parsed_args, norm, plan.target)
        reject_incompatible_mode_for_type(parsed_args, plan.target)
    elif plan.action is EndpointAction.NONE:
        reject_endpoint_create_args(parsed_args)


def reject_non_active_endpoint(target):
    """Reject up front if the target endpoint is not in ``Active`` state.

    The service requires an Active endpoint to accept an update, and would
    otherwise reject it only after the revision was deployed. A state
    change after this probe still surfaces the service's own error.
    """
    state = target.get('state')
    if state and state != 'Active':
        raise LambdaWebError(
            f"Endpoint '{target.get('endpointName')}' is in the {state} "
            'state. Wait until the endpoint is Active, and then run the '
            'command again.'
        )


def reject_incompatible_mode_for_type(parsed_args, target):
    """Reject --auto-deployment-mode illegal for the endpoint's fixed type.

    ``LatestRevision`` is only legal for a ``HomeRegion`` endpoint, and the
    type cannot change on update, so the service would otherwise reject the
    conflict only after the revision was deployed.
    """
    mode = parsed_args.auto_deployment_mode
    if mode is None:
        return
    endpoint_type = target.get('endpointType')
    if (
        endpoint_type in constants.REGION_REQUIRED_ENDPOINT_TYPES
        and mode != constants.DISABLED_AUTO_DEPLOYMENT_MODE
    ):
        raise LambdaWebError(
            '--auto-deployment-mode must be '
            f'{constants.DISABLED_AUTO_DEPLOYMENT_MODE} for {endpoint_type} '
            f"endpoint '{target.get('endpointName')}'. {mode} is supported "
            'only for a HomeRegion endpoint.'
        )


def reject_immutable_endpoint_args(parsed_args, norm, target):
    """Raise if an immutable endpoint arg differs from the live endpoint.

    ``endpointType`` and ``regions`` are not members of
    ``UpdateWebFunctionEndpointRequest``. A matching value is a harmless
    no-op; a differing one is rejected.
    """
    conflicts = []
    requested_settings = []
    if parsed_args.endpoint_type and parsed_args.endpoint_type != target.get(
        'endpointType'
    ):
        conflicts.append(
            f"--endpoint-type (endpoint is '{target.get('endpointType')}')"
        )
        requested_settings.append('endpoint type')
    if parsed_args.regions and set(norm.regions) != set(
        target.get('regions') or []
    ):
        current = ','.join(target.get('regions') or [])
        conflicts.append(f"--regions (endpoint is '{current}')")
        requested_settings.append('AWS Regions')
    if not conflicts:
        return
    settings = ' and '.join(requested_settings)
    raise LambdaWebError(
        f"The following settings can't be changed for endpoint "
        f"'{target.get('endpointName')}': {', '.join(conflicts)}. The existing "
        f"endpoint wasn't changed. To use the {settings} you specified, create "
        'a new endpoint with a different name. If the existing endpoint is no '
        'longer in use and you need to reuse its name, delete it before '
        'creating the replacement.'
    )


def reject_endpoint_create_args(parsed_args):
    """Raise if endpoint-create args were given with no endpoint to create.

    Reached when the Web Function exists, has no endpoints, and none was named.
    """
    provided = [
        flag
        for attr, flag in args.ENDPOINT_CREATE_ARGS
        if getattr(parsed_args, attr, None) is not None
    ]
    if not provided:
        return
    raise LambdaWebError(
        f"Web Function '{parsed_args.name}' has no endpoint. Specify "
        f'--endpoint-name to create one before using {", ".join(provided)}.'
    )
