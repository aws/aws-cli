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
"""S3 bucket management and zip upload for ``lambda-web``.

All functions operate on a caller-provided ``s3_client``; no clients are
created here.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from botocore.exceptions import BotoCoreError, ClientError
from s3transfer import S3Transfer, TransferConfig

from awscli.customizations.lambdaweb import constants, naming, output, policies
from awscli.customizations.lambdaweb.exceptions import (
    BucketNotOwnedError,
    LambdaWebError,
)

LOG = logging.getLogger(__name__)

_BUCKET_NOT_ACCESSIBLE_OVERRIDE_MSG = (
    "Amazon S3 bucket '{0}' isn't accessible. Verify the bucket name and AWS "
    "Region, and confirm that your credentials allow s3:ListBucket. You can "
    "also omit --bucket-name to use a managed bucket."
)
_MANAGED_BUCKET_NOT_ACCESSIBLE_MSG = (
    "Amazon S3 bucket '{0}' isn't accessible. Verify your permissions, or "
    "specify a different bucket with --bucket-name."
)
_CREATE_BUCKET_ERROR_GUIDANCE = {
    'AccessDenied': 'Verify that your credentials allow s3:CreateBucket.',
    'TooManyBuckets': (
        'Delete an unused bucket or request an Amazon S3 bucket quota increase.'
    ),
}


def ensure_bucket(
    s3_client, account_id, region, partition, override_name=None
):
    """Resolve, validate, or create the S3 bucket for code artifacts.

    Existing buckets are checked for access but are not reconfigured.
    """
    if override_name is not None:
        _check_bucket_access(
            s3_client,
            override_name,
            _BUCKET_NOT_ACCESSIBLE_OVERRIDE_MSG,
        )
        return override_name

    name = naming.bucket_name(account_id, region)
    should_create = _check_bucket_access(
        s3_client,
        name,
        _MANAGED_BUCKET_NOT_ACCESSIBLE_MSG,
        allow_create=True,
    )
    if should_create:
        _create_managed_bucket(s3_client, name, region, partition, account_id)
    return name


def _check_bucket_access(
    s3_client, name, not_accessible_msg, allow_create=False
):
    """Return whether managed-bucket creation should be attempted."""
    try:
        s3_client.head_bucket(Bucket=name)
    except ClientError as e:
        status = _http_status(e)
        if allow_create and status in (400, 404):
            return True
        if status in (400, 403, 404):
            raise BucketNotOwnedError(not_accessible_msg.format(name))
        raise
    return False


def upload_zip(s3_client, bucket, function_name, zip_path):
    """Upload ``zip_path`` to S3 and return ``{bucket, key, versionId}``."""
    utc_iso = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    key = f'lambda-web/{function_name}/{utc_iso}-{uuid4().hex[:8]}.zip'
    config = TransferConfig(
        multipart_threshold=constants.S3_MULTIPART_THRESHOLD_BYTES
    )
    transfer = S3Transfer(s3_client, config)
    try:
        transfer.upload_file(
            zip_path,
            bucket,
            key,
            extra_args={'ContentType': 'application/zip'},
        )
    except Exception as e:
        raise LambdaWebError(
            f"Unable to upload the deployment package to Amazon S3 bucket "
            f"'{bucket}'. Verify the bucket name and AWS Region, and confirm "
            'that your credentials allow s3:PutObject.'
        ) from e

    try:
        head = s3_client.head_object(Bucket=bucket, Key=key)
        version_id = head.get('VersionId', '')
    except (BotoCoreError, ClientError):
        # Each deployment uses a unique key, so the object remains unambiguous
        # when the caller cannot read its version ID.
        LOG.debug(
            'Unable to retrieve the uploaded object version ID',
            exc_info=True,
        )
        version_id = ''
        output.progress(
            "Warning: The command couldn't retrieve an Amazon S3 version ID "
            'for the uploaded deployment package. The deployment request will '
            'omit the version ID.'
        )
    return {
        'bucket': bucket,
        'key': key,
        'versionId': version_id,
    }


def _http_status(client_error):
    return client_error.response.get('ResponseMetadata', {}).get(
        'HTTPStatusCode'
    )


def _create_managed_bucket(s3_client, name, region, partition, account_id):
    params = {
        'Bucket': name,
        'BucketNamespace': constants.S3_BUCKET_NAMESPACE,
    }
    # us-east-1 must omit LocationConstraint; every other region requires it.
    if region != 'us-east-1':
        params['CreateBucketConfiguration'] = {'LocationConstraint': region}
    try:
        s3_client.create_bucket(**params)
    except ClientError as e:
        code = e.response.get('Error', {}).get('Code', 'Unknown')
        if code != 'BucketAlreadyOwnedByYou':
            guidance = _CREATE_BUCKET_ERROR_GUIDANCE.get(
                code, 'Retry the command.'
            )
            raise LambdaWebError(
                f"Unable to create managed Amazon S3 bucket '{name}' in AWS "
                f"Region '{region}'. AWS returned {code}. {guidance}"
            ) from e
    _apply_managed_bucket_settings(s3_client, name, partition, account_id)


def _apply_managed_bucket_settings(s3_client, name, partition, account_id):
    try:
        s3_client.put_bucket_policy(
            Bucket=name,
            Policy=policies.bucket_policy_document(
                partition, name, account_id
            ),
        )
    except ClientError as e:
        raise _managed_bucket_setup_error(
            name, 'apply the required bucket policy to', e
        ) from e
    try:
        s3_client.put_bucket_versioning(
            Bucket=name,
            VersioningConfiguration={'Status': 'Enabled'},
        )
    except ClientError as e:
        raise _managed_bucket_setup_error(
            name, 'enable S3 Versioning on', e
        ) from e


def _managed_bucket_setup_error(name, action, error):
    code = error.response.get('Error', {}).get('Code', 'Unknown')
    return LambdaWebError(
        f"Unable to {action} managed Amazon S3 bucket '{name}' (AWS error: "
        f'{code}). The bucket was retained. Resolve the Amazon S3 error. If the '
        'bucket is empty, you can delete it and rerun the command, or specify '
        'another bucket with --bucket-name.'
    )
