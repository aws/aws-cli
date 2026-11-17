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
import re
from unittest import mock

import botocore.session
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from awscli.customizations.lambdaweb import bucket as bucket_module
from awscli.customizations.lambdaweb import constants, naming, policies
from awscli.customizations.lambdaweb.bucket import ensure_bucket, upload_zip
from awscli.customizations.lambdaweb.exceptions import (
    BucketNotOwnedError,
    LambdaWebError,
)

PARTITION = 'aws'
REGION = 'us-west-2'
ACCOUNT_ID = '123456789012'
FUNCTION_NAME = 'my-fn'
MANAGED_BUCKET = naming.bucket_name(ACCOUNT_ID, REGION)
EXPECTED_POLICY = policies.bucket_policy_document(
    PARTITION, MANAGED_BUCKET, ACCOUNT_ID
)
VERSIONING_CONFIG = {'Status': 'Enabled'}


def _make_s3_client(region=REGION):
    session = botocore.session.get_session()
    return session.create_client('s3', region_name=region)


def test_ensure_bucket_user_override_no_mutation():
    # Stubber raises StubResponseError if any unstubbed call is attempted,
    # so queueing only head_bucket guarantees no mutating calls happen.
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_response(
        'head_bucket', {}, expected_params={'Bucket': 'customer-bucket'}
    )
    with stubber:
        result = ensure_bucket(
            client,
            ACCOUNT_ID,
            REGION,
            PARTITION,
            override_name='customer-bucket',
        )
    assert result == 'customer-bucket'
    stubber.assert_no_pending_responses()


def test_ensure_bucket_user_override_allows_cross_region_bucket():
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_response(
        'head_bucket',
        {'BucketRegion': 'us-east-1'},
        expected_params={'Bucket': 'customer-bucket'},
    )
    with stubber:
        result = ensure_bucket(
            client,
            ACCOUNT_ID,
            REGION,
            PARTITION,
            override_name='customer-bucket',
        )
    assert result == 'customer-bucket'
    stubber.assert_no_pending_responses()


@pytest.mark.parametrize('http_status', [400, 403, 404])
def test_ensure_bucket_user_override_404_raises_BucketNotOwned(http_status):
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'head_bucket',
        service_error_code=str(http_status),
        http_status_code=http_status,
        expected_params={'Bucket': 'customer-bucket'},
    )
    with stubber:
        with pytest.raises(BucketNotOwnedError) as excinfo:
            ensure_bucket(
                client,
                ACCOUNT_ID,
                REGION,
                PARTITION,
                override_name='customer-bucket',
            )
    message = str(excinfo.value)
    assert 'customer-bucket' in message
    assert "isn't accessible" in message
    assert 'credentials' in message
    stubber.assert_no_pending_responses()


def test_ensure_bucket_head_200_does_not_reapply_settings():
    # Queueing only head_bucket proves that ensure_bucket does not overwrite
    # policy or versioning changes.
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_response(
        'head_bucket', {}, expected_params={'Bucket': MANAGED_BUCKET}
    )
    with stubber:
        result = ensure_bucket(client, ACCOUNT_ID, REGION, PARTITION)
    assert result == MANAGED_BUCKET
    stubber.assert_no_pending_responses()


def test_ensure_bucket_head_403_raises_with_hint():
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'head_bucket',
        service_error_code='403',
        http_status_code=403,
        expected_params={'Bucket': MANAGED_BUCKET},
    )
    with stubber:
        with pytest.raises(BucketNotOwnedError) as excinfo:
            ensure_bucket(client, ACCOUNT_ID, REGION, PARTITION)
    assert '--bucket-name' in str(excinfo.value)
    assert MANAGED_BUCKET in str(excinfo.value)
    stubber.assert_no_pending_responses()


@pytest.mark.parametrize('http_status', [400, 404])
def test_ensure_bucket_missing_creates_with_policy_and_versioning(http_status):
    # Stubber consumes responses in FIFO order, so this test also locks in
    # the call sequence: head_bucket -> create_bucket -> policy -> versioning.
    # With no encryption response queued, an unexpected PutBucketEncryption
    # call also fails the test.
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'head_bucket',
        service_error_code=str(http_status),
        http_status_code=http_status,
        expected_params={'Bucket': MANAGED_BUCKET},
    )
    stubber.add_response(
        'create_bucket',
        {'Location': f'/{MANAGED_BUCKET}'},
        expected_params={
            'Bucket': MANAGED_BUCKET,
            'BucketNamespace': constants.S3_BUCKET_NAMESPACE,
            'CreateBucketConfiguration': {'LocationConstraint': REGION},
        },
    )
    stubber.add_response(
        'put_bucket_policy',
        {},
        expected_params={'Bucket': MANAGED_BUCKET, 'Policy': EXPECTED_POLICY},
    )
    stubber.add_response(
        'put_bucket_versioning',
        {},
        expected_params={
            'Bucket': MANAGED_BUCKET,
            'VersioningConfiguration': VERSIONING_CONFIG,
        },
    )
    with stubber:
        result = ensure_bucket(client, ACCOUNT_ID, REGION, PARTITION)
    assert result == MANAGED_BUCKET
    stubber.assert_no_pending_responses()


@pytest.mark.parametrize(
    ('operation', 'error_code', 'http_status', 'message_fragment'),
    [
        ('put_bucket_policy', 'AccessDenied', 403, 'bucket policy'),
        ('put_bucket_versioning', 'InternalError', 500, 'S3 Versioning'),
    ],
)
def test_apply_managed_bucket_settings_failure_has_recovery_guidance(
    operation, error_code, http_status, message_fragment
):
    error = ClientError(
        {
            'Error': {'Code': error_code, 'Message': 'setup failed'},
            'ResponseMetadata': {'HTTPStatusCode': http_status},
        },
        operation,
    )
    client = mock.Mock()
    getattr(client, operation).side_effect = error

    with pytest.raises(LambdaWebError) as excinfo:
        bucket_module._apply_managed_bucket_settings(
            client,
            MANAGED_BUCKET,
            PARTITION,
            ACCOUNT_ID,
        )

    message = str(excinfo.value)
    assert error_code in message
    assert message_fragment in message
    assert 'retained' in message
    assert '--bucket-name' in message
    if operation == 'put_bucket_policy':
        client.put_bucket_versioning.assert_not_called()


@pytest.mark.parametrize(
    ('error_code', 'http_status', 'message_fragment'),
    [
        ('AccessDenied', 403, 's3:CreateBucket'),
        ('TooManyBuckets', 400, 'quota'),
        ('InternalError', 500, 'Retry the command'),
    ],
)
def test_create_managed_bucket_error_has_guidance(
    error_code, http_status, message_fragment
):
    error = ClientError(
        {
            'Error': {'Code': error_code, 'Message': 'create failed'},
            'ResponseMetadata': {'HTTPStatusCode': http_status},
        },
        'CreateBucket',
    )
    client = mock.Mock()
    client.create_bucket.side_effect = error

    with pytest.raises(LambdaWebError) as excinfo:
        bucket_module._create_managed_bucket(
            client,
            MANAGED_BUCKET,
            REGION,
            PARTITION,
            ACCOUNT_ID,
        )

    message = str(excinfo.value)
    assert MANAGED_BUCKET in message
    assert REGION in message
    assert error_code in message
    assert message_fragment in message


def test_ensure_bucket_us_east_1_omits_location_constraint():
    region = 'us-east-1'
    managed = naming.bucket_name(ACCOUNT_ID, region)
    expected_policy = policies.bucket_policy_document(
        PARTITION, managed, ACCOUNT_ID
    )
    client = _make_s3_client(region=region)
    stubber = Stubber(client)
    stubber.add_client_error(
        'head_bucket',
        service_error_code='404',
        http_status_code=404,
        expected_params={'Bucket': managed},
    )
    # Expect Bucket + namespace only — no CreateBucketConfiguration in
    # us-east-1.
    stubber.add_response(
        'create_bucket',
        {'Location': f'/{managed}'},
        expected_params={
            'Bucket': managed,
            'BucketNamespace': constants.S3_BUCKET_NAMESPACE,
        },
    )
    stubber.add_response(
        'put_bucket_policy',
        {},
        expected_params={'Bucket': managed, 'Policy': expected_policy},
    )
    stubber.add_response(
        'put_bucket_versioning',
        {},
        expected_params={
            'Bucket': managed,
            'VersioningConfiguration': VERSIONING_CONFIG,
        },
    )
    with stubber:
        result = ensure_bucket(client, ACCOUNT_ID, region, PARTITION)
    assert result == managed
    stubber.assert_no_pending_responses()


def test_ensure_bucket_BucketAlreadyOwnedByYou_swallowed():
    # Race tolerance: a parallel CLI run could create the bucket between our
    # head_bucket and create_bucket calls; ensure_bucket must keep going.
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'head_bucket',
        service_error_code='404',
        http_status_code=404,
        expected_params={'Bucket': MANAGED_BUCKET},
    )
    stubber.add_client_error(
        'create_bucket',
        service_error_code='BucketAlreadyOwnedByYou',
        http_status_code=409,
        expected_params={
            'Bucket': MANAGED_BUCKET,
            'BucketNamespace': constants.S3_BUCKET_NAMESPACE,
            'CreateBucketConfiguration': {'LocationConstraint': REGION},
        },
    )
    stubber.add_response(
        'put_bucket_policy',
        {},
        expected_params={'Bucket': MANAGED_BUCKET, 'Policy': EXPECTED_POLICY},
    )
    stubber.add_response(
        'put_bucket_versioning',
        {},
        expected_params={
            'Bucket': MANAGED_BUCKET,
            'VersioningConfiguration': VERSIONING_CONFIG,
        },
    )
    with stubber:
        result = ensure_bucket(client, ACCOUNT_ID, REGION, PARTITION)
    assert result == MANAGED_BUCKET
    stubber.assert_no_pending_responses()


def test_upload_zip_uses_transfer_config_threshold():
    # Verify that S3Transfer is instantiated with a TransferConfig carrying
    # the expected multipart threshold, and upload_file receives the correct
    # positional and keyword arguments.
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_response(
        'head_object',
        {'VersionId': 'v1'},
        expected_params={'Bucket': MANAGED_BUCKET, 'Key': mock.ANY},
    )

    captured = {}
    real_transfer_config = bucket_module.TransferConfig

    def _capture(**kwargs):
        captured.update(kwargs)
        return real_transfer_config(**kwargs)

    mock_transfer_instance = mock.MagicMock()
    mock_transfer_cls = mock.MagicMock(return_value=mock_transfer_instance)

    with (
        mock.patch.object(bucket_module, 'S3Transfer', mock_transfer_cls),
        mock.patch.object(
            bucket_module, 'TransferConfig', side_effect=_capture
        ),
    ):
        with stubber:
            upload_zip(client, MANAGED_BUCKET, FUNCTION_NAME, '/tmp/fake.zip')

    assert (
        captured['multipart_threshold']
        == constants.S3_MULTIPART_THRESHOLD_BYTES
    )
    mock_transfer_cls.assert_called_once()
    init_args = mock_transfer_cls.call_args
    assert init_args[0][0] is client
    mock_transfer_instance.upload_file.assert_called_once()
    call_args = mock_transfer_instance.upload_file.call_args
    assert call_args[0][0] == '/tmp/fake.zip'
    assert call_args[0][1] == MANAGED_BUCKET
    assert call_args[1]['extra_args'] == {'ContentType': 'application/zip'}
    stubber.assert_no_pending_responses()


def test_upload_zip_failure_raises_friendly_error():
    client = _make_s3_client()
    mock_transfer_instance = mock.MagicMock()
    mock_transfer_instance.upload_file.side_effect = RuntimeError(
        'upload exploded'
    )
    mock_transfer_cls = mock.MagicMock(return_value=mock_transfer_instance)

    with (
        mock.patch.object(bucket_module, 'S3Transfer', mock_transfer_cls),
        pytest.raises(LambdaWebError) as excinfo,
    ):
        upload_zip(client, MANAGED_BUCKET, FUNCTION_NAME, '/tmp/fake.zip')

    message = str(excinfo.value)
    assert MANAGED_BUCKET in message
    assert 's3:PutObject' in message


def test_upload_zip_head_failure_omits_version_id():
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_client_error(
        'head_object',
        service_error_code='AccessDenied',
        http_status_code=403,
        expected_params={'Bucket': MANAGED_BUCKET, 'Key': mock.ANY},
    )
    mock_transfer_instance = mock.MagicMock()
    mock_transfer_cls = mock.MagicMock(return_value=mock_transfer_instance)

    with (
        mock.patch.object(bucket_module, 'S3Transfer', mock_transfer_cls),
        mock.patch.object(bucket_module.output, 'progress') as progress,
    ):
        with stubber:
            result = upload_zip(
                client, MANAGED_BUCKET, FUNCTION_NAME, '/tmp/fake.zip'
            )

    assert result['bucket'] == MANAGED_BUCKET
    assert result['versionId'] == ''
    warning = progress.call_args.args[0]
    assert "couldn't retrieve an Amazon S3 version ID" in warning
    assert 'deployment request will omit the version ID' in warning
    stubber.assert_no_pending_responses()


def test_upload_zip_returns_versionId():
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_response(
        'head_object',
        {'VersionId': 'abc123versionid'},
        expected_params={'Bucket': MANAGED_BUCKET, 'Key': mock.ANY},
    )
    mock_transfer_instance = mock.MagicMock()
    mock_transfer_cls = mock.MagicMock(return_value=mock_transfer_instance)
    with (
        mock.patch.object(bucket_module, 'S3Transfer', mock_transfer_cls),
        mock.patch.object(bucket_module.output, 'progress') as progress,
    ):
        with stubber:
            result = upload_zip(
                client, MANAGED_BUCKET, FUNCTION_NAME, '/tmp/fake.zip'
            )
    assert result['bucket'] == MANAGED_BUCKET
    assert result['key'].startswith(f'lambda-web/{FUNCTION_NAME}/')
    assert result['versionId'] == 'abc123versionid'
    progress.assert_not_called()
    stubber.assert_no_pending_responses()


def test_upload_zip_object_key_format():
    client = _make_s3_client()
    stubber = Stubber(client)
    stubber.add_response(
        'head_object',
        {},
        expected_params={'Bucket': MANAGED_BUCKET, 'Key': mock.ANY},
    )
    mock_transfer_instance = mock.MagicMock()
    mock_transfer_cls = mock.MagicMock(return_value=mock_transfer_instance)
    with (
        mock.patch.object(bucket_module, 'S3Transfer', mock_transfer_cls),
        mock.patch.object(bucket_module.output, 'progress') as progress,
    ):
        with stubber:
            result = upload_zip(
                client, MANAGED_BUCKET, FUNCTION_NAME, '/tmp/fake.zip'
            )
    pattern = re.compile(
        r'^lambda-web/[A-Za-z0-9_-]+/\d{8}T\d{6}Z-[a-f0-9]{8}\.zip$'
    )
    assert pattern.match(
        result['key']
    ), 'key {!r} did not match expected pattern'.format(result['key'])
    # versionId default when head_object returns no VersionId
    assert result['versionId'] == ''
    progress.assert_not_called()
    stubber.assert_no_pending_responses()


def test_upload_zip_works_with_botocore_client_no_upload_file_method():
    # create_nested_client returns a botocore client without the boto3-only
    # ``upload_file`` method, so upload_zip must use S3Transfer.
    client = _make_s3_client()
    # Confirm the precondition: raw botocore client lacks upload_file.
    assert not hasattr(
        client, 'upload_file'
    ), 'botocore client should not have upload_file'

    stubber = Stubber(client)
    stubber.add_response(
        'head_object',
        {'VersionId': 'regression-v1'},
        expected_params={'Bucket': MANAGED_BUCKET, 'Key': mock.ANY},
    )
    # Patch S3Transfer.upload_file at the class level so no real S3 call
    # is made, but the code path through S3Transfer is exercised.
    with mock.patch('s3transfer.S3Transfer.upload_file') as mock_upload:
        with stubber:
            result = upload_zip(
                client, MANAGED_BUCKET, FUNCTION_NAME, '/tmp/fake.zip'
            )

    # Verify upload_file was called with correct positional + keyword args
    mock_upload.assert_called_once()
    args, kwargs = mock_upload.call_args
    assert args[0] == '/tmp/fake.zip'
    assert args[1] == MANAGED_BUCKET
    assert kwargs['extra_args'] == {'ContentType': 'application/zip'}
    assert result['versionId'] == 'regression-v1'
    stubber.assert_no_pending_responses()
