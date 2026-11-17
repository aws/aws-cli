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
import copy
import os
import signal
import sys
import time
from pathlib import PureWindowsPath

from botocore.exceptions import BotoCoreError, ClientError

from awscli.compat import compat_input
from awscli.constants import GENERAL_ERROR_RC, PARAM_VALIDATION_ERROR_RC
from awscli.customizations.commands import BasicCommand
from awscli.customizations.lambdaweb import (
    args,
    bucket,
    bundle,
    constants,
    model,
    output,
    requests,
    role,
    scaffold,
    validation,
    wait,
)
from awscli.customizations.lambdaweb.endpoint_plan import (
    EndpointAction,
    is_endpoint_update_conflict,
    resolve_endpoint_plan,
)
from awscli.customizations.lambdaweb.exceptions import (
    ActivationFailedError,
    ActivationTimeoutError,
    ArgumentValidationError,
    BundleTooLargeError,
    IncompleteWebFunctionRevisionError,
    InvalidSourceError,
    LambdaWebError,
    NoRegionError,
)
from awscli.customizations.lambdaweb.utils import (
    create_nested_client,
    get_partition_for_region,
    is_tty,
    parse_kv,
)


class LambdaWebDeploy(BasicCommand):
    NAME = 'deploy'
    DESCRIPTION = args.DESCRIPTION
    # examples live in awscli/examples/lambda-web/deploy.rst, loaded by the
    # ``addexamples`` doc customization.
    EXAMPLES = ''

    ARG_TABLE = args.ARG_TABLE

    def _build_arg_table(self):
        self.ARG_TABLE = copy.deepcopy(self.__class__.ARG_TABLE)
        for arg_data in self.ARG_TABLE:
            shape_name = model.ENUM_ARG_SHAPES.get(arg_data['name'])
            if shape_name is not None:
                choices = model.enum_choices(self._session, shape_name)
                arg_data['choices'] = choices
                arg_data['schema'] = {'type': 'string', 'enum': choices}
        arg_table = super()._build_arg_table()
        for name in args.APPEND_ARGS:
            if name in arg_table:
                arg_table[name].argument_model = None
        return arg_table

    def _run_main(self, parsed_args, parsed_globals):
        try:
            return self._run_pipeline(parsed_args, parsed_globals)
        except LambdaWebError as e:
            output.emit_error(str(e), parsed_globals)
            # the param-validation code lets --cli-auto-prompt re-prompt for
            # the bad argument, as it would for a modeled command.
            if isinstance(e, ArgumentValidationError):
                return PARAM_VALIDATION_ERROR_RC
            return GENERAL_ERROR_RC
        except KeyboardInterrupt:
            # the context message was already emitted where the interrupt
            # fired, so say nothing more here and risk contradicting it.
            return 128 + signal.SIGINT

    def _run_pipeline(self, parsed_args, parsed_globals):
        bundle.validate_function_name(parsed_args.name)
        self._resolve_code_dir(parsed_args)
        # omitting --code deploys a revision that reuses the existing
        # function's code with only config changes.
        reuse_code = not parsed_args.code and not parsed_args.hello_world
        # these two gates run before the args are normalized because they
        # reject the source directory itself, which is the earlier complaint.
        if parsed_args.hello_world:
            validation.validate_hello_world_args(parsed_args)
        elif not reuse_code and not os.path.isdir(parsed_args.code):
            raise InvalidSourceError(
                f"--code '{parsed_args.code}' must be a directory that "
                'contains the Web Function source code. To deploy a prebuilt '
                ".zip file, use 'aws lambda-web create-web-function' or "
                "'aws lambda-web create-web-function-revision'. To create a "
                'starter application, use --hello-world.'
            )

        norm = validation.normalize_args(self._session, parsed_args)
        if reuse_code:
            validation.validate_reuse_code_args(parsed_args, norm)
        # two different ways to select the entry point; the inherited-value
        # case is caught later in _customer_entrypoint.
        if (
            parsed_args.entry_point
            and constants.ENTRYPOINT_ENV_VAR in norm.env
        ):
            raise validation.entrypoint_conflict_error()
        # Tag values can be empty, so parse them separately from --env.
        tags = parse_kv(parsed_args.tags, label='--tags')
        validation.validate_bounded_args(self._session, parsed_args, norm)
        region = parsed_globals.region or self._session.get_config_variable(
            'region'
        )
        if not region:
            raise NoRegionError(
                'You must specify an AWS Region. Pass --region, set '
                'AWS_DEFAULT_REGION, or configure a default region with '
                "'aws configure'."
            )
        partition = get_partition_for_region(self._session, region)
        verify = parsed_globals.verify_ssl

        sts = create_nested_client(
            self._session,
            'sts',
            region_name=region,
            verify=verify,
        )
        s3 = create_nested_client(
            self._session,
            's3',
            region_name=region,
            verify=verify,
        )
        lambda_web = create_nested_client(
            self._session,
            'lambda-web',
            region_name=region,
            verify=verify,
            endpoint_url=parsed_globals.endpoint_url,
        )

        try:
            account_id = sts.get_caller_identity()['Account']
        except (BotoCoreError, ClientError) as e:
            raise LambdaWebError(
                'Unable to retrieve the AWS account ID with AWS Security '
                'Token Service (AWS STS) GetCallerIdentity. Verify your '
                'credentials and sts:GetCallerIdentity permission.'
            ) from e

        creating = self._probe_is_create(lambda_web, parsed_args.name)

        # Complete local work and bucket validation before provisioning the
        # execution role. Upload only after the role is ready.
        if parsed_args.hello_world and not creating:
            raise LambdaWebError(
                f"Web Function '{parsed_args.name}' already exists. "
                '--hello-world creates a starter application for a new Web '
                'Function. Remove --hello-world to deploy existing code, or '
                'specify a new --name.'
            )
        if reuse_code and creating:
            raise LambdaWebError(
                f"Web Function '{parsed_args.name}' doesn't exist. Specify "
                '--code to create it, or use --hello-world to create a starter '
                'application. Omit --code only when you update configuration '
                'for an existing Web Function.'
            )
        if creating:
            validation.reject_update_only_args(parsed_args, norm)
            validation.validate_create_endpoint_args(parsed_args, norm, region)
            if parsed_args.hello_world:
                # --hello-world is itself the create opt-in, so it needs no
                # separate confirmation.
                output.progress(
                    f'Creating starter application in {parsed_args.code} ...'
                )
                scaffold.write_hello_world(parsed_args.code, parsed_args.name)
            else:
                self._confirm_create(parsed_args, region)
            existing = None
            endpoint_plan = None
        else:
            existing = requests.resolve_latest_revision(
                lambda_web, parsed_args.name
            )
            validation.reject_unreadable_environment(
                parsed_args.name, existing
            )
            # resolve and gate the endpoint before any mutation, so an invalid
            # endpoint request fails without deploying a revision first.
            endpoint_plan = resolve_endpoint_plan(lambda_web, parsed_args)
            validation.validate_endpoint_plan_args(
                parsed_args, norm, region, endpoint_plan
            )
            if endpoint_plan.action is EndpointAction.ADD:
                self._confirm_create_endpoint(parsed_args)

        if reuse_code:
            s3_obj = self._reuse_existing_s3_object(parsed_args, existing)
            bucket_resolved = s3_obj['bucket']
            output.progress(
                'Reusing deployed code from '
                f"s3://{s3_obj['bucket']}/{s3_obj['key']}. No deployment "
                'package was uploaded.'
            )
        else:
            # when the customer sets AWS_LAMBDA_NODEJS_ENTRYPOINT the runtime
            # loads that file instead of index.js, so defer to it and inject
            # no wrapper; only check that the named file is in the bundle.
            customer_entrypoint = self._customer_entrypoint(
                parsed_args, norm, existing
            )
            if customer_entrypoint is not None:
                validation.verify_entrypoint_in_tree(
                    parsed_args.code, customer_entrypoint
                )
                output.progress(
                    f"Using entry point '{customer_entrypoint}' from "
                    f'{constants.ENTRYPOINT_ENV_VAR}.'
                )
                # ``entry=None`` tells build_zip to skip wrapper injection.
                entry = None
            else:
                entry = bundle.resolve_entry_point(
                    parsed_args.code,
                    parsed_args.entry_point,
                )
            output.progress('Creating deployment package ...')
            zip_path, size = bundle.build_zip(
                parsed_args.code,
                entry,
                exclude_patterns=constants.DEFAULT_EXCLUDE_PATTERNS,
                include_hidden=parsed_args.include_hidden_files,
                force_include=parsed_args.force_include,
            )

        try:
            if not reuse_code:
                if size > constants.BUNDLE_SIZE_MAX_BYTES:
                    raise BundleTooLargeError(
                        f'The deployment package is {size} bytes and exceeds '
                        'the 512 MB limit. Remove unused dependencies or '
                        'development files from the code directory.'
                    )
                output.progress('Preparing Amazon S3 bucket ...')
                bucket_resolved = bucket.ensure_bucket(
                    s3,
                    account_id,
                    region,
                    partition,
                    override_name=parsed_args.bucket_name,
                )

            if creating:
                role_arn = self._ensure_create_role(
                    parsed_args,
                    region,
                    verify,
                )
            else:
                role_arn = self._resolve_update_role(
                    parsed_args,
                    region,
                    verify,
                    existing,
                )

            if not reuse_code:
                output.progress('Uploading deployment package ...')
                s3_obj = bucket.upload_zip(
                    s3,
                    bucket_resolved,
                    parsed_args.name,
                    zip_path,
                )
        finally:
            if not reuse_code:
                bundle.remove_bundle(zip_path)

        if creating:
            return self._run_create(
                parsed_args,
                parsed_globals,
                norm,
                tags,
                region,
                partition,
                lambda_web,
                s3_obj,
                bucket_resolved,
                role_arn,
            )
        return self._run_update(
            parsed_args,
            parsed_globals,
            norm,
            tags,
            region,
            partition,
            lambda_web,
            s3_obj,
            bucket_resolved,
            role_arn,
            existing,
            endpoint_plan,
            package_uploaded=not reuse_code,
        )

    def _customer_entrypoint(self, parsed_args, norm, existing):
        """Return the effective customer-set entry-point value, or ``None``.

        Honored from ``--env`` or inherited from the prior revision. The CLI
        never sets the variable itself, it only defers to it.
        """
        value = norm.env.get(constants.ENTRYPOINT_ENV_VAR)
        if value is None and existing is not None:
            inherited = (existing.get('serviceConfig') or {}).get(
                'environmentVariables'
            ) or {}
            # An explicit --unset-env of the key means the customer is taking
            # it back off, so do not treat the inherited value as active.
            if constants.ENTRYPOINT_ENV_VAR not in norm.unset_env:
                value = inherited.get(constants.ENTRYPOINT_ENV_VAR)
        if value is None:
            return None
        if parsed_args.entry_point:
            raise validation.entrypoint_conflict_error()
        value = PureWindowsPath(value).as_posix()
        norm.env[constants.ENTRYPOINT_ENV_VAR] = value
        return value

    def _resolve_code_dir(self, parsed_args):
        """Default ``--code`` to ``./<name>`` for ``--hello-world``."""
        if not parsed_args.code and parsed_args.hello_world:
            parsed_args.code = os.path.join('.', parsed_args.name)

    def _reuse_existing_s3_object(self, parsed_args, existing):
        """Return the prior revision's S3 object to reuse."""
        build = existing.get('buildConfig') or {}
        s3 = (build.get('codeConfig') or {}).get('s3Object') or {}
        if not s3.get('bucket') or not s3.get('key'):
            raise IncompleteWebFunctionRevisionError(
                f"The latest revision for '{parsed_args.name}' doesn't "
                'include an Amazon S3 code location. Specify --code to '
                'upload a deployment package.'
            )
        return {
            'bucket': s3['bucket'],
            'key': s3['key'],
            'versionId': s3.get('versionId'),
        }

    def _probe_is_create(self, lambda_web, function_name):
        """Return True when the Web Function does not exist yet (create path).

        ``--create`` only controls the confirmation gate, not the path.
        """
        try:
            lambda_web.get_web_function(functionName=function_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return True
            raise
        return False

    def _confirm_create(self, parsed_args, region):
        """Gate creation of a not-yet-existing Web Function."""
        self._confirm_or_refuse(
            create_flag=getattr(parsed_args, constants.CONFIRM_CREATE_ARG),
            prompt=(
                f"Web Function '{parsed_args.name}' doesn't exist in AWS "
                f"Region '{region}'. Creating it also creates an endpoint. It "
                'can also create an AWS IAM execution role and an Amazon S3 '
                'bucket. Press Enter to continue, or press Ctrl+C to cancel.\n'
            ),
            refuse_message=(
                f"Web Function '{parsed_args.name}' doesn't exist in AWS "
                f"Region '{region}'. Creating the Web Function also creates "
                'an endpoint and can create an AWS IAM execution role and an '
                'Amazon S3 bucket. '
                f'Run the command again with {constants.CONFIRM_CREATE_FLAG} '
                'to confirm resource creation, or verify --name and --region.'
            ),
        )

    def _confirm_create_endpoint(self, parsed_args):
        """Gate adding an endpoint to an existing Web Function.

        Mirrors :meth:`_confirm_create`, and runs during up-front validation so
        a Ctrl-C here has created nothing.
        """
        self._confirm_or_refuse(
            create_flag=getattr(parsed_args, constants.CONFIRM_CREATE_ARG),
            prompt=(
                f"Endpoint '{parsed_args.endpoint_name}' doesn't exist for "
                f"Web Function '{parsed_args.name}'. Press Enter to create "
                'it, or press Ctrl+C to cancel.\n'
            ),
            refuse_message=(
                f"Endpoint '{parsed_args.endpoint_name}' doesn't exist for "
                f"Web Function '{parsed_args.name}'. Run the command again "
                f'with {constants.CONFIRM_CREATE_FLAG} to create it, or '
                'verify --endpoint-name.'
            ),
        )

    def _confirm_or_refuse(self, *, create_flag, prompt, refuse_message):
        """Shared create-gate: --create, else TTY ENTER, else refuse.

        Prompts on stderr so stdout stays machine-clean.
        """
        if create_flag:
            return
        if self._stdin_is_tty():
            sys.stderr.write(prompt)
            sys.stderr.flush()
            try:
                compat_input('')
            except KeyboardInterrupt:
                output.progress('Cancelled; no resources were created.')
                raise
            except EOFError as e:
                raise LambdaWebError(
                    'Confirmation input ended; no resources were created. '
                    f'Specify {constants.CONFIRM_CREATE_FLAG} to continue '
                    'without a prompt.'
                ) from e
            return
        raise LambdaWebError(refuse_message)

    @staticmethod
    def _stdin_is_tty():
        return is_tty(sys.stdin)

    def _ensure_create_role(self, parsed_args, region, verify):
        """Create / verify the execution role for the create path."""
        iam = create_nested_client(
            self._session,
            'iam',
            region_name=region,
            verify=verify,
        )
        output.progress('Preparing AWS IAM execution role ...')
        return role.ensure_role(
            iam,
            parsed_args.name,
            override_arn=parsed_args.execution_role_arn,
        )

    def _resolve_update_role(self, parsed_args, region, verify, existing):
        """Resolve the role for the update path.

        With an explicit ``--execution-role-arn`` the iam client is built
        and the role verified; otherwise the latest revision's role is
        reused with zero IAM calls.
        """
        if parsed_args.execution_role_arn:
            iam = create_nested_client(
                self._session,
                'iam',
                region_name=region,
                verify=verify,
            )
            return role.ensure_role(
                iam,
                parsed_args.name,
                override_arn=parsed_args.execution_role_arn,
            )
        existing_service = existing.get('serviceConfig') or {}
        role_arn = existing_service.get('executionRoleArn')
        if not role_arn:
            raise IncompleteWebFunctionRevisionError(
                f"The latest revision for '{parsed_args.name}' doesn't "
                'include an execution role. Specify --execution-role-arn.'
            )
        return role_arn

    def _run_create(
        self,
        parsed_args,
        parsed_globals,
        norm,
        tags,
        region,
        partition,
        lambda_web,
        s3_obj,
        bucket_resolved,
        role_arn,
    ):
        request = requests.build_create_request(
            parsed_args,
            norm,
            tags,
            role_arn,
            s3_obj,
            region,
        )
        output.progress('Creating Lambda Web Function ...')
        try:
            response = role.wait_for_iam_propagation(
                lambda: lambda_web.create_web_function(**request)
            )
        except Exception:
            self._report_retained_package(s3_obj)
            raise
        function_arn = response['functionArn']

        console = output.console_url(partition, region, parsed_args.name)
        if parsed_args.no_wait:
            self._emit(
                parsed_globals,
                {
                    'functionArn': function_arn,
                    'endpointUrl': '',
                    'roleArn': role_arn,
                    'bucketName': bucket_resolved,
                    'objectKey': s3_obj['key'],
                    'consoleUrl': console,
                },
                console,
            )
            return 0

        endpoint_name = (
            parsed_args.endpoint_name or constants.DEFAULT_ENDPOINT_NAME
        )
        timeout = parsed_args.activation_timeout
        output.progress(
            f'Waiting for endpoint to become active (timeout {timeout}s) ...'
        )
        endpoint = wait.wait_for_endpoint_active(
            lambda_web,
            parsed_args.name,
            endpoint_name,
            timeout_seconds=timeout,
            poll_interval_seconds=constants.DEFAULT_POLL_INTERVAL_SECONDS,
            progress_frequency_seconds=parsed_args.progress_frequency,
        )

        output.report_regional_urls(endpoint)
        self._emit(
            parsed_globals,
            {
                'functionArn': function_arn,
                **output.endpoint_url_fields(endpoint),
                'roleArn': role_arn,
                'bucketName': bucket_resolved,
                'objectKey': s3_obj['key'],
                'consoleUrl': console,
            },
            console,
        )
        return 0

    def _run_update(
        self,
        parsed_args,
        parsed_globals,
        norm,
        tags,
        region,
        partition,
        lambda_web,
        s3_obj,
        bucket_resolved,
        role_arn,
        existing,
        endpoint_plan,
        *,
        package_uploaded,
    ):
        request = requests.build_revision_request(
            self._session,
            parsed_args,
            norm,
            role_arn,
            s3_obj,
            existing,
        )
        output.progress('Creating Web Function revision ...')
        try:
            revision = lambda_web.create_web_function_revision(**request)
        except (BotoCoreError, ClientError):
            if package_uploaded:
                self._report_retained_package(s3_obj)
            raise
        revision_id = revision['revisionId']
        revision_arn = revision['revisionArn']
        function_arn = revision['functionArn']
        self._update_web_function_tags(
            lambda_web,
            parsed_args,
            function_arn,
            revision_id,
            tags,
        )

        console = output.console_url(partition, region, parsed_args.name)
        result = {
            'functionArn': function_arn,
            'endpointUrl': '',
            'roleArn': role_arn,
            'bucketName': bucket_resolved,
            'objectKey': s3_obj['key'],
            'revisionId': revision_id,
            'revisionArn': revision_arn,
            'consoleUrl': console,
        }
        timeout = parsed_args.activation_timeout
        endpoint_submission_required = self._endpoint_submission_required(
            parsed_args, endpoint_plan, revision_id
        )
        revision_active = (
            not parsed_args.no_wait or endpoint_submission_required
        )
        if revision_active:
            if parsed_args.no_wait:
                output.progress(
                    f'Waiting for revision {revision_id} to become Active '
                    'before submitting endpoint changes '
                    f'(timeout {timeout}s) ...'
                )
            else:
                output.progress(
                    f'Waiting for revision {revision_id} to become active '
                    f'(timeout {timeout}s) ...'
                )
            try:
                wait.wait_for_revision_active(
                    lambda_web,
                    parsed_args.name,
                    revision_id,
                    timeout_seconds=timeout,
                    poll_interval_seconds=(
                        constants.DEFAULT_POLL_INTERVAL_SECONDS
                    ),
                    progress_frequency_seconds=(
                        parsed_args.progress_frequency
                    ),
                )
            except (ActivationFailedError, ActivationTimeoutError) as e:
                if not parsed_args.no_wait:
                    raise
                endpoint_name = (
                    parsed_args.endpoint_name
                    if endpoint_plan.action is EndpointAction.ADD
                    else endpoint_plan.target['endpointName']
                )
                action = (
                    'creation'
                    if endpoint_plan.action is EndpointAction.ADD
                    else 'update'
                )
                past_tense = (
                    'created'
                    if endpoint_plan.action is EndpointAction.ADD
                    else 'updated'
                )
                if isinstance(e, ActivationTimeoutError):
                    recovery = (
                        'Check the revision status with the command shown '
                        'above. After it becomes Active, run the same deploy '
                        f'command again to retry the endpoint {action}.'
                    )
                else:
                    recovery = (
                        'Resolve the revision failure, then run the same '
                        f'deploy command again to retry the endpoint {action}.'
                    )
                raise type(e)(
                    f"{e} Endpoint '{endpoint_name}' was not {past_tense}. "
                    f'{recovery}'
                ) from e

        endpoint = self._apply_endpoint_plan(
            lambda_web,
            parsed_args,
            norm,
            region,
            endpoint_plan,
            revision_id,
            timeout,
            wait_for_endpoint=not parsed_args.no_wait,
            revision_active=revision_active,
        )
        if not parsed_args.no_wait:
            output.report_regional_urls(endpoint)
            result.update(output.endpoint_url_fields(endpoint))
        self._emit(parsed_globals, result, console)
        return 0

    @staticmethod
    def _update_web_function_tags(
        lambda_web,
        parsed_args,
        function_arn,
        revision_id,
        tags,
    ):
        if not tags:
            return
        output.progress('Updating Web Function tags ...')
        try:
            lambda_web.tag_resource(resource=function_arn, tags=tags)
        except (BotoCoreError, ClientError) as e:
            warning = (
                f"Warning: Revision {revision_id} was created, but the command "
                f"couldn't confirm whether tags for Web Function "
                f"'{parsed_args.name}' were updated."
            )
            if isinstance(e, ClientError):
                error = e.response.get('Error', {})
                details = ': '.join(
                    value
                    for value in (
                        error.get('Code'),
                        ' '.join((error.get('Message') or '').split()),
                    )
                    if value
                )
                if details:
                    warning += f" AWS error: {details.rstrip('.')}."
            warning += (
                " Run 'aws lambda-web tag-resource' to verify or retry the "
                'tags.'
            )
            output.progress(warning)

    @staticmethod
    def _report_retained_package(s3_obj):
        location = f"s3://{s3_obj['bucket']}/{s3_obj['key']}"
        version_id = s3_obj.get('versionId')
        if version_id:
            location += f' (version ID: {version_id})'
        output.progress(
            f'The deployment package remains in Amazon S3: {location}'
        )

    @staticmethod
    def _emit(parsed_globals, result, console):
        output.emit_result(parsed_globals, result)
        output.emit_console_hint(parsed_globals, console)

    @staticmethod
    def _endpoint_submission_required(parsed_args, endpoint_plan, revision_id):
        """Return True when deploy must submit an endpoint request."""
        if endpoint_plan.action is EndpointAction.ADD:
            return True
        if endpoint_plan.action is EndpointAction.UPDATE:
            request, _ = requests.build_update_endpoint_request(
                parsed_args, endpoint_plan.target, revision_id
            )
            return request is not None
        return False

    def _apply_endpoint_plan(
        self,
        lambda_web,
        parsed_args,
        norm,
        region,
        endpoint_plan,
        revision_id,
        timeout,
        *,
        wait_for_endpoint,
        revision_active,
    ):
        """Execute the endpoint plan and optionally wait for activation."""
        if endpoint_plan.action is EndpointAction.NONE:
            revision_status = 'is Active' if revision_active else 'was created'
            output.progress(
                f"Revision {revision_id} {revision_status}, but Web Function "
                f"'{parsed_args.name}' has no endpoint. Run the command again "
                'with --endpoint-name NAME, or create one with '
                "'aws lambda-web create-web-function-endpoint'."
            )
            return None
        if endpoint_plan.action is EndpointAction.ADD:
            return self._add_endpoint(
                lambda_web,
                parsed_args,
                norm,
                region,
                revision_id,
                timeout,
                wait_for_endpoint,
            )
        return self._update_endpoint(
            lambda_web,
            parsed_args,
            endpoint_plan.target,
            revision_id,
            timeout,
            wait_for_endpoint,
        )

    def _add_endpoint(
        self,
        lambda_web,
        parsed_args,
        norm,
        region,
        revision_id,
        timeout,
        wait_for_endpoint,
    ):
        """Create the named endpoint and optionally wait for activation."""
        endpoint_name = parsed_args.endpoint_name
        request = requests.build_create_endpoint_request(
            parsed_args, norm, region, revision_id
        )
        output.progress(f"Creating endpoint '{endpoint_name}' ...")
        try:
            endpoint = lambda_web.create_web_function_endpoint(**request)
        except (BotoCoreError, ClientError):
            output.progress(
                f"Revision {revision_id} is Active, but endpoint "
                f"'{endpoint_name}' was not created. Resolve the reported "
                'error, then run the same deploy command again.'
            )
            raise
        if not wait_for_endpoint:
            return endpoint
        return self._wait_endpoint_active(
            lambda_web, parsed_args, endpoint_name, timeout
        )

    def _update_endpoint(
        self,
        lambda_web,
        parsed_args,
        target,
        revision_id,
        timeout,
        wait_for_endpoint,
    ):
        """Point / reconfigure an existing endpoint for the new revision."""
        endpoint_name = target['endpointName']
        request, note = requests.build_update_endpoint_request(
            parsed_args, target, revision_id
        )
        if request is None:
            # two distinct no-op cases: ``note`` is set only for a preserved
            # traffic split, so it tells them apart.
            if note:
                output.progress(note)
            else:
                if wait_for_endpoint:
                    message = (
                        f"Endpoint '{endpoint_name}' auto-deploys the latest "
                        'revision and will serve the new revision after it '
                        'becomes Active.'
                    )
                else:
                    message = (
                        f"With --no-wait, endpoint '{endpoint_name}' "
                        'automatically serves the new revision after it '
                        'becomes Active.'
                    )
                output.progress(message)
            if not wait_for_endpoint:
                return target
            return self._wait_endpoint_active(
                lambda_web, parsed_args, endpoint_name, timeout
            )
        if note:
            output.progress(note)
        output.progress(f"Updating endpoint '{endpoint_name}' ...")
        try:
            endpoint = self._update_endpoint_call(
                lambda_web, parsed_args, target, revision_id, request
            )
        except (BotoCoreError, ClientError):
            output.progress(
                f'Revision {revision_id} is Active, but the endpoint update '
                f"returned an error. Endpoint '{endpoint_name}' might have "
                'been partially updated. Check its current configuration with '
                "'aws lambda-web get-web-function-endpoint "
                f'--function-name {parsed_args.name} '
                f"--endpoint-name {endpoint_name}' before retrying the deploy."
            )
            raise
        if not wait_for_endpoint:
            return endpoint
        return self._wait_endpoint_updated(
            lambda_web, parsed_args, endpoint_name, timeout
        )

    def _update_endpoint_call(
        self, lambda_web, parsed_args, target, revision_id, request
    ):
        """Call ``update_web_function_endpoint``, retrying a lost race.

        The update uses optimistic concurrency, and the repoint is idempotent
        in intent, so a lost race is retried against freshly read state. Any
        other error surfaces immediately.
        """
        retries = constants.ENDPOINT_UPDATE_CONFLICT_RETRIES
        sleep_seconds = constants.ENDPOINT_UPDATE_CONFLICT_SLEEP_SECONDS
        endpoint_name = target['endpointName']
        for attempt in range(retries):
            try:
                return lambda_web.update_web_function_endpoint(**request)
            except ClientError as e:
                if (
                    not is_endpoint_update_conflict(e)
                    or attempt == retries - 1
                ):
                    raise
                time.sleep(sleep_seconds)
                # the winning update may already have pinned our revision, in
                # which case the rebuilt request is empty.
                fresh = lambda_web.get_web_function_endpoint(
                    functionName=parsed_args.name, endpointName=endpoint_name
                )
                request, note = requests.build_update_endpoint_request(
                    parsed_args, fresh, revision_id
                )
                if note:
                    output.progress(note)
                if request is None:
                    return fresh
                output.progress(
                    f"Endpoint '{endpoint_name}' was updated concurrently; "
                    'retrying ...'
                )

    def _wait_endpoint_active(
        self, lambda_web, parsed_args, endpoint_name, timeout
    ):
        output.progress(
            f"Waiting for endpoint '{endpoint_name}' to become active "
            f'(timeout {timeout}s) ...'
        )
        return wait.wait_for_endpoint_active(
            lambda_web,
            parsed_args.name,
            endpoint_name,
            timeout_seconds=timeout,
            poll_interval_seconds=constants.DEFAULT_POLL_INTERVAL_SECONDS,
            progress_frequency_seconds=parsed_args.progress_frequency,
        )

    def _wait_endpoint_updated(
        self, lambda_web, parsed_args, endpoint_name, timeout
    ):
        output.progress(
            f"Waiting for endpoint '{endpoint_name}' update to complete "
            f'(timeout {timeout}s) ...'
        )
        return wait.wait_for_endpoint_updated(
            lambda_web,
            parsed_args.name,
            endpoint_name,
            timeout_seconds=timeout,
            poll_interval_seconds=constants.DEFAULT_POLL_INTERVAL_SECONDS,
            progress_frequency_seconds=parsed_args.progress_frequency,
        )
