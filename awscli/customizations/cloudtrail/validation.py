# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import base64
import binascii
import hashlib
import json
import logging
import re
import sys
import zlib
from datetime import timedelta
from zlib import error as ZLibError

import rsa
from botocore.exceptions import ClientError
from dateutil import parser, tz
from pyasn1.error import PyAsn1Error

from awscli.compat import get_current_datetime
from awscli.customizations.cloudtrail.utils import (
    get_account_id_from_arn,
    get_trail_by_arn,
)
from awscli.customizations.commands import BasicCommand
from awscli.schema import ParameterRequiredError
from awscli.utils import create_nested_client

LOG = logging.getLogger(__name__)
DATE_FORMAT = '%Y%m%dT%H%M%SZ'
DISPLAY_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def format_date(date):
    """Returns a formatted date string in a CloudTrail date format"""
    return date.strftime(DATE_FORMAT)


def format_display_date(date):
    """Returns a formatted date string meant for CLI output"""
    return date.strftime(DISPLAY_DATE_FORMAT)


def normalize_date(date):
    """Returns a normalized date using a UTC timezone"""
    return date.replace(tzinfo=tz.tzutc())


def is_backfill_digest_key(digest_key):
    """Utility function to determine if a digest key represents a backfill digest file"""
    return digest_key.endswith('_backfill.json.gz')


def extract_digest_key_date(digest_s3_key):
    """Extract the timestamp portion of a manifest file.

    Manifest file names take the following form:
    AWSLogs/{account}/CloudTrail-Digest/{region}/{ymd}/{account}_CloudTrail \
    -Digest_{region}_{name}_region_{date}.json.gz

    For backfill files:
    AWSLogs/{account}/CloudTrail-Digest/{region}/{ymd}/{account}_CloudTrail \
    -Digest_{region}_{name}_region_{date}_backfill.json.gz
    """
    if is_backfill_digest_key(digest_s3_key):
        # Backfill files have _backfill suffix before .json.gz
        return digest_s3_key[-33:-17]
    else:
        # Regular digest files
        return digest_s3_key[-24:-8]


def parse_date(date_string):
    try:
        return parser.parse(date_string)
    except ValueError:
        raise ValueError(f'Unable to parse date value: {date_string}')


def assert_cloudtrail_arn_is_valid(trail_arn):
    """Ensures that the arn looks correct.

    ARNs look like: arn:aws:cloudtrail:us-east-1:123456789012:trail/foo"""
    pattern = re.compile(r'arn:.+:cloudtrail:.+:\d{12}:trail/.+')
    if not pattern.match(trail_arn):
        raise ValueError(f'Invalid trail ARN provided: {trail_arn}')


def create_digest_traverser(
    cloudtrail_client,
    organization_client,
    s3_client_provider,
    trail_arn,
    trail_source_region=None,
    on_invalid=None,
    on_gap=None,
    on_missing=None,
    bucket=None,
    prefix=None,
    account_id=None,
):
    """Creates a CloudTrail DigestTraverser and its object graph.

    :type cloudtrail_client: botocore.client.CloudTrail
    :param cloudtrail_client: Client used to connect to CloudTrail
    :type organization_client: botocore.client.organizations
    :param organization_client: Client used to connect to Organizations
    :type s3_client_provider: S3ClientProvider
    :param s3_client_provider: Used to create Amazon S3 client per/region.
    :param trail_arn: CloudTrail trail ARN
    :param trail_source_region: The scanned region of a trail.
    :param on_invalid: Callback that is invoked when validating a digest fails.
    :param on_gap: Callback that is invoked when a digest has no link to the
        previous digest, but there are more digests to validate. This can
        happen when a trail is disabled for a period of time.
    :param on_missing: Callback that is invoked when a digest file has been
        deleted from Amazon S3 but is supposed to be present.
    :param bucket: Amazon S3 bucket of the trail if it is different than the
        bucket that is currently associated with the trail.
    :param prefix: bucket: Key prefix prepended to each digest and log placed
        in the Amazon S3 bucket if it is different than the prefix that is
        currently associated with the trail.
    :param account_id: The account id for which the digest files are
        validated. For normal trails this is the caller account, for
        organization trails it is the member accout.

    ``on_gap``, ``on_invalid``, and ``on_missing`` callbacks are invoked with
    the following named arguments:

    - ``bucket`: The next S3 bucket.
    - ``next_key``: (optional) Next digest key that was found in the bucket.
    - ``next_end_date``: (optional) End date of the next found digest.
    - ``last_key``: The last digest key that was found.
    - ``last_start_date``: (optional) Start date of last found digest.
    - ``message``: (optional) Message string about the notification.
    """
    assert_cloudtrail_arn_is_valid(trail_arn)
    organization_id = None
    if bucket is None:
        # Determine the bucket and prefix based on the trail arn.
        trail_info = get_trail_by_arn(cloudtrail_client, trail_arn)
        LOG.debug(f'Loaded trail info: {trail_info}')
        bucket = trail_info['S3BucketName']
        prefix = trail_info.get('S3KeyPrefix', None)
        is_org_trail = trail_info.get('IsOrganizationTrail')
        if is_org_trail:
            if not account_id:
                raise ParameterRequiredError(
                    "Missing required parameter for organization "
                    "trail: '--account-id'"
                )
            organization_id = organization_client.describe_organization()[
                'Organization'
            ]['Id']

    # Determine the region from the ARN (e.g., arn:aws:cloudtrail:REGION:...)
    trail_region = trail_arn.split(':')[3]
    # Determine the name from the ARN (the last part after "/")
    trail_name = trail_arn.split('/')[-1]
    # If account id is not specified parse it from trail ARN
    if not account_id:
        account_id = get_account_id_from_arn(trail_arn)

    digest_provider = DigestProvider(
        account_id=account_id,
        trail_name=trail_name,
        s3_client_provider=s3_client_provider,
        trail_source_region=trail_source_region,
        trail_home_region=trail_region,
        organization_id=organization_id,
    )
    return DigestTraverser(
        digest_provider=digest_provider,
        starting_bucket=bucket,
        starting_prefix=prefix,
        on_invalid=on_invalid,
        on_gap=on_gap,
        on_missing=on_missing,
        public_key_provider=PublicKeyProvider(cloudtrail_client),
    )


class S3ClientProvider:
    """Creates Amazon S3 clients and determines the region name of a client.

    This class will cache the location constraints of previously requested
    buckets and cache previously created clients for the same region.
    """

    def __init__(self, session, get_bucket_location_region='us-east-1'):
        self._session = session
        self._get_bucket_location_region = get_bucket_location_region
        self._client_cache = {}
        self._region_cache = {}

    def get_client(self, bucket_name):
        """Creates an S3 client that can work with the given bucket name"""
        region_name = self._get_bucket_region(bucket_name)
        return self._create_client(region_name)

    def _get_bucket_region(self, bucket_name):
        """Returns the region of a bucket"""
        if bucket_name not in self._region_cache:
            client = self._create_client(self._get_bucket_location_region)
            result = client.get_bucket_location(Bucket=bucket_name)
            region = result['LocationConstraint'] or 'us-east-1'
            self._region_cache[bucket_name] = region
        return self._region_cache[bucket_name]

    def _create_client(self, region_name):
        """Creates an Amazon S3 client for the given region name"""
        if region_name not in self._client_cache:
            client = create_nested_client(
                self._session, 's3', region_name=region_name
            )
            # Remove the CLI error event that prevents exceptions.
            self._client_cache[region_name] = client
        return self._client_cache[region_name]


class DigestError(ValueError):
    """Exception raised when a digest fails to validate"""

    pass


class DigestSignatureError(DigestError):
    """Exception raised when a digest signature is invalid"""

    def __init__(self, bucket, key):
        message = (
            f'Digest file\ts3://{bucket}/{key}\tINVALID: signature verification '
            'failed'
        )
        super().__init__(message)


class InvalidDigestFormat(DigestError):
    """Exception raised when a digest has an invalid format"""

    def __init__(self, bucket, key):
        message = f'Digest file\ts3://{bucket}/{key}\tINVALID: invalid format'
        super().__init__(message)


class PublicKeyProvider:
    """Retrieves public keys from CloudTrail within a date range."""

    def __init__(self, cloudtrail_client):
        self._cloudtrail_client = cloudtrail_client

    def get_public_keys(self, start_date, end_date):
        """Loads public keys in a date range into a returned dict.

        :type start_date: datetime
        :param start_date: Start date of a date range.
        :type end_date: datetime
        :param end_date: End date of a date range.
        :rtype: dict
        :return: Returns a dict where each key is the fingerprint of the
            public key, and each value is a dict of public key data.
        """
        public_keys = self._cloudtrail_client.list_public_keys(
            StartTime=start_date, EndTime=end_date
        )
        public_keys_in_range = public_keys['PublicKeyList']
        LOG.debug(f'Loaded public keys in range: {public_keys_in_range}')
        return dict((key['Fingerprint'], key) for key in public_keys_in_range)


class DigestProvider:
    """
    Retrieves digest keys and digests from Amazon S3.

    This class is responsible for determining the full list of digest files
    in a bucket and loading digests from the bucket into a JSON decoded
    dict. This class is not responsible for validation or iterating from
    one digest to the next.
    """

    def __init__(
        self,
        s3_client_provider,
        account_id,
        trail_name,
        trail_home_region,
        trail_source_region=None,
        organization_id=None,
    ):
        self._client_provider = s3_client_provider
        self.trail_name = trail_name
        self.account_id = account_id
        self.trail_home_region = trail_home_region
        self.trail_source_region = trail_source_region or trail_home_region
        self.organization_id = organization_id
        self._digest_cache = {}

    def load_all_digest_keys_in_range(
        self, bucket, prefix, start_date, end_date
    ):
        """Load all digest keys and separate into standard and backfill lists.

        Performs a single S3 list operation and separates keys into standard
        and backfill digest lists during iteration for optimal performance.

        :param bucket: S3 bucket name
        :param prefix: S3 key prefix
        :param start_date: Start date for digest range
        :param end_date: End date for digest range
        :return: Tuple of (standard_digests, backfill_digests) lists
        :rtype: tuple
        """
        standard_digests = []
        backfill_digests = []
        marker = self._create_digest_key(start_date, prefix)
        s3_digest_files_prefix = self._create_digest_prefix(start_date, prefix)
        client = self._client_provider.get_client(bucket)
        paginator = client.get_paginator('list_objects')
        page_iterator = paginator.paginate(
            Bucket=bucket, Marker=marker, Prefix=s3_digest_files_prefix
        )
        key_filter = page_iterator.search('Contents[*].Key')
        # Create a target start end end date
        target_start_date = format_date(normalize_date(start_date))
        # Add one hour to the end_date to get logs that spilled over to next.
        target_end_date = format_date(
            normalize_date(end_date + timedelta(hours=1))
        )
        # Ensure digests are from the same trail.
        digest_key_regex = re.compile(self._create_digest_key_regex(prefix))
        for key in key_filter:
            if not (key and digest_key_regex.match(key)):
                continue
            # Use a lexicographic comparison to know when to stop.
            extracted_date = extract_digest_key_date(key)
            if extracted_date > target_end_date:
                break
            # Only append digests after the start date.
            if extracted_date < target_start_date:
                continue
            if is_backfill_digest_key(key):
                backfill_digests.append(key)
            else:
                standard_digests.append(key)
        return standard_digests, backfill_digests

    def load_digest_keys_in_range(
        self, bucket, prefix, start_date, end_date, is_backfill=False
    ):
        """Returns a list of digest keys in the date range.

        This method uses caching to avoid duplicate S3 list operations.
        On first call, it loads all digest keys and caches them separated
        by type. Subsequent calls return the appropriate cached list.

        :param bucket: S3 bucket name
        :param prefix: S3 key prefix
        :param start_date: Start date for digest range
        :param end_date: End date for digest range
        :param is_backfill: Optional filter - True for backfill digests only,
                           False for standard digests only
        :return: List of digest keys matching the specified type
        :rtype: list
        """
        cache_key = (bucket, prefix, start_date, end_date)

        if cache_key not in self._digest_cache:
            standard_digests, backfill_digests = (
                self.load_all_digest_keys_in_range(
                    bucket, prefix, start_date, end_date
                )
            )
            self._digest_cache[cache_key] = {
                'standard': standard_digests,
                'backfill': backfill_digests,
            }

        if is_backfill:
            return self._digest_cache[cache_key]['backfill']
        else:
            return self._digest_cache[cache_key]['standard']

    def fetch_digest(self, bucket, key):
        """Loads a digest by key from S3.

        Returns the JSON decode data and GZIP inflated raw content.
        For backfill digests, also extracts the backfill-generation-timestamp.
        """
        client = self._client_provider.get_client(bucket)
        result = client.get_object(Bucket=bucket, Key=key)
        try:
            digest = zlib.decompress(
                result['Body'].read(), zlib.MAX_WBITS | 16
            )
            digest_data = json.loads(digest.decode())
        except (ValueError, ZLibError):
            # Cannot gzip decode or JSON parse.
            raise InvalidDigestFormat(bucket, key)
        # Add the expected digest signature and algorithm to the dict.
        if (
            'signature' not in result['Metadata']
            or 'signature-algorithm' not in result['Metadata']
        ):
            raise DigestSignatureError(bucket, key)
        digest_data['_signature'] = result['Metadata']['signature']
        digest_data['_signature_algorithm'] = result['Metadata'][
            'signature-algorithm'
        ]

        if is_backfill_digest_key(key):
            if 'backfill-generation-timestamp' in result['Metadata']:
                digest_data['_backfill_generation_timestamp'] = result[
                    'Metadata'
                ]['backfill-generation-timestamp']
            else:
                raise InvalidDigestFormat(bucket, key)

        return digest_data, digest

    def _create_digest_key(self, start_date, key_prefix):
        """Computes an Amazon S3 key based on the provided data.

        The computed is what would have been placed in the S3 bucket if
        a log digest were created at a specific time. This computed key
        does not have to actually exist as it will only be used to as
        a Marker parameter in a list_objects call.

        :return: Returns a computed key as a string.
        """
        # Subtract one minute to ensure the dates are inclusive.
        date = start_date - timedelta(minutes=1)
        account_id = self.account_id
        date_str = format_date(date)
        ymd = date.strftime('%Y/%m/%d')
        source_region = self.trail_source_region
        home_region = self.trail_home_region
        name = self.trail_name

        if self.organization_id:
            organization_id = self.organization_id
            key = (
                f'AWSLogs/{organization_id}/{account_id}/CloudTrail-Digest/'
                f'{source_region}/{ymd}/{account_id}_CloudTrail-Digest_'
                f'{source_region}_{name}_{home_region}_{date_str}.json.gz'
            )
        else:
            key = (
                f'AWSLogs/{account_id}/CloudTrail-Digest/{source_region}/'
                f'{ymd}/{account_id}_CloudTrail-Digest_{source_region}_{name}_'
                f'{home_region}_{date_str}.json.gz'
            )

        if key_prefix:
            key = key_prefix + '/' + key
        return key

    def _create_digest_prefix(self, start_date, key_prefix):
        """Creates an S3 prefix to scope listing to trail's region.

        :return: Returns a prefix string to limit S3 listing scope.
        """
        template = 'AWSLogs/'
        template_params = {
            'account_id': self.account_id,
            'source_region': self.trail_source_region,
        }
        if self.organization_id:
            template += '{organization_id}/'
            template_params['organization_id'] = self.organization_id
        template += '{account_id}/CloudTrail-Digest/{source_region}'
        prefix = template.format(**template_params)
        if key_prefix:
            prefix = key_prefix + '/' + prefix
        return prefix

    def _create_digest_key_regex(self, key_prefix):
        """Creates a regular expression used to match against S3 keys for both standard and backfill digests"""
        account_id = re.escape(self.account_id)
        source_region = re.escape(self.trail_source_region)
        home_region = re.escape(self.trail_home_region)
        name = re.escape(self.trail_name)

        if self.organization_id:
            organization_id = self.organization_id
            key = (
                f'AWSLogs/{organization_id}/{account_id}/CloudTrail\\-Digest/'
                f'{source_region}/\\d+/\\d+/\\d+/{account_id}_CloudTrail\\-Digest_'
                f'{source_region}_{name}_{home_region}_.+(?:_backfill)?\\.json\\.gz'
            )
        else:
            key = (
                f'AWSLogs/{account_id}/CloudTrail\\-Digest/{source_region}/'
                f'\\d+/\\d+/\\d+/{account_id}_CloudTrail\\-Digest_'
                f'{source_region}_{name}_{home_region}_.+(?:_backfill)?\\.json\\.gz'
            )

        if key_prefix:
            key = re.escape(key_prefix) + '/' + key
        return '^' + key + '$'


class DigestTraverser:
    """Retrieves and validates digests within a date range."""

    # These keys are required to be present before validating the contents
    # of a digest.
    required_digest_keys = [
        'digestPublicKeyFingerprint',
        'digestS3Bucket',
        'digestS3Object',
        'previousDigestSignature',
        'digestEndTime',
        'digestStartTime',
    ]

    def __init__(
        self,
        digest_provider,
        starting_bucket,
        starting_prefix,
        public_key_provider,
        digest_validator=None,
        on_invalid=None,
        on_gap=None,
        on_missing=None,
    ):
        """
        :type digest_provider: DigestProvider
        :param digest_provider: DigestProvider object
        :param starting_bucket: S3 bucket where the digests are stored.
        :param starting_prefix: An optional prefix applied to each S3 key.
        :param public_key_provider: Provides public keys for a range.
        :param digest_validator: Validates digest using a validate method.
        :param on_invalid: Callback invoked when a digest is invalid.
        :param on_gap: Callback invoked when a digest has no parent, but
            there are still more digests to validate.
        :param on_missing: Callback invoked when a digest file is missing.
        """
        self.starting_bucket = starting_bucket
        self.starting_prefix = starting_prefix
        self.digest_provider = digest_provider
        self._public_key_provider = public_key_provider
        self._on_gap = on_gap
        self._on_invalid = on_invalid
        self._on_missing = on_missing
        if digest_validator is None:
            digest_validator = Sha256RSADigestValidator()
        self._digest_validator = digest_validator

    def traverse_digests(self, start_date, end_date=None, is_backfill=False):
        """Creates and returns a generator that yields validated digest data.

        Each yielded digest dictionary contains information about the digest
        and the log file associated with the digest. Digest files are validated
        before they are yielded. Whether or not the digest is successfully
        validated is stated in the "isValid" key value pair of the yielded
        dictionary.

        :type start_date: datetime
        :param start_date: Date to start validating from (inclusive).
        :type end_date: datetime
        :param end_date: Date to stop validating at (inclusive).
        :type is_backfill: bool
        :param is_backfill: Flag indicating whether to process backfill digests only.
        """
        if end_date is None:
            end_date = get_current_datetime()
        end_date = normalize_date(end_date)
        start_date = normalize_date(start_date)
        bucket = self.starting_bucket
        prefix = self.starting_prefix

        digests = self._load_digests(
            bucket, prefix, start_date, end_date, is_backfill=is_backfill
        )

        # For regular digests, pre-load public keys. For backfill, start with empty dict
        public_keys = (
            {} if is_backfill else self._load_public_keys(start_date, end_date)
        )

        yield from self._traverse_digest_chain(
            digests,
            bucket,
            prefix,
            start_date,
            public_keys,
            is_backfill=is_backfill,
        )

    def _traverse_digest_chain(
        self,
        digests,
        bucket,
        prefix,
        start_date,
        public_keys,
        is_backfill=False,
    ):
        """Traverses a single chain of digests

        :param is_backfill: Boolean indicating whether this chain contains backfill digests
        """
        key, end_date = self._get_last_digest(digests)
        last_start_date = end_date

        while key and start_date <= last_start_date:
            try:
                digest, end_date = self._load_and_validate_digest(
                    public_keys, bucket, key, is_backfill=is_backfill
                )
                last_start_date = normalize_date(
                    parse_date(digest['digestStartTime'])
                )
                previous_bucket = digest.get('previousDigestS3Bucket', None)
                previous_key = digest.get('previousDigestS3Object', None)
                yield digest
                if previous_bucket is None or previous_key is None:
                    # The chain is broken, so find next in digest store.
                    key, end_date = self._find_next_digest(
                        digests=digests,
                        bucket=bucket,
                        last_key=key,
                        last_start_date=last_start_date,
                        cb=self._on_gap,
                        is_cb_conditional=True,
                        is_backfill=is_backfill,
                    )
                else:
                    key = previous_key
                    if previous_bucket != bucket:
                        bucket = previous_bucket
                        # The bucket changed so reload the digest list.
                        digests = self._load_digests(
                            bucket,
                            prefix,
                            start_date,
                            end_date,
                            is_backfill=is_backfill,
                        )
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchKey':
                    raise e
                key, end_date = self._find_next_digest(
                    digests=digests,
                    bucket=bucket,
                    last_key=key,
                    last_start_date=last_start_date,
                    cb=self._on_missing,
                    message=str(e),
                    is_backfill=is_backfill,
                )
            except DigestError as e:
                key, end_date = self._find_next_digest(
                    digests=digests,
                    bucket=bucket,
                    last_key=key,
                    last_start_date=last_start_date,
                    cb=self._on_invalid,
                    message=str(e),
                    is_backfill=is_backfill,
                )
            except Exception as e:
                # Any other unexpected errors.
                key, end_date = self._find_next_digest(
                    digests=digests,
                    bucket=bucket,
                    last_key=key,
                    last_start_date=last_start_date,
                    cb=self._on_invalid,
                    message=f'Digest file\ts3://{bucket}/{key}\tINVALID: {str(e)}',
                    is_backfill=is_backfill,
                )

    def _load_digests(
        self, bucket, prefix, start_date, end_date, is_backfill=False
    ):
        return self.digest_provider.load_digest_keys_in_range(
            bucket=bucket,
            prefix=prefix,
            start_date=start_date,
            end_date=end_date,
            is_backfill=is_backfill,
        )

    def _find_next_digest(
        self,
        digests,
        bucket,
        last_key,
        last_start_date,
        cb=None,
        is_cb_conditional=False,
        message=None,
        is_backfill=False,
    ):
        """Finds the next digest in the bucket and invokes any callback."""
        next_key, next_end_date = self._get_last_digest(digests, last_key)
        if cb and (not is_cb_conditional or next_key):
            cb(
                bucket=bucket,
                next_key=next_key,
                last_key=last_key,
                next_end_date=next_end_date,
                last_start_date=last_start_date,
                message=message,
                is_backfill=is_backfill,
            )
        return next_key, next_end_date

    def _get_last_digest(self, digests, before_key=None):
        """Finds the previous digest key (either the last or before before_key)

        If no key is provided, the last digest is used. If a digest is found,
        the end date of the provider is adjusted to match the found key's end
        date.
        """
        if not digests:
            return None, None
        elif before_key is None:
            next_key = digests.pop()
            next_key_date = normalize_date(
                parse_date(extract_digest_key_date(next_key))
            )
            return next_key, next_key_date
        # find a key before the given key.
        before_key_date = parse_date(extract_digest_key_date(before_key))
        while digests:
            next_key = digests.pop()
            next_key_date = normalize_date(
                parse_date(extract_digest_key_date(next_key))
            )
            if next_key_date < before_key_date:
                LOG.debug(f"Next found key: {next_key}")
                return next_key, next_key_date
        return None, None

    def _load_and_validate_digest(
        self, public_keys, bucket, key, is_backfill=False
    ):
        """Loads and validates a digest from S3.

        :param public_keys: Public key dictionary of fingerprint to dict.
        :param bucket: S3 bucket name
        :param key: S3 key for the digest file
        :param is_backfill: Flag indicating if this is a backfill digest
        :return: Returns a tuple of the digest data as a dict and end_date
        :rtype: tuple
        """
        digest_data, digest = self.digest_provider.fetch_digest(bucket, key)

        # Validate required keys are present
        for required_key in self.required_digest_keys:
            if required_key not in digest_data:
                raise InvalidDigestFormat(bucket, key)

        # Ensure the bucket and key are the same as what's expected
        if (
            digest_data['digestS3Bucket'] != bucket
            or digest_data['digestS3Object'] != key
        ):
            raise DigestError(
                f'Digest file\ts3://{bucket}/{key}\tINVALID: has been moved from its '
                'original location'
            )

        fingerprint = digest_data['digestPublicKeyFingerprint']
        if fingerprint not in public_keys and is_backfill:
            # Backfill-specific logic to fetch public keys
            backfill_timestamp = normalize_date(
                parse_date(digest_data['_backfill_generation_timestamp'])
            )
            start_time = backfill_timestamp - timedelta(hours=1)
            end_time = backfill_timestamp + timedelta(hours=1)
            public_keys.update(self._load_public_keys(start_time, end_time))

        if fingerprint not in public_keys:
            error_message = (
                f'Digest file\ts3://{bucket}/{key}\tINVALID: public key not found in '
                f'region {self.digest_provider.trail_home_region} for fingerprint {fingerprint}'
            )
            raise DigestError(error_message)

        public_key_hex = public_keys[fingerprint]['Value']
        self._digest_validator.validate(
            bucket, key, public_key_hex, digest_data, digest
        )

        end_date = normalize_date(parse_date(digest_data['digestEndTime']))
        return digest_data, end_date

    def _load_public_keys(self, start_date, end_date):
        public_keys = self._public_key_provider.get_public_keys(
            start_date, end_date
        )
        if not public_keys:
            raise RuntimeError(
                f'No public keys found between {format_display_date(start_date)} and {format_display_date(end_date)}'
            )
        return public_keys


class Sha256RSADigestValidator:
    """
    Validates SHA256withRSA signed digests.

    The result of validating the digest is inserted into the digest_data
    dictionary using the isValid key value pair.
    """

    def validate(self, bucket, key, public_key, digest_data, inflated_digest):
        """Validates a digest file.

        Throws a DigestError when the digest is invalid.

        :param bucket: Bucket of the digest file
        :param key: Key of the digest file
        :param public_key: Public key bytes.
        :param digest_data: Dict of digest data returned when JSON
            decoding a manifest.
        :param inflated_digest: Inflated digest file contents as bytes.
        """
        try:
            decoded_key = base64.b64decode(public_key)
            public_key = rsa.PublicKey.load_pkcs1(decoded_key, format='DER')
            to_sign = self._create_string_to_sign(digest_data, inflated_digest)
            signature_bytes = binascii.unhexlify(digest_data['_signature'])
            rsa.verify(to_sign, signature_bytes, public_key)
        except PyAsn1Error:
            raise DigestError(
                f'Digest file\ts3://{bucket}/{key}\tINVALID: Unable to load PKCS #1 key'
                f' with fingerprint {digest_data["digestPublicKeyFingerprint"]}'
            )
        except rsa.pkcs1.VerificationError:
            # Note from the Python-RSA docs: Never display the stack trace of
            # a rsa.pkcs1.VerificationError exception. It shows where in the
            # code the exception occurred, and thus leaks information about
            # the key.
            raise DigestSignatureError(bucket, key)

    def _create_string_to_sign(self, digest_data, inflated_digest):
        previous_signature = digest_data['previousDigestSignature']
        if previous_signature is None:
            # The value must be 'null' to match the Java implementation.
            previous_signature = 'null'

        string_to_sign = f"{digest_data['digestEndTime']}\n{digest_data['digestS3Bucket']}/{digest_data['digestS3Object']}\n{hashlib.sha256(inflated_digest).hexdigest()}\n{previous_signature}"
        LOG.debug(f'Digest string to sign: {string_to_sign}')
        return string_to_sign.encode()


class CloudTrailValidateLogs(BasicCommand):
    """
    Validates log digests and log files, optionally saving them to disk.
    """

    NAME = 'validate-logs'
    DESCRIPTION = """
    Validates CloudTrail logs for a given period of time.

    This command uses the digest files delivered to your S3 bucket to perform
    the validation. It supports validation of both digest files and
    backfill digest files in a single run.

    The AWS CLI allows you to detect the following types of changes:

    - Modification or deletion of CloudTrail log files.
    - Modification or deletion of CloudTrail digest files.

    To validate log files with the AWS CLI, the following preconditions must
    be met:

    - You must have online connectivity to AWS.
    - You must have read access to the S3 bucket that contains the digest and
      log files.
    - The digest and log files must not have been moved from the original S3
      location where CloudTrail delivered them.
    - For organization trails you must have access to describe-organization to
      validate digest files

    When you disable Log File Validation, the chain of digest files is broken
    after one hour. CloudTrail will not digest log files that were delivered
    during a period in which the Log File Validation feature was disabled.
    For example, if you enable Log File Validation on January 1, disable it
    on January 2, and re-enable it on January 10, digest files will not be
    created for the log files delivered from January 3 to January 9. The same
    applies whenever you stop CloudTrail logging or delete a trail.

    .. note::

        Log files that have been downloaded to local disk cannot be validated
        with the AWS CLI. The CLI will download all log files each time this
        command is executed.

    .. note::

        This command requires that the role executing the command has
        permission to call ListObjects, GetObject, and GetBucketLocation for
        each bucket referenced by the trail.

    """

    ARG_TABLE = [
        {
            'name': 'trail-arn',
            'required': True,
            'cli_type_name': 'string',
            'help_text': 'Specifies the ARN of the trail to be validated',
        },
        {
            'name': 'start-time',
            'required': True,
            'cli_type_name': 'string',
            'help_text': (
                'Specifies that log files delivered on or after the '
                'specified UTC timestamp value will be validated. '
                'Example: "2015-01-08T05:21:42Z".'
            ),
        },
        {
            'name': 'end-time',
            'cli_type_name': 'string',
            'help_text': (
                'Optionally specifies that log files delivered on or '
                'before the specified UTC timestamp value will be '
                'validated. The default value is the current time. '
                'Example: "2015-01-08T12:31:41Z".'
            ),
        },
        {
            'name': 's3-bucket',
            'cli_type_name': 'string',
            'help_text': (
                'Optionally specifies the S3 bucket where the digest '
                'files are stored. If a bucket name is not specified, '
                'the CLI will retrieve it by calling describe_trails'
            ),
        },
        {
            'name': 's3-prefix',
            'cli_type_name': 'string',
            'help_text': (
                'Optionally specifies the optional S3 prefix where the '
                'digest files are stored. If not specified, the CLI '
                'will determine the prefix automatically by calling '
                'describe_trails.'
            ),
        },
        {
            'name': 'account-id',
            'cli_type_name': 'string',
            'help_text': (
                'Optionally specifies the account for validating logs. '
                'This parameter is needed for organization trails '
                'for validating logs for specific account inside an '
                'organization'
            ),
        },
        {
            'name': 'verbose',
            'cli_type_name': 'boolean',
            'action': 'store_true',
            'help_text': 'Display verbose log validation information',
        },
    ]

    def __init__(self, session):
        super().__init__(session)
        self.trail_arn = None
        self.is_verbose = False
        self.start_time = None
        self.end_time = None
        self.s3_bucket = None
        self.s3_prefix = None
        self.s3_client_provider = None
        self.cloudtrail_client = None
        self.account_id = None
        self._source_region = None
        self._valid_digests = 0
        self._invalid_digests = 0
        self._valid_backfill_digests = 0
        self._invalid_backfill_digests = 0
        self._valid_logs = 0
        self._invalid_logs = 0
        self._is_last_status_double_space = True
        self._found_start_time = None
        self._found_end_time = None

    def _run_main(self, args, parsed_globals):
        self.handle_args(args)
        self.setup_services(parsed_globals)
        self._call()
        total_invalid_digests = (
            self._invalid_digests + self._invalid_backfill_digests
        )
        if total_invalid_digests > 0 or self._invalid_logs > 0:
            return 1
        return 0

    def handle_args(self, args):
        self.trail_arn = args.trail_arn
        self.is_verbose = args.verbose
        self.s3_bucket = args.s3_bucket
        self.s3_prefix = args.s3_prefix
        self.account_id = args.account_id
        self.start_time = normalize_date(parse_date(args.start_time))
        if args.end_time:
            self.end_time = normalize_date(parse_date(args.end_time))
        else:
            self.end_time = normalize_date(get_current_datetime())
        if self.start_time > self.end_time:
            raise ValueError(
                'Invalid time range specified: start-time must '
                'occur before end-time'
            )

    def setup_services(self, parsed_globals):
        self._source_region = parsed_globals.region
        # Use the the same region as the region of the CLI to get locations.
        self.s3_client_provider = S3ClientProvider(
            self._session, self._source_region
        )
        client_args = {
            'region_name': parsed_globals.region,
            'verify': parsed_globals.verify_ssl,
        }
        self.organization_client = create_nested_client(
            self._session, 'organizations', **client_args
        )

        if parsed_globals.endpoint_url is not None:
            client_args['endpoint_url'] = parsed_globals.endpoint_url
        self.cloudtrail_client = create_nested_client(
            self._session, 'cloudtrail', **client_args
        )

    def _call(self):
        traverser = create_digest_traverser(
            trail_arn=self.trail_arn,
            cloudtrail_client=self.cloudtrail_client,
            organization_client=self.organization_client,
            trail_source_region=self._source_region,
            s3_client_provider=self.s3_client_provider,
            bucket=self.s3_bucket,
            prefix=self.s3_prefix,
            on_missing=self._on_missing_digest,
            on_invalid=self._on_invalid_digest,
            on_gap=self._on_digest_gap,
            account_id=self.account_id,
        )
        self._write_startup_text()

        digests = traverser.traverse_digests(
            self.start_time, self.end_time, is_backfill=False
        )
        for digest in digests:
            # Only valid digests are yielded and only valid digests can adjust
            # the found times that are reported in the CLI output summary.
            self._track_found_times(digest)

            self._valid_digests += 1

            self._write_status(
                f'Digest file\ts3://{digest["digestS3Bucket"]}/{digest["digestS3Object"]}\tvalid'
            )

            if not digest['logFiles']:
                continue
            for log in digest['logFiles']:
                self._download_log(log)

        backfill_digests = traverser.traverse_digests(
            self.start_time, self.end_time, is_backfill=True
        )
        for digest in backfill_digests:
            # Only valid digests are yielded and only valid digests can adjust
            # the found times that are reported in the CLI output summary.
            self._track_found_times(digest)

            self._valid_backfill_digests += 1

            self._write_status(
                f'(backfill) Digest file\ts3://{digest["digestS3Bucket"]}/{digest["digestS3Object"]}\tvalid'
            )

            if not digest['logFiles']:
                continue
            for log in digest['logFiles']:
                self._download_log(log)

        self._write_summary_text()

    def _track_found_times(self, digest):
        # Track the earliest found start time, but do not use a date before
        # the user supplied start date.
        digest_start_time = parse_date(digest['digestStartTime'])
        earliest_start_time = max(digest_start_time, self.start_time)
        if (
            not self._found_start_time
            or earliest_start_time < self._found_start_time
        ):
            self._found_start_time = earliest_start_time
        # Track the latest found end time from all digest types, but do not exceed
        # the user supplied end time (or the current date).
        digest_end_time = parse_date(digest['digestEndTime'])
        latest_end_time = min(digest_end_time, self.end_time)
        if not self._found_end_time or latest_end_time > self._found_end_time:
            self._found_end_time = latest_end_time

    def _download_log(self, log):
        """Download a log, decompress, and compare SHA256 checksums"""
        try:
            # Create a client that can work with this bucket.
            client = self.s3_client_provider.get_client(log['s3Bucket'])
            response = client.get_object(
                Bucket=log['s3Bucket'], Key=log['s3Object']
            )
            gzip_inflater = zlib.decompressobj(zlib.MAX_WBITS | 16)
            rolling_hash = hashlib.sha256()
            for chunk in iter(lambda: response['Body'].read(2048), b""):
                data = gzip_inflater.decompress(chunk)
                rolling_hash.update(data)
            remaining_data = gzip_inflater.flush()
            if remaining_data:
                rolling_hash.update(remaining_data)
            computed_hash = rolling_hash.hexdigest()
            if computed_hash != log['hashValue']:
                self._on_log_invalid(log)
            else:
                self._valid_logs += 1
                self._write_status(
                    f'Log file\ts3://{log["s3Bucket"]}/{log["s3Object"]}\tvalid'
                )
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                raise
            self._on_missing_log(log)
        except Exception:
            self._on_invalid_log_format(log)

    def _write_status(self, message, is_error=False):
        if is_error:
            if self._is_last_status_double_space:
                sys.stderr.write(f"{message}\n\n")
            else:
                sys.stderr.write(f"\n{message}\n\n")
            self._is_last_status_double_space = True
        elif self.is_verbose:
            self._is_last_status_double_space = False
            sys.stdout.write(f"{message}\n")

    def _write_startup_text(self):
        sys.stdout.write(
            f'Validating log files for trail {self.trail_arn} between {format_display_date(self.start_time)} and {format_display_date(self.end_time)}\n\n'
        )

    def _write_summary_text(self):
        if not self._is_last_status_double_space:
            sys.stdout.write('\n')
        sys.stdout.write(
            f'Results requested for {format_display_date(self.start_time)} to {format_display_date(self.end_time)}\n'
        )

        total_valid_digests = (
            self._valid_digests + self._valid_backfill_digests
        )
        total_invalid_digests = (
            self._invalid_digests + self._invalid_backfill_digests
        )

        if not total_valid_digests and not total_invalid_digests:
            sys.stdout.write('No digests found\n')
            return
        if not self._found_start_time or not self._found_end_time:
            sys.stdout.write('No valid digests found in range\n')
        else:
            sys.stdout.write(
                f'Results found for {format_display_date(self._found_start_time)} to {format_display_date(self._found_end_time)}:\n'
            )

        self._write_ratio(self._valid_digests, self._invalid_digests, 'digest')
        self._write_ratio(
            self._valid_backfill_digests,
            self._invalid_backfill_digests,
            'backfill digest',
        )
        self._write_ratio(self._valid_logs, self._invalid_logs, 'log')

        sys.stdout.write('\n')

    def _write_ratio(self, valid, invalid, name):
        total = valid + invalid
        if total > 0:
            sys.stdout.write(f'\n{valid}/{total} {name} files valid')
            if invalid > 0:
                sys.stdout.write(f', {invalid}/{total} {name} files INVALID')

    def _on_missing_digest(
        self, bucket, last_key, is_backfill=False, **kwargs
    ):
        if is_backfill:
            self._invalid_backfill_digests += 1
        else:
            self._invalid_digests += 1
        digest_type = '(backfill) ' if is_backfill else ''
        self._write_status(
            f'{digest_type}Digest file\ts3://{bucket}/{last_key}\tINVALID: not found',
            True,
        )

    def _on_digest_gap(self, is_backfill=False, **kwargs):
        log_type = '(backfill) ' if is_backfill else ''
        self._write_status(
            f'{log_type}No log files were delivered by CloudTrail between {format_display_date(kwargs["next_end_date"])} and {format_display_date(kwargs["last_start_date"])}',
            True,
        )

    def _on_invalid_digest(self, message, is_backfill=False, **kwargs):
        if is_backfill:
            self._invalid_backfill_digests += 1
        else:
            self._invalid_digests += 1
        digest_type = '(backfill) ' if is_backfill else ''
        self._write_status(f'{digest_type}{message}', True)

    def _on_invalid_log_format(self, log_data):
        self._invalid_logs += 1
        self._write_status(
            f'Log file\ts3://{log_data["s3Bucket"]}/{log_data["s3Object"]}\tINVALID: invalid format',
            True,
        )

    def _on_log_invalid(self, log_data):
        self._invalid_logs += 1
        self._write_status(
            f"Log file\ts3://{log_data['s3Bucket']}/{log_data['s3Object']}\tINVALID: hash value doesn't match",
            True,
        )

    def _on_missing_log(self, log_data):
        self._invalid_logs += 1
        self._write_status(
            f'Log file\ts3://{log_data["s3Bucket"]}/{log_data["s3Object"]}\tINVALID: not found',
            True,
        )
