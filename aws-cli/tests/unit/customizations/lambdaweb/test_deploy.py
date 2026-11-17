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
"""Unit tests for ``awscli.customizations.lambdaweb.deploy``."""

import copy
import io
import json
from unittest import mock

import botocore.session
import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.stub import Stubber

from awscli.customizations.lambdaweb import constants, deploy
from awscli.customizations.lambdaweb.deploy import LambdaWebDeploy
from awscli.customizations.lambdaweb.exceptions import ActivationTimeoutError

REGION = 'us-east-1'
FUNCTION_NAME = 'my-fn'
FUNCTION_ARN = f'arn:aws:lambda:{REGION}:111111111111:function:{FUNCTION_NAME}'
ROLE_ARN = 'arn:aws:iam::111111111111:role/customer-role'
BUCKET_NAME = 'customer-bucket'
ENDPOINT_NAME = 'dev'
TIMESTAMP = '2026-01-01T00:00:00Z'
S3_OBJECT = {
    'bucket': BUCKET_NAME,
    'key': f'lambda-web/{FUNCTION_NAME}/2026-key.zip',
    'versionId': 'vid-1',
}


_MODELED_INPUT_FIELDS = {
    'CreateWebFunctionRevision': {
        'description',
        'kmsKeyArn',
        'buildConfig',
        'serviceConfig',
    },
}


def _copy_projected_input(_session, operation_name, source):
    """Simulate fields already accepted by the operation input model.

    Recursive model projection is covered in ``test_model.py``.
    """
    allowed = _MODELED_INPUT_FIELDS[operation_name]
    return {
        key: copy.deepcopy(value)
        for key, value in source.items()
        if key in allowed or key.startswith('future')
    }


def _update_projected_input_member(
    _session, _operation_name, member_path, request, update
):
    *parents, leaf = member_path
    container = request
    for member_name in parents:
        container = container.setdefault(member_name, {})
    container[leaf] = copy.deepcopy(update(container.get(leaf)))


def _create_web_function_response(state='Pending'):
    return {
        'functionName': FUNCTION_NAME,
        'functionArn': FUNCTION_ARN,
        'state': state,
        'stateReason': 'Creating',
        'createdAt': TIMESTAMP,
        'updatedAt': TIMESTAMP,
    }


def _endpoint_response(
    state='Active',
    update_status=None,
    update_status_reason='ok',
):
    response = {
        'functionArn': FUNCTION_ARN,
        'endpointArn': f'{FUNCTION_ARN}:endpoint/{ENDPOINT_NAME}',
        'endpointName': ENDPOINT_NAME,
        'endpointType': 'HomeRegion',
        'domainName': 'abc123.lambda-url.us-east-1.on.aws',
        'authType': 'ApplicationManaged',
        'autoDeploymentMode': 'LatestRevision',
        'regions': [REGION],
        'state': state,
        'stateReason': 'ok',
        'createdAt': TIMESTAMP,
        'updatedAt': TIMESTAMP,
    }
    if update_status is not None:
        response['updateStatus'] = update_status
        response['updateStatusReason'] = update_status_reason
    return response


def _role_payload():
    return {
        'Role': {
            'Path': '/',
            'RoleName': 'customer-role',
            'RoleId': 'AROAEXAMPLEROLEIDXX',
            'Arn': ROLE_ARN,
            'CreateDate': TIMESTAMP,
        }
    }


class _FakeLambdaWebClient:
    """Stubber-style test double for the ``lambda-web`` client."""

    def __init__(self):
        self._queue = []
        self.calls = []

    def add_response(self, operation, response):
        self._queue.append((operation, response, None))

    def add_client_error(
        self,
        operation,
        service_error_code='',
        service_message='',
        http_status_code=400,
    ):
        error = ClientError(
            {
                'Error': {
                    'Code': service_error_code,
                    'Message': service_message,
                },
                'ResponseMetadata': {'HTTPStatusCode': http_status_code},
            },
            operation,
        )
        self._queue.append((operation, None, error))

    def assert_no_pending_responses(self):
        assert not self._queue, f'pending responses: {self._queue}'

    def create_web_function(self, **kwargs):
        return self._invoke('create_web_function', kwargs)

    def get_web_function(self, **kwargs):
        return self._invoke('get_web_function', kwargs)

    def get_web_function_endpoint(self, **kwargs):
        return self._invoke('get_web_function_endpoint', kwargs)

    def list_web_function_revisions(self, **kwargs):
        return self._invoke('list_web_function_revisions', kwargs)

    def get_web_function_revision(self, **kwargs):
        return self._invoke('get_web_function_revision', kwargs)

    def create_web_function_revision(self, **kwargs):
        return self._invoke('create_web_function_revision', kwargs)

    def list_web_function_endpoints(self, **kwargs):
        return self._invoke('list_web_function_endpoints', kwargs)

    def create_web_function_endpoint(self, **kwargs):
        return self._invoke('create_web_function_endpoint', kwargs)

    def update_web_function_endpoint(self, **kwargs):
        return self._invoke('update_web_function_endpoint', kwargs)

    def tag_resource(self, **kwargs):
        return self._invoke('tag_resource', kwargs)

    def _invoke(self, operation, kwargs):
        self.calls.append((operation, kwargs))
        assert self._queue, f'unexpected call to {operation}: {kwargs}'
        expected_op, response, error = self._queue.pop(0)
        assert (
            operation == expected_op
        ), f'expected call to {expected_op}, got {operation}'
        if error is not None:
            raise error
        return response


class _Harness:
    """Wires stubbed clients into the deploy module under test."""

    def __init__(self, region=REGION):
        self.session = botocore.session.get_session()
        self.partition = 'aws-cn' if region.startswith('cn-') else 'aws'
        self.region = region
        self.sts = self.session.create_client('sts', region_name=region)
        self.s3 = self.session.create_client('s3', region_name=region)
        self.iam = self.session.create_client('iam', region_name=region)
        self.lambda_web = _FakeLambdaWebClient()

        self.sts_stub = Stubber(self.sts)
        self.s3_stub = Stubber(self.s3)
        self.iam_stub = Stubber(self.iam)
        self._patches = []

    def install(self):
        def fake_create_nested_client(session, service_name, **kwargs):
            if service_name == 'sts':
                return self.sts
            if service_name == 's3':
                return self.s3
            if service_name == 'iam':
                return self.iam
            if service_name == 'lambda-web':
                return self.lambda_web
            raise AssertionError(f'unexpected service_name: {service_name}')

        self._patches.append(
            mock.patch.object(
                deploy,
                'create_nested_client',
                side_effect=fake_create_nested_client,
            )
        )
        self._patches.append(
            mock.patch.object(
                deploy,
                'get_partition_for_region',
                return_value=self.partition,
            )
        )
        self._patches.append(
            mock.patch.object(
                deploy.requests.model,
                'copy_input_fields',
                side_effect=_copy_projected_input,
            )
        )
        self._patches.append(
            mock.patch.object(
                deploy.requests.model,
                'update_input_member',
                side_effect=_update_projected_input_member,
            )
        )
        for patcher in self._patches:
            patcher.start()
        self.sts_stub.activate()
        self.s3_stub.activate()
        self.iam_stub.activate()

    def uninstall(self):
        self.sts_stub.deactivate()
        self.s3_stub.deactivate()
        self.iam_stub.deactivate()
        for patcher in self._patches:
            patcher.stop()


@pytest.fixture
def harness():
    h = _Harness()
    h.install()
    try:
        yield h
    finally:
        h.uninstall()


@pytest.fixture
def source_dir(tmp_path):
    """Minimal source tree resolvable by ``bundle.resolve_entry_point``."""
    (tmp_path / 'index.js').write_text("console.log('ok');\n")
    return str(tmp_path)


@pytest.fixture(autouse=True)
def _patch_bundle_and_upload():
    """Avoid real zipping and S3 PUTs in unit tests."""
    with (
        mock.patch.object(
            deploy.bundle,
            'build_zip',
            return_value=('/tmp/lambda-web-test.zip', 1024),
        ),
        mock.patch.object(
            deploy.bucket,
            'upload_zip',
            return_value=dict(S3_OBJECT),
        ) as upload_mock,
    ):
        yield upload_mock


def _make_args(source_dir, **overrides):
    args = mock.Mock()
    args.name = FUNCTION_NAME
    args.code = source_dir
    args.create = True
    args.hello_world = False
    args.entry_point = None
    args.bucket_name = BUCKET_NAME
    args.execution_role_arn = ROLE_ARN
    args.revision_description = None
    args.runtime = None
    args.env = None
    args.unset_env = None
    args.timeout_seconds = None
    args.max_concurrency_per_environment = None
    args.kms_key_arn = None
    args.application_log_level = None
    args.system_log_level = None
    args.include_hidden_files = False
    args.force_include = None
    args.activation_timeout = constants.DEFAULT_ACTIVATION_TIMEOUT_SECONDS
    args.progress_frequency = None
    args.no_wait = False
    args.endpoint_name = None
    args.endpoint_type = None
    args.auth_type = None
    args.auto_deployment_mode = None
    args.regions = None
    args.description = None
    args.max_environments = None
    args.rate_limit = None
    args.tags = None
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def _make_globals(region=REGION, output=None, query=None):
    globals_obj = mock.Mock()
    globals_obj.region = region
    globals_obj.verify_ssl = None
    globals_obj.endpoint_url = None
    globals_obj.output = output
    # query / color must be real values (not Mocks): emit_result checks
    # ``query is None`` to pick the url-only default, and the CLI formatters
    # read ``color``.
    globals_obj.query = query
    globals_obj.color = 'off'
    globals_obj.cli_error_format = None
    return globals_obj


ACCOUNT_ID = '111111111111'


def _stub_sts(harness):
    harness.sts_stub.add_response(
        'get_caller_identity',
        {
            'Account': ACCOUNT_ID,
            'Arn': f'arn:aws:iam::{ACCOUNT_ID}:user/test',
            'UserId': 'AID' + ('A' * 18),
        },
        expected_params={},
    )


def _stub_probe_not_found(harness):
    harness.lambda_web.add_client_error(
        'get_web_function',
        service_error_code='ResourceNotFoundException',
        service_message='no such function',
    )


def _stub_probe_found(harness):
    harness.lambda_web.add_response(
        'get_web_function',
        {
            'functionName': FUNCTION_NAME,
            'functionArn': FUNCTION_ARN,
            'state': 'Active',
            'stateReason': 'Ready',
            'createdAt': TIMESTAMP,
            'updatedAt': TIMESTAMP,
        },
    )


def _stub_bucket_ok(harness):
    harness.s3_stub.add_response(
        'head_bucket', {}, expected_params={'Bucket': BUCKET_NAME}
    )


def _stub_role_ok(harness):
    harness.iam_stub.add_response(
        'get_role',
        _role_payload(),
        expected_params={'RoleName': 'customer-role'},
    )


def _run(harness, args, parsed_globals):
    cmd = LambdaWebDeploy(harness.session)
    return cmd._run_main(args, parsed_globals)


def _mutating_calls(harness):
    """Lambda-web calls other than read-only probes and listings."""
    return [
        (op, kwargs)
        for op, kwargs in harness.lambda_web.calls
        if not op.startswith(('get_', 'list_'))
    ]


def _request_for(harness, operation):
    return next(
        kwargs for op, kwargs in harness.lambda_web.calls if op == operation
    )


def test_create_happy_path_prints_url(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out == 'https://abc123.lambda-url.us-east-1.on.aws\n'
    assert 'Console:' in captured.err
    harness.lambda_web.assert_no_pending_responses()
    harness.s3_stub.assert_no_pending_responses()
    harness.iam_stub.assert_no_pending_responses()


def test_create_json_output_includes_fields(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    rc = _run(harness, _make_args(source_dir), _make_globals(output='json'))

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['functionArn'] == FUNCTION_ARN
    assert (
        payload['endpointUrl'] == 'https://abc123.lambda-url.us-east-1.on.aws'
    )
    assert payload['roleArn'] == ROLE_ARN
    assert payload['bucketName'] == BUCKET_NAME
    assert payload['objectKey'] == S3_OBJECT['key']


def test_create_no_wait_submits_initial_endpoint_without_polling(
    harness, source_dir, capsys
):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )

    rc = _run(
        harness,
        _make_args(source_dir, no_wait=True),
        _make_globals(output='json'),
    )

    assert rc == 0
    request = _request_for(harness, 'create_web_function')
    assert request['endpointConfig']['endpointName'] == ENDPOINT_NAME
    assert all(
        op != 'get_web_function_endpoint' for op, _ in harness.lambda_web.calls
    )
    payload = json.loads(capsys.readouterr().out)
    assert 'endpointUrl' not in payload
    harness.lambda_web.assert_no_pending_responses()


def test_force_include_is_forwarded_to_bundle(harness, source_dir):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )

    rc = _run(
        harness,
        _make_args(
            source_dir,
            force_include=['.env', 'certs/public.pem'],
            no_wait=True,
        ),
        _make_globals(),
    )

    assert rc == 0
    assert deploy.bundle.build_zip.call_args.kwargs['force_include'] == [
        '.env',
        'certs/public.pem',
    ]


def test_create_request_carries_env_and_config(harness, source_dir):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    args = _make_args(
        source_dir,
        env=['A=1', 'TOKEN=a=b=c'],
        runtime='nodejs22.x',
        timeout_seconds=30,
        kms_key_arn='arn:aws:kms:us-east-1:111111111111:key/k1',
        application_log_level='DEBUG',
        tags=['team=web', 'empty='],
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    request = _request_for(harness, 'create_web_function')
    revision = request['revisionConfig']
    assert revision['buildConfig']['runtimeConfig']['runtime'] == 'nodejs22.x'
    assert revision['buildConfig']['codeConfig']['s3Object'] == S3_OBJECT
    service = revision['serviceConfig']
    assert service['executionRoleArn'] == ROLE_ARN
    assert service['timeoutSeconds'] == 30
    assert service['environmentVariables'] == {
        'A': '1',
        'TOKEN': 'a=b=c',
    }
    assert (
        service['telemetryConfig']['loggingConfig']['applicationLogLevel']
        == 'DEBUG'
    )
    assert revision['kmsKeyArn'].endswith('key/k1')
    assert request['endpointConfig'] == {
        'endpointName': 'dev',
        'endpointType': 'HomeRegion',
        'authType': 'ApplicationManaged',
        'autoDeploymentMode': 'LatestRevision',
        'regions': [REGION],
    }
    assert request['tags'] == {'team': 'web', 'empty': ''}


def test_create_request_defaults_runtime(harness, source_dir):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 0
    request = _request_for(harness, 'create_web_function')
    runtime = request['revisionConfig']['buildConfig']['runtimeConfig'][
        'runtime'
    ]
    assert runtime == deploy.constants.DEFAULT_RUNTIME


def _assert_fails_before_any_client(harness, args, parsed_globals, capsys):
    rc = _run(harness, args, parsed_globals)
    assert rc != 0
    assert _mutating_calls(harness) == []
    return capsys.readouterr(), rc


def test_non_directory_code_rejected(harness, capsys):
    args = _make_args('/does/not/exist')
    captured, rc = _assert_fails_before_any_client(
        harness, args, _make_globals(), capsys
    )
    assert rc == 252
    assert '--code' in captured.err


def test_invalid_function_name_rejected(harness, source_dir, capsys):
    args = _make_args(source_dir, name='-bad-')
    captured, rc = _assert_fails_before_any_client(
        harness, args, _make_globals(), capsys
    )
    assert rc == 252
    assert 'invalid' in captured.err


def test_entry_point_conflicts_with_entrypoint_env(
    harness, source_dir, capsys
):
    args = _make_args(
        source_dir,
        entry_point='server.js',
        env=['AWS_LAMBDA_NODEJS_ENTRYPOINT=app.mjs'],
    )
    captured, rc = _assert_fails_before_any_client(
        harness, args, _make_globals(), capsys
    )
    assert rc == 252
    assert 'AWS_LAMBDA_NODEJS_ENTRYPOINT' in captured.err


def test_no_region_raises_friendly_error(harness, source_dir, capsys):
    args = _make_args(source_dir)
    parsed_globals = _make_globals(region=None)
    with mock.patch.object(
        harness.session, 'get_config_variable', return_value=None
    ):
        captured, rc = _assert_fails_before_any_client(
            harness, args, parsed_globals, capsys
        )
    assert rc == 255
    assert 'must specify an AWS Region' in captured.err


@pytest.mark.parametrize('value', [0, -5])
def test_nonpositive_activation_timeout_rejected(
    harness, source_dir, capsys, value
):
    args = _make_args(source_dir, activation_timeout=value)
    captured, rc = _assert_fails_before_any_client(
        harness, args, _make_globals(), capsys
    )
    assert rc == 252
    assert '--activation-timeout' in captured.err


@pytest.mark.parametrize('value', [0, -5])
def test_nonpositive_progress_frequency_rejected(
    harness, source_dir, capsys, value
):
    args = _make_args(source_dir, progress_frequency=value)
    captured, rc = _assert_fails_before_any_client(
        harness, args, _make_globals(), capsys
    )
    assert rc == 252
    assert '--progress-frequency' in captured.err


def test_empty_env_value_rejected(harness, source_dir, capsys):
    args = _make_args(source_dir, env=['KEY='])
    captured, rc = _assert_fails_before_any_client(
        harness, args, _make_globals(), capsys
    )
    assert rc == 252
    assert 'must not be empty' in captured.err


@pytest.mark.parametrize(
    'entry',
    ['==========', '1BAD=value', 'BAD-NAME=value'],
)
def test_invalid_env_key_rejected_before_upload(
    harness,
    source_dir,
    capsys,
    _patch_bundle_and_upload,
    entry,
):
    args = _make_args(source_dir, env=[entry])
    captured, rc = _assert_fails_before_any_client(
        harness, args, _make_globals(), capsys
    )

    assert rc == 252
    assert '--env' in captured.err
    _patch_bundle_and_upload.assert_not_called()


def test_activation_timeout_default_is_declared():
    activation_timeout = next(
        item
        for item in deploy.args.ARG_TABLE
        if item['name'] == 'activation-timeout'
    )

    assert (
        activation_timeout['default']
        == constants.DEFAULT_ACTIVATION_TIMEOUT_SECONDS
    )


def test_application_log_level_choices_come_from_model(harness):
    cmd = LambdaWebDeploy(harness.session)
    arg = cmd.arg_table['application-log-level']
    expected = deploy.model.enum_choices(
        harness.session,
        deploy.model.ENUM_ARG_SHAPES['application-log-level'],
    )

    assert arg.choices == expected
    assert list(arg.argument_model.enum) == expected


def test_bad_bucket_fails_before_role_and_upload(
    harness, source_dir, capsys, _patch_bundle_and_upload
):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    harness.s3_stub.add_client_error(
        'head_bucket',
        service_error_code='404',
        http_status_code=404,
        expected_params={'Bucket': BUCKET_NAME},
    )

    rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 255
    captured = capsys.readouterr()
    assert BUCKET_NAME in captured.err
    # ordering: the role is not verified and nothing is uploaded after a
    # bucket failure, so no resource is orphaned.
    harness.iam_stub.assert_no_pending_responses()
    _patch_bundle_and_upload.assert_not_called()
    assert _mutating_calls(harness) == []


def test_missing_role_fails_before_upload(
    harness, source_dir, capsys, _patch_bundle_and_upload
):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    harness.iam_stub.add_client_error(
        'get_role',
        service_error_code='NoSuchEntity',
        expected_params={'RoleName': 'customer-role'},
    )

    rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 255
    assert ROLE_ARN in capsys.readouterr().err
    _patch_bundle_and_upload.assert_not_called()
    assert _mutating_calls(harness) == []


def test_bundle_removed_after_success(harness, source_dir):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    with mock.patch.object(deploy.bundle, 'remove_bundle') as remove_mock:
        rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 0
    remove_mock.assert_called_once_with('/tmp/lambda-web-test.zip')


def test_bundle_removed_when_upload_fails(
    harness, source_dir, capsys, _patch_bundle_and_upload
):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    _patch_bundle_and_upload.side_effect = deploy.LambdaWebError(
        'Unable to upload the deployment package.'
    )

    with mock.patch.object(deploy.bundle, 'remove_bundle') as remove_mock:
        rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 255
    assert 'Unable to upload' in capsys.readouterr().err
    remove_mock.assert_called_once_with('/tmp/lambda-web-test.zip')
    assert _mutating_calls(harness) == []


def test_bundle_over_max_size_fails_before_any_aws_mutation(
    harness, source_dir, capsys, _patch_bundle_and_upload
):
    """An oversized bundle is rejected client-side: nothing is uploaded and
    the temp zip is still cleaned up."""
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    too_big = deploy.constants.BUNDLE_SIZE_MAX_BYTES + 1
    with (
        mock.patch.object(
            deploy.bundle,
            'build_zip',
            return_value=('/tmp/lambda-web-test.zip', too_big),
        ),
        mock.patch.object(deploy.bundle, 'remove_bundle') as remove_mock,
    ):
        rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 252
    captured = capsys.readouterr()
    assert 'exceeds' in captured.err
    assert '512 MB' in captured.err
    _patch_bundle_and_upload.assert_not_called()
    remove_mock.assert_called_once_with('/tmp/lambda-web-test.zip')
    assert _mutating_calls(harness) == []
    harness.s3_stub.assert_no_pending_responses()
    harness.iam_stub.assert_no_pending_responses()


def test_customer_entrypoint_skips_wrapper(harness, source_dir, capsys):
    nested = deploy.os.path.join(source_dir, 'dist')
    deploy.os.makedirs(nested)
    with open(deploy.os.path.join(nested, 'app.mjs'), 'w') as f:
        f.write('export default 1;\n')
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    args = _make_args(
        source_dir,
        env=[r'AWS_LAMBDA_NODEJS_ENTRYPOINT=dist\\app.mjs'],
    )
    with mock.patch.object(
        deploy.bundle, 'build_zip', return_value=('/tmp/z.zip', 10)
    ) as build_mock:
        rc = _run(harness, args, _make_globals())

    assert rc == 0
    assert build_mock.call_args[0][1] is None
    request = _request_for(harness, 'create_web_function')
    assert (
        request['revisionConfig']['serviceConfig']['environmentVariables'][
            constants.ENTRYPOINT_ENV_VAR
        ]
        == 'dist/app.mjs'
    )
    assert 'AWS_LAMBDA_NODEJS_ENTRYPOINT' in capsys.readouterr().err


def test_customer_entrypoint_missing_file_errors(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    args = _make_args(
        source_dir, env=['AWS_LAMBDA_NODEJS_ENTRYPOINT=missing.mjs']
    )
    rc = _run(harness, args, _make_globals())
    assert rc == 252
    assert 'missing.mjs' in capsys.readouterr().err
    assert _mutating_calls(harness) == []


def test_inherited_entrypoint_checked_against_replacement_code(
    harness,
    source_dir,
    capsys,
    _patch_bundle_and_upload,
):
    existing = _existing_revision(
        env_vars={constants.ENTRYPOINT_ENV_VAR: 'server.mjs'}
    )
    _stub_update_prelude(harness, existing=existing)

    rc = _run(
        harness,
        _make_args(source_dir, execution_role_arn=None),
        _make_globals(),
    )

    assert rc == 252
    error = capsys.readouterr().err
    assert constants.ENTRYPOINT_ENV_VAR in error
    assert 'server.mjs' in error
    _patch_bundle_and_upload.assert_not_called()
    assert all(
        operation != 'create_web_function_revision'
        for operation, _ in harness.lambda_web.calls
    )


def test_create_failure_surfaces_service_error(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_client_error(
        'create_web_function',
        service_error_code='ConflictException',
        service_message='function already exists',
        http_status_code=409,
    )

    with (
        mock.patch.object(harness.s3, 'delete_object') as delete_mock,
        pytest.raises(ClientError),
    ):
        _run(harness, _make_args(source_dir), _make_globals())

    captured = capsys.readouterr()
    assert f's3://{BUCKET_NAME}/{S3_OBJECT["key"]}' in captured.err
    assert f'version ID: {S3_OBJECT["versionId"]}' in captured.err
    delete_mock.assert_not_called()


def test_non_tty_without_create_refuses(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    args = _make_args(source_dir, create=False)

    with mock.patch.object(
        LambdaWebDeploy, '_stdin_is_tty', return_value=False
    ):
        rc = _run(harness, args, _make_globals())

    assert rc == 255
    captured = capsys.readouterr()
    assert 'Run the command again with --create' in captured.err
    assert _mutating_calls(harness) == []


def test_tty_enter_confirm_proceeds(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )
    args = _make_args(source_dir, create=False)

    with (
        mock.patch.object(LambdaWebDeploy, '_stdin_is_tty', return_value=True),
        mock.patch.object(deploy, 'compat_input', return_value=''),
    ):
        rc = _run(harness, args, _make_globals())

    assert rc == 0
    assert 'Press Enter' in capsys.readouterr().err


def test_ctrl_c_at_prompt_cancels_cleanly(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    args = _make_args(source_dir, create=False)

    with (
        mock.patch.object(LambdaWebDeploy, '_stdin_is_tty', return_value=True),
        mock.patch.object(
            deploy, 'compat_input', side_effect=KeyboardInterrupt
        ),
    ):
        rc = _run(harness, args, _make_globals())

    assert rc == 130
    assert 'no resources were created' in capsys.readouterr().err
    assert _mutating_calls(harness) == []


def test_eof_at_prompt_cancels_cleanly(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    args = _make_args(source_dir, create=False)

    with (
        mock.patch.object(LambdaWebDeploy, '_stdin_is_tty', return_value=True),
        mock.patch.object(deploy, 'compat_input', side_effect=EOFError),
    ):
        rc = _run(harness, args, _make_globals())

    assert rc == 255
    error = capsys.readouterr().err
    assert 'no resources were created' in error
    assert '--create' in error
    assert _mutating_calls(harness) == []


def test_create_retries_iam_propagation_then_succeeds(
    harness, source_dir, capsys
):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_client_error(
        'create_web_function',
        service_error_code='ValidationException',
        service_message='The role cannot be assumed; retry in a few seconds',
    )
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    with mock.patch.object(deploy.role.time, 'sleep') as sleep_mock:
        rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 0
    sleep_mock.assert_called_once()
    harness.lambda_web.assert_no_pending_responses()


def test_create_managed_role_when_no_override(harness, source_dir):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    harness.iam_stub.add_client_error(
        'get_role',
        service_error_code='NoSuchEntity',
        expected_params={'RoleName': f'awscli-lambdaweb-{FUNCTION_NAME}'},
    )
    harness.iam_stub.add_response(
        'create_role',
        {
            'Role': {
                'Path': '/',
                'RoleName': f'awscli-lambdaweb-{FUNCTION_NAME}',
                'RoleId': 'AROAEXAMPLEROLEIDXX',
                'Arn': (
                    f'arn:aws:iam::{ACCOUNT_ID}:role/'
                    f'awscli-lambdaweb-{FUNCTION_NAME}'
                ),
                'CreateDate': TIMESTAMP,
            }
        },
        expected_params={
            'RoleName': f'awscli-lambdaweb-{FUNCTION_NAME}',
            'AssumeRolePolicyDocument': mock.ANY,
        },
    )
    harness.iam_stub.add_response(
        'put_role_policy',
        {},
        expected_params={
            'RoleName': f'awscli-lambdaweb-{FUNCTION_NAME}',
            'PolicyName': 'awscli-lambdaweb-logs',
            'PolicyDocument': mock.ANY,
        },
    )
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    rc = _run(
        harness,
        _make_args(source_dir, execution_role_arn=None),
        _make_globals(),
    )

    assert rc == 0
    harness.iam_stub.assert_no_pending_responses()


def test_create_managed_bucket_when_no_override(harness, source_dir):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    managed = f'awscli-lambdaweb-{ACCOUNT_ID}-{REGION}-an'
    harness.s3_stub.add_response(
        'head_bucket', {}, expected_params={'Bucket': managed}
    )
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    rc = _run(
        harness,
        _make_args(source_dir, bucket_name=None),
        _make_globals(output='json'),
    )

    assert rc == 0
    harness.s3_stub.assert_no_pending_responses()


def test_sts_failure_reports_permission_hint(harness, source_dir, capsys):
    harness.sts_stub.add_client_error(
        'get_caller_identity',
        service_error_code='AccessDenied',
        http_status_code=403,
    )

    parsed_globals = _make_globals()
    parsed_globals.cli_error_format = 'json'
    rc = _run(harness, _make_args(source_dir), parsed_globals)

    assert rc == 255
    captured = capsys.readouterr()
    error = json.loads(captured.err)
    assert 'sts:GetCallerIdentity' in error['Error']['Message']
    assert harness.lambda_web.calls == []


def test_sts_missing_credentials_reports_permission_hint(
    harness,
    source_dir,
    capsys,
):
    with mock.patch.object(
        harness.sts,
        'get_caller_identity',
        side_effect=NoCredentialsError(),
    ):
        rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 255
    captured = capsys.readouterr()
    assert 'sts:GetCallerIdentity' in captured.err
    assert _mutating_calls(harness) == []


def test_partition_aware_console_url_for_aws_cn(source_dir, capsys):
    h = _Harness(region='cn-north-1')
    h.install()
    try:
        h.sts_stub.add_response(
            'get_caller_identity',
            {
                'Account': ACCOUNT_ID,
                'Arn': f'arn:aws:iam::{ACCOUNT_ID}:user/test',
                'UserId': 'AID' + ('A' * 18),
            },
            expected_params={},
        )
        h.lambda_web.add_client_error(
            'get_web_function',
            service_error_code='ResourceNotFoundException',
            service_message='no such function',
        )
        h.s3_stub.add_response(
            'head_bucket', {}, expected_params={'Bucket': BUCKET_NAME}
        )
        h.iam_stub.add_response(
            'get_role',
            _role_payload(),
            expected_params={'RoleName': 'customer-role'},
        )
        h.lambda_web.add_response(
            'create_web_function', _create_web_function_response()
        )
        h.lambda_web.add_response(
            'get_web_function_endpoint', _endpoint_response()
        )
        rc = _run(
            h, _make_args(source_dir), _make_globals(region='cn-north-1')
        )
    finally:
        h.uninstall()

    assert rc == 0
    assert 'console.amazonaws.cn' in capsys.readouterr().err


REVISION_ID = 'rev-001'
REVISION_ARN = f'arn:aws:lambda:{REGION}:{ACCOUNT_ID}:revision:{REVISION_ID}'
EXISTING_ROLE_ARN = (
    f'arn:aws:iam::{ACCOUNT_ID}:role/awscli-lambdaweb-{FUNCTION_NAME}'
)
EXISTING_RUNTIME = 'nodejs20.x'


def _revision_summary(revision_id=REVISION_ID, state='Active'):
    return {
        'revisionArn': f'arn:aws:lambda:{REGION}:{ACCOUNT_ID}:revision:{revision_id}',
        'revisionId': revision_id,
        'state': state,
        'stateReason': 'ok',
        'createdAt': TIMESTAMP,
    }


def _existing_revision(env_vars=None, kms_key_arn=None):
    service_config = {
        'executionRoleArn': EXISTING_ROLE_ARN,
        'timeoutSeconds': 15,
        'maxConcurrencyPerEnvironment': 10,
    }
    if env_vars is not None:
        service_config['environmentVariables'] = env_vars
    response = {
        'functionArn': FUNCTION_ARN,
        'revisionArn': REVISION_ARN,
        'revisionId': REVISION_ID,
        'serviceConfig': service_config,
        'buildConfig': {
            'codeConfig': {
                's3Object': {
                    'bucket': 'previous-bucket',
                    'key': 'previous-key',
                }
            },
            'runtimeConfig': {'runtime': EXISTING_RUNTIME},
        },
        'state': 'Active',
        'stateReason': 'ok',
        'createdAt': TIMESTAMP,
    }
    if kms_key_arn:
        response['kmsKeyArn'] = kms_key_arn
    return response


def _new_revision_response(state='Pending'):
    response = _existing_revision()
    response['revisionId'] = 'rev-002'
    response['revisionArn'] = REVISION_ARN.replace('rev-001', 'rev-002')
    response['state'] = state
    return response


def _endpoint_summary(auto_mode='LatestRevision'):
    return {
        'endpointArn': f'{FUNCTION_ARN}:endpoint/{ENDPOINT_NAME}',
        'endpointName': ENDPOINT_NAME,
        'endpointType': 'HomeRegion',
        'domainName': 'abc123.lambda-url.us-east-1.on.aws',
        'authType': 'ApplicationManaged',
        'autoDeploymentMode': auto_mode,
        'revisionWeights': [{'revisionId': REVISION_ID, 'weight': 100}],
        'regions': [REGION],
        'state': 'Active',
        'stateReason': 'ok',
        'createdAt': TIMESTAMP,
        'updatedAt': TIMESTAMP,
    }


def _stub_update_prelude(
    harness,
    *,
    existing=None,
    endpoints=None,
    endpoint_pages=None,
):
    """Queue probe-found, inheritance chain, and endpoint listing."""
    _stub_sts(harness)
    _stub_probe_found(harness)
    harness.lambda_web.add_response(
        'list_web_function_revisions',
        {'revisions': [_revision_summary()]},
    )
    harness.lambda_web.add_response(
        'get_web_function_revision',
        existing if existing is not None else _existing_revision(),
    )
    if endpoint_pages is None:
        endpoint_pages = [
            {
                'endpoints': (
                    endpoints
                    if endpoints is not None
                    else [_endpoint_summary()]
                )
            }
        ]
    for page in endpoint_pages:
        harness.lambda_web.add_response(
            'list_web_function_endpoints',
            page,
        )


def _stub_update_tail(harness):
    """Queue the create-revision call, revision wait, and endpoint wait."""
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_revision', _new_revision_response(state='Active')
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )


def test_update_happy_path_deploys_revision(harness, source_dir, capsys):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    _stub_update_tail(harness)

    rc = _run(
        harness,
        _make_args(source_dir, execution_role_arn=None),
        _make_globals(output='json'),
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['revisionId'] == 'rev-002'
    assert (
        payload['endpointUrl'] == 'https://abc123.lambda-url.us-east-1.on.aws'
    )
    harness.lambda_web.assert_no_pending_responses()
    harness.iam_stub.assert_no_pending_responses()


def test_update_failure_reports_retained_package(
    harness,
    source_dir,
    capsys,
):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    harness.lambda_web.add_client_error(
        'create_web_function_revision',
        service_error_code='ConflictException',
        service_message='revision conflict',
        http_status_code=409,
    )

    with (
        mock.patch.object(harness.s3, 'delete_object') as delete_mock,
        pytest.raises(ClientError),
    ):
        _run(
            harness,
            _make_args(source_dir, execution_role_arn=None),
            _make_globals(),
        )

    captured = capsys.readouterr()
    assert f's3://{BUCKET_NAME}/{S3_OBJECT["key"]}' in captured.err
    assert f'version ID: {S3_OBJECT["versionId"]}' in captured.err
    delete_mock.assert_not_called()


def test_update_inherits_runtime_and_role(harness, source_dir):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    _stub_update_tail(harness)

    args = _make_args(source_dir, execution_role_arn=None)
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    request = _request_for(harness, 'create_web_function_revision')
    assert (
        request['buildConfig']['runtimeConfig']['runtime'] == EXISTING_RUNTIME
    )
    assert request['serviceConfig']['executionRoleArn'] == EXISTING_ROLE_ARN
    assert request['serviceConfig']['timeoutSeconds'] == 15
    harness.iam_stub.assert_no_pending_responses()


def test_update_preserves_projected_revision_fields_when_overriding(
    harness, source_dir
):
    existing = _existing_revision(
        kms_key_arn='arn:aws:kms:us-east-1:111111111111:key/existing'
    )
    existing['description'] = 'existing description'
    existing['futureRevisionConfig'] = {
        'disabled': False,
        'emptyValue': '',
    }
    existing['buildConfig']['futureBuildConfig'] = {'items': []}
    existing['buildConfig']['codeConfig']['futureCodeConfig'] = {
        'enabled': False
    }
    existing['buildConfig']['codeConfig']['s3Object']['futureS3Object'] = {
        'value': 0
    }
    existing['buildConfig']['runtimeConfig']['futureRuntimeConfig'] = {
        'mode': 'existing'
    }
    existing['serviceConfig']['futureServiceConfig'] = {
        'emptyObject': {},
        'enabled': False,
    }
    existing['serviceConfig']['telemetryConfig'] = {
        'futureTelemetryConfig': {'items': []},
        'loggingConfig': {
            'logGroup': '/custom/log-group',
            'futureLoggingConfig': {'enabled': False},
        },
    }
    _stub_update_prelude(harness, existing=existing)
    _stub_bucket_ok(harness)
    _stub_update_tail(harness)

    args = _make_args(
        source_dir,
        execution_role_arn=None,
        timeout_seconds=30,
        application_log_level='DEBUG',
        kms_key_arn='',
        revision_description='',
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    request = _request_for(harness, 'create_web_function_revision')
    assert 'description' not in request
    assert request['kmsKeyArn'].endswith('/existing')
    assert request['futureRevisionConfig'] == {
        'disabled': False,
        'emptyValue': '',
    }
    build = request['buildConfig']
    assert build['futureBuildConfig'] == {'items': []}
    assert build['codeConfig']['futureCodeConfig'] == {'enabled': False}
    assert build['codeConfig']['s3Object']['futureS3Object'] == {'value': 0}
    assert build['codeConfig']['s3Object']['bucket'] == BUCKET_NAME
    assert build['runtimeConfig']['futureRuntimeConfig'] == {
        'mode': 'existing'
    }
    service = request['serviceConfig']
    assert service['futureServiceConfig'] == {
        'emptyObject': {},
        'enabled': False,
    }
    assert service['timeoutSeconds'] == 30
    telemetry = service['telemetryConfig']
    assert telemetry['futureTelemetryConfig'] == {'items': []}
    logging = telemetry['loggingConfig']
    assert logging['logGroup'] == '/custom/log-group'
    assert logging['applicationLogLevel'] == 'DEBUG'
    assert logging['futureLoggingConfig'] == {'enabled': False}


def test_update_applies_nonempty_revision_description(harness, source_dir):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    _stub_update_tail(harness)

    args = _make_args(
        source_dir,
        execution_role_arn=None,
        revision_description='updated revision',
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    request = _request_for(harness, 'create_web_function_revision')
    assert request['description'] == 'updated revision'


def test_update_merges_env_and_applies_unset(harness, source_dir):
    _stub_update_prelude(
        harness,
        existing=_existing_revision(
            env_vars={'KEEP': '1', 'OVERRIDE': 'old', 'DROP': 'x'}
        ),
    )
    _stub_bucket_ok(harness)
    _stub_update_tail(harness)

    args = _make_args(
        source_dir,
        execution_role_arn=None,
        env=['OVERRIDE=new', 'ADDED=2'],
        unset_env=['DROP'],
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    request = _request_for(harness, 'create_web_function_revision')
    assert request['serviceConfig']['environmentVariables'] == {
        'KEEP': '1',
        'OVERRIDE': 'new',
        'ADDED': '2',
    }


def test_update_repoints_pinned_endpoint(harness, source_dir):
    _stub_update_prelude(
        harness, endpoints=[_endpoint_summary(auto_mode='Disabled')]
    )
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_revision', _new_revision_response(state='Active')
    )
    harness.lambda_web.add_response('update_web_function_endpoint', {})
    harness.lambda_web.add_response(
        'get_web_function_endpoint',
        _endpoint_response(update_status='InProgress'),
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint',
        _endpoint_response(update_status='Successful'),
    )

    rc = _run(
        harness,
        _make_args(source_dir, execution_role_arn=None),
        _make_globals(),
    )

    assert rc == 0
    request = _request_for(harness, 'update_web_function_endpoint')
    assert request['revisionWeights'] == [
        {'revisionId': 'rev-002', 'weight': 100}
    ]
    harness.lambda_web.assert_no_pending_responses()


def test_update_auto_deploy_endpoint_not_repointed(
    harness, source_dir, capsys
):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    _stub_update_tail(harness)

    rc = _run(
        harness,
        _make_args(source_dir, execution_role_arn=None),
        _make_globals(),
    )

    assert rc == 0
    assert all(
        op != 'update_web_function_endpoint'
        for op, _ in harness.lambda_web.calls
    )
    assert 'auto-deploys the latest' in capsys.readouterr().err


def test_update_no_endpoints_reports_no_url(harness, source_dir, capsys):
    _stub_update_prelude(harness, endpoints=[])
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_revision', _new_revision_response(state='Active')
    )

    rc = _run(
        harness,
        _make_args(source_dir, execution_role_arn=None),
        _make_globals(output='json'),
    )

    assert rc == 0
    captured = capsys.readouterr()
    assert 'has no endpoint' in captured.err
    payload = json.loads(captured.out)
    assert 'endpointUrl' not in payload


def test_reuse_code_updates_config_without_upload(
    harness, source_dir, capsys, _patch_bundle_and_upload
):
    _stub_update_prelude(
        harness, existing=_existing_revision(env_vars={'A': '1'})
    )
    _stub_update_tail(harness)

    args = _make_args(
        None,
        code=None,
        bucket_name=None,
        execution_role_arn=None,
        env=['B=2'],
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    _patch_bundle_and_upload.assert_not_called()
    assert 'Reusing deployed code' in capsys.readouterr().err
    request = _request_for(harness, 'create_web_function_revision')
    assert request['buildConfig']['codeConfig']['s3Object']['bucket'] == (
        'previous-bucket'
    )
    assert request['serviceConfig']['environmentVariables'] == {
        'A': '1',
        'B': '2',
    }
    harness.s3_stub.assert_no_pending_responses()


def test_reuse_code_on_missing_function_errors(harness, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)

    args = _make_args(
        None, code=None, bucket_name=None, execution_role_arn=None
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 255
    assert "doesn't exist" in capsys.readouterr().err


def test_reuse_code_rejects_bundling_flags(harness, capsys):
    args = _make_args(
        None,
        code=None,
        execution_role_arn=None,
        entry_point='server.js',
        force_include=['.env'],
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 255
    captured = capsys.readouterr()
    assert '--entry-point' in captured.err
    assert '--bucket-name' in captured.err
    assert '--force-include' in captured.err
    assert harness.lambda_web.calls == []


def test_tags_added_or_replaced_on_update(harness, source_dir):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    harness.lambda_web.add_response('tag_resource', {})
    harness.lambda_web.add_response(
        'get_web_function_revision', _new_revision_response(state='Active')
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    rc = _run(
        harness,
        _make_args(
            source_dir,
            execution_role_arn=None,
            tags=['team=web', 'owner=platform'],
        ),
        _make_globals(),
    )

    assert rc == 0
    assert _request_for(harness, 'tag_resource') == {
        'resource': FUNCTION_ARN,
        'tags': {'team': 'web', 'owner': 'platform'},
    }


def test_tag_failure_warns_and_continues_update(harness, source_dir, capsys):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    harness.lambda_web.add_client_error(
        'tag_resource',
        service_error_code='AccessDeniedException',
        service_message='tagging denied',
        http_status_code=403,
    )
    harness.lambda_web.add_response(
        'get_web_function_revision', _new_revision_response(state='Active')
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    rc = _run(
        harness,
        _make_args(
            source_dir,
            execution_role_arn=None,
            tags=['team=web'],
        ),
        _make_globals(output='json'),
    )

    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload['revisionId'] == 'rev-002'
    assert (
        payload['endpointUrl'] == 'https://abc123.lambda-url.us-east-1.on.aws'
    )
    error = captured.err
    assert 'Warning:' in error
    assert 'Revision rev-002 was created' in error
    assert "couldn't confirm whether tags" in error
    assert 'AccessDeniedException' in error
    assert 'aws lambda-web tag-resource' in error
    harness.lambda_web.assert_no_pending_responses()


def test_unset_env_rejected_on_create(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)

    args = _make_args(source_dir, unset_env=['SOME_KEY'])
    rc = _run(harness, args, _make_globals())

    assert rc == 252
    assert '--unset-env' in capsys.readouterr().err
    assert _mutating_calls(harness) == []


def test_update_no_revisions_raises_clear_error(harness, source_dir, capsys):
    _stub_sts(harness)
    _stub_probe_found(harness)
    harness.lambda_web.add_response(
        'list_web_function_revisions', {'revisions': []}
    )

    rc = _run(harness, _make_args(source_dir), _make_globals())

    assert rc == 255
    assert 'no revisions to inherit from' in capsys.readouterr().err


def test_environment_read_error_blocks_revision_before_bundle(
    harness,
    source_dir,
    capsys,
    _patch_bundle_and_upload,
):
    existing = _existing_revision(
        kms_key_arn='arn:aws:kms:us-east-1:111111111111:key/k1'
    )
    existing['errors'] = [
        {
            'attribute': 'serviceConfig.environmentVariables',
            'errorCode': 'AccessDeniedException',
            'errorMessage': 'Could not decrypt the environment variables.',
        }
    ]
    _stub_update_prelude(
        harness,
        existing=existing,
    )

    rc = _run(
        harness,
        _make_args(source_dir, execution_role_arn=None),
        _make_globals(),
    )

    assert rc == 255
    error = capsys.readouterr().err
    assert "environment variables aren't readable" in error
    assert 'AccessDeniedException' in error
    _patch_bundle_and_upload.assert_not_called()
    assert all(
        op != 'create_web_function_revision'
        for op, _ in harness.lambda_web.calls
    )


def test_empty_environment_without_read_error_can_update(harness):
    _stub_update_prelude(
        harness,
        existing=_existing_revision(
            kms_key_arn='arn:aws:kms:us-east-1:111111111111:key/k1'
        ),
    )
    _stub_update_tail(harness)

    rc = _run(
        harness,
        _make_args(
            None,
            code=None,
            bucket_name=None,
            execution_role_arn=None,
            env=['B=2'],
        ),
        _make_globals(),
    )

    assert rc == 0
    request = _request_for(harness, 'create_web_function_revision')
    assert request['serviceConfig']['environmentVariables'] == {'B': '2'}


def _stub_update_through_revision_active(harness, *, endpoints=None):
    _stub_update_prelude(harness, endpoints=endpoints)
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_revision', _new_revision_response(state='Active')
    )


def test_add_endpoint_with_create_flag(harness, source_dir, capsys):
    _stub_update_through_revision_active(harness)
    harness.lambda_web.add_response('create_web_function_endpoint', {})
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    args = _make_args(
        source_dir, execution_role_arn=None, endpoint_name='staging'
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    request = _request_for(harness, 'create_web_function_endpoint')
    assert request['endpointName'] == 'staging'
    assert request['endpointType'] == 'HomeRegion'
    assert "Creating endpoint 'staging'" in capsys.readouterr().err


def test_named_endpoint_is_found_on_later_page(harness, source_dir):
    staging = _endpoint_summary()
    staging['endpointName'] = 'staging'
    staging['endpointArn'] = f'{FUNCTION_ARN}:endpoint/staging'
    _stub_update_prelude(
        harness,
        endpoint_pages=[
            {
                'endpoints': [_endpoint_summary()],
                'nextToken': 'page-2',
            },
            {'endpoints': [staging]},
        ],
    )
    _stub_bucket_ok(harness)
    _stub_update_tail(harness)

    rc = _run(
        harness,
        _make_args(
            source_dir,
            execution_role_arn=None,
            endpoint_name='staging',
        ),
        _make_globals(),
    )

    assert rc == 0
    list_calls = [
        params
        for operation, params in harness.lambda_web.calls
        if operation == 'list_web_function_endpoints'
    ]
    assert list_calls == [
        {'functionName': FUNCTION_NAME},
        {'functionName': FUNCTION_NAME, 'nextToken': 'page-2'},
    ]
    assert (
        _request_for(harness, 'get_web_function_endpoint')['endpointName']
        == 'staging'
    )


def test_add_endpoint_non_tty_without_create_refuses(
    harness, source_dir, capsys
):
    _stub_update_prelude(harness)

    args = _make_args(
        source_dir,
        create=False,
        execution_role_arn=None,
        endpoint_name='staging',
    )
    with mock.patch.object(deploy.sys, 'stdin', io.StringIO()):
        rc = _run(harness, args, _make_globals())

    assert rc == 255
    captured = capsys.readouterr()
    assert 'staging' in captured.err
    assert '--create' in captured.err
    assert _mutating_calls(harness) == []


def test_reconfigure_endpoint_auth_type(harness, source_dir):
    _stub_update_through_revision_active(harness)
    harness.lambda_web.add_response('update_web_function_endpoint', {})
    harness.lambda_web.add_response(
        'get_web_function_endpoint',
        _endpoint_response(update_status='Successful'),
    )

    args = _make_args(source_dir, execution_role_arn=None, auth_type='IamAuth')
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    request = _request_for(harness, 'update_web_function_endpoint')
    assert request['authType'] == 'IamAuth'


def test_immutable_endpoint_type_rejected_when_differs(
    harness, source_dir, capsys
):
    _stub_update_prelude(harness)

    args = _make_args(
        source_dir, execution_role_arn=None, endpoint_type='MultiRegion'
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 255
    captured = capsys.readouterr()
    assert '--endpoint-type' in captured.err
    assert "can't be changed" in captured.err
    assert 'create a new endpoint with a different name' in captured.err
    assert _mutating_calls(harness) == []


def test_canary_split_endpoint_not_collapsed(harness, source_dir, capsys):
    split = _endpoint_summary(auto_mode='Disabled')
    split['revisionWeights'] = [
        {'revisionId': REVISION_ID, 'weight': 90},
        {'revisionId': 'rev-000', 'weight': 10},
    ]
    _stub_update_through_revision_active(harness, endpoints=[split])
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    rc = _run(
        harness,
        _make_args(source_dir, execution_role_arn=None),
        _make_globals(),
    )

    assert rc == 0
    assert all(
        op != 'update_web_function_endpoint'
        for op, _ in harness.lambda_web.calls
    )
    assert 'splits traffic across' in capsys.readouterr().err


def test_repoint_retries_on_concurrent_update_conflict(
    harness, source_dir, capsys
):
    pinned = _endpoint_summary(auto_mode='Disabled')
    _stub_update_through_revision_active(harness, endpoints=[pinned])
    harness.lambda_web.add_client_error(
        'update_web_function_endpoint',
        service_error_code='ConflictException',
        service_message='endpoint has a newer update at 2026-01-01',
        http_status_code=409,
    )
    fresh = dict(
        pinned,
        revisionWeights=[{'revisionId': 'rev-somebody-else', 'weight': 100}],
    )
    harness.lambda_web.add_response('get_web_function_endpoint', fresh)
    harness.lambda_web.add_response('update_web_function_endpoint', {})
    harness.lambda_web.add_response(
        'get_web_function_endpoint',
        _endpoint_response(update_status='Successful'),
    )

    with mock.patch.object(deploy.time, 'sleep'):
        rc = _run(
            harness,
            _make_args(source_dir, execution_role_arn=None),
            _make_globals(),
        )

    assert rc == 0
    assert 'updated concurrently' in capsys.readouterr().err
    harness.lambda_web.assert_no_pending_responses()


def test_repoint_non_race_conflict_surfaces_immediately(
    harness, source_dir, capsys
):
    pinned = _endpoint_summary(auto_mode='Disabled')
    _stub_update_through_revision_active(harness, endpoints=[pinned])
    harness.lambda_web.add_client_error(
        'update_web_function_endpoint',
        service_error_code='ConflictException',
        service_message='endpoint is being deleted',
        http_status_code=409,
    )

    with pytest.raises(ClientError):
        _run(
            harness,
            _make_args(source_dir, execution_role_arn=None),
            _make_globals(),
        )
    error = capsys.readouterr().err
    assert 'Revision rev-002 is Active' in error
    assert (
        f"Endpoint '{ENDPOINT_NAME}' might have been partially updated"
        in error
    )
    assert 'aws lambda-web get-web-function-endpoint' in error
    assert f'--function-name {FUNCTION_NAME}' in error
    assert f'--endpoint-name {ENDPOINT_NAME}' in error
    assert 'before retrying the deploy' in error


def test_no_wait_returns_after_revision_create(harness, source_dir, capsys):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )

    args = _make_args(source_dir, execution_role_arn=None, no_wait=True)
    rc = _run(harness, args, _make_globals(output='json'))

    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload['revisionId'] == 'rev-002'
    assert 'endpointUrl' not in payload
    assert '--no-wait' in captured.err
    harness.lambda_web.assert_no_pending_responses()


def test_no_wait_submits_endpoint_update_without_waiting_for_endpoint(
    harness, source_dir, capsys
):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_revision', _new_revision_response(state='Active')
    )
    harness.lambda_web.add_response(
        'update_web_function_endpoint', _endpoint_response()
    )

    args = _make_args(
        source_dir,
        execution_role_arn=None,
        no_wait=True,
        auth_type='IamAuth',
    )
    rc = _run(harness, args, _make_globals(output='json'))

    assert rc == 0
    request = _request_for(harness, 'update_web_function_endpoint')
    assert request['authType'] == 'IamAuth'
    assert all(
        op != 'get_web_function_endpoint' for op, _ in harness.lambda_web.calls
    )
    captured = capsys.readouterr()
    assert 'before submitting endpoint changes' in captured.err
    assert 'endpointUrl' not in json.loads(captured.out)
    harness.lambda_web.assert_no_pending_responses()


def test_no_wait_creates_endpoint_without_waiting_for_endpoint(
    harness, source_dir, capsys
):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_revision', _new_revision_response(state='Active')
    )
    harness.lambda_web.add_response(
        'create_web_function_endpoint',
        _endpoint_response(state='Pending'),
    )

    args = _make_args(
        source_dir,
        execution_role_arn=None,
        endpoint_name='staging',
        no_wait=True,
    )
    rc = _run(harness, args, _make_globals(output='json'))

    assert rc == 0
    request = _request_for(harness, 'create_web_function_endpoint')
    assert request['endpointName'] == 'staging'
    assert all(
        op != 'get_web_function_endpoint' for op, _ in harness.lambda_web.calls
    )
    captured = capsys.readouterr()
    assert 'before submitting endpoint changes' in captured.err
    assert 'endpointUrl' not in json.loads(captured.out)
    harness.lambda_web.assert_no_pending_responses()


def test_no_wait_revision_failure_explains_endpoint_update_recovery(
    harness, source_dir, capsys
):
    _stub_update_prelude(harness)
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    failed = _new_revision_response(state='Failed')
    failed['stateReason'] = 'Build failed'
    harness.lambda_web.add_response('get_web_function_revision', failed)

    rc = _run(
        harness,
        _make_args(
            source_dir,
            execution_role_arn=None,
            no_wait=True,
            auth_type='IamAuth',
        ),
        _make_globals(),
    )

    assert rc == 255
    error = capsys.readouterr().err
    assert "Endpoint 'dev' was not updated" in error
    assert 'Resolve the revision failure' in error
    assert 'run the same deploy command again' in error
    assert all(
        op != 'update_web_function_endpoint'
        for op, _ in harness.lambda_web.calls
    )
    harness.lambda_web.assert_no_pending_responses()


def test_no_wait_revision_timeout_explains_endpoint_create_recovery(
    harness, source_dir, capsys
):
    _stub_update_prelude(harness, endpoints=[])
    _stub_bucket_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function_revision', _new_revision_response()
    )
    timeout = ActivationTimeoutError(
        "Revision 'rev-002' did not become active. Resume with: "
        'aws lambda-web get-web-function-revision'
    )

    with mock.patch.object(
        deploy.wait, 'wait_for_revision_active', side_effect=timeout
    ):
        rc = _run(
            harness,
            _make_args(
                source_dir,
                execution_role_arn=None,
                endpoint_name='staging',
                no_wait=True,
            ),
            _make_globals(),
        )

    assert rc == 255
    error = capsys.readouterr().err
    assert "Endpoint 'staging' was not created" in error
    assert 'Check the revision status with the command shown above' in error
    assert 'run the same deploy command again' in error
    assert all(
        op != 'create_web_function_endpoint'
        for op, _ in harness.lambda_web.calls
    )
    harness.lambda_web.assert_no_pending_responses()


def test_add_endpoint_failure_reports_revision_and_recovery(
    harness, source_dir, capsys
):
    _stub_update_through_revision_active(harness, endpoints=[])
    harness.lambda_web.add_client_error(
        'create_web_function_endpoint',
        service_error_code='AccessDeniedException',
        service_message='not authorized',
        http_status_code=403,
    )

    with pytest.raises(ClientError):
        _run(
            harness,
            _make_args(
                source_dir,
                execution_role_arn=None,
                endpoint_name='staging',
            ),
            _make_globals(),
        )

    error = capsys.readouterr().err
    assert "Revision rev-002 is Active, but endpoint 'staging'" in error
    assert 'was not created' in error
    assert 'run the same deploy command again' in error
    harness.lambda_web.assert_no_pending_responses()


def test_endpoint_tuning_sent_when_differs(harness, source_dir):
    pinned = _endpoint_summary(auto_mode='Disabled')
    _stub_update_through_revision_active(harness, endpoints=[pinned])
    harness.lambda_web.add_response('update_web_function_endpoint', {})
    harness.lambda_web.add_response(
        'get_web_function_endpoint',
        _endpoint_response(update_status='Successful'),
    )

    args = _make_args(
        source_dir,
        execution_role_arn=None,
        max_environments=7,
        rate_limit=250,
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    request = _request_for(harness, 'update_web_function_endpoint')
    assert request['scalingConfig'] == {'maxEnvironments': 7}
    assert request['throttleConfig'] == {'rateLimit': 250}


def test_multiregion_add_requires_regions(harness, source_dir, capsys):
    _stub_update_prelude(harness, endpoints=[])

    args = _make_args(
        source_dir,
        execution_role_arn=None,
        endpoint_name='global',
        endpoint_type='MultiRegion',
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 255
    assert '--regions is required' in capsys.readouterr().err
    assert _mutating_calls(harness) == []


def test_multiregion_add_pins_new_revision(harness, source_dir):
    _stub_update_through_revision_active(harness, endpoints=[])
    harness.lambda_web.add_response('create_web_function_endpoint', {})
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    args = _make_args(
        source_dir,
        execution_role_arn=None,
        endpoint_name='global',
        endpoint_type='MultiRegion',
        regions='us-east-1,us-west-2',
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    request = _request_for(harness, 'create_web_function_endpoint')
    assert request['endpointType'] == 'MultiRegion'
    assert request['regions'] == ['us-east-1', 'us-west-2']
    assert request['autoDeploymentMode'] == 'Disabled'
    assert request['revisionWeights'] == [
        {'revisionId': 'rev-002', 'weight': 100}
    ]


def test_hello_world_scaffolds_and_creates(harness, tmp_path, capsys):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )

    target = str(tmp_path / 'fresh-app')
    args = _make_args(target, hello_world=True, create=False)
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    assert (tmp_path / 'fresh-app' / 'server.ts').exists()
    assert 'Creating starter application' in capsys.readouterr().err


def test_hello_world_defaults_code_to_dot_name(harness, tmp_path, monkeypatch):
    _stub_sts(harness)
    _stub_probe_not_found(harness)
    _stub_bucket_ok(harness)
    _stub_role_ok(harness)
    harness.lambda_web.add_response(
        'create_web_function', _create_web_function_response()
    )
    harness.lambda_web.add_response(
        'get_web_function_endpoint', _endpoint_response()
    )
    monkeypatch.chdir(tmp_path)

    args = _make_args(None, code=None, hello_world=True, create=False)
    rc = _run(harness, args, _make_globals())

    assert rc == 0
    assert (tmp_path / FUNCTION_NAME / 'server.ts').exists()


def test_hello_world_refuses_existing_function(harness, tmp_path, capsys):
    _stub_sts(harness)
    _stub_probe_found(harness)
    harness.lambda_web.add_response(
        'list_web_function_revisions',
        {'revisions': [_revision_summary()]},
    )
    harness.lambda_web.add_response(
        'get_web_function_revision', _existing_revision()
    )
    harness.lambda_web.add_response(
        'list_web_function_endpoints', {'endpoints': [_endpoint_summary()]}
    )

    args = _make_args(str(tmp_path / 'fresh'), hello_world=True)
    rc = _run(harness, args, _make_globals())

    assert rc == 255
    assert '--hello-world' in capsys.readouterr().err
    assert _mutating_calls(harness) == []


def test_hello_world_refuses_non_empty_code_dir(harness, source_dir, capsys):
    args = _make_args(source_dir, hello_world=True)
    rc = _run(harness, args, _make_globals())

    assert rc == 252
    assert 'does not overwrite files' in capsys.readouterr().err
    assert harness.lambda_web.calls == []


def test_hello_world_rejects_entry_point(harness, tmp_path, capsys):
    args = _make_args(
        str(tmp_path / 'fresh'), hello_world=True, entry_point='server.js'
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 255
    assert '--entry-point' in capsys.readouterr().err
    assert harness.lambda_web.calls == []


def test_hello_world_rejects_force_include(harness, tmp_path, capsys):
    target = tmp_path / 'fresh'
    args = _make_args(str(target), hello_world=True, force_include=['.env'])
    rc = _run(harness, args, _make_globals())

    assert rc == 255
    error = capsys.readouterr().err
    assert '--force-include' in error
    assert '--hello-world' in error
    assert not target.exists()
    assert harness.lambda_web.calls == []


def test_hello_world_rejects_nondefault_runtime(harness, tmp_path, capsys):
    args = _make_args(
        str(tmp_path / 'fresh'),
        hello_world=True,
        runtime='nodejs22.x',
    )
    rc = _run(harness, args, _make_globals())

    assert rc == 255
    error = capsys.readouterr().err
    assert '--runtime' in error
    assert constants.DEFAULT_RUNTIME in error
    assert harness.lambda_web.calls == []
