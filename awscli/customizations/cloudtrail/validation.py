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
import codecs
import json
import hashlib
import logging
import re
import sys
import zlib
from zlib import error as ZLibError
from datetime import datetime, timedelta
from dateutil import tz, parser

from pyasn1.error import PyAsn1Error
import rsa

from awscli.customizations.cloudtrail.utils import get_trail_by_arn, \
    get_account_id_from_arn, remove_cli_error_event
from awscli.customizations.commands import BasicCommand
from botocore.exceptions import ClientError


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


def extract_digest_key_date(digest_s3_key):
    """Extract the timestamp portion of a manifest file.

    Manifest file names take the following form:
    AWSLogs/{account}/CloudTrail-Digest/{region}/{ymd}/{account}_CloudTrail \
    -Digest_{region}_{name}_region_{date}.json.gz
    """
    return digest_s3_key[-24:-8]


def parse_date(date_string):
    try:
        return parser.parse(date_string)
    except ValueError:
        raise ValueError('Unable to parse date value: %s' % date_string)


def assert_cloudtrail_arn_is_valid(trail_arn):
    """Ensures that the arn looks correct.

    ARNs look like: arn:aws:cloudtrail:us-east-1:123456789012:trail/foo"""
    pattern = re.compile('arn:.+:cloudtrail:.+:\d{12}:trail/.+')
    if not pattern.match(trail_arn):
        raise ValueError('Invalid trail ARN provided: %s' % trail_arn)


def create_digest_traverser(cloudtrail_client, s3_client_provider, trail_arn,
                            trail_source_region=None, on_invalid=None,
                            on_gap=None, on_missing=None, bucket=None,
                            prefix=None):
    """Creates a CloudTrail DigestTraverser and its object graph.

    :type cloudtrail_client: botocore.client.CloudTrail
    :param cloudtrail_client: Client used to connect to CloudTrail
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
    account_id = get_account_id_from_arn(trail_arn)
    if bucket is None:
        # Determine the bucket and prefix based on the trail arn.
        trail_info = get_trail_by_arn(cloudtrail_client, trail_arn)
        LOG.debug('Loaded trail info: %s', trail_info)
        bucket = trail_info['S3BucketName']
        prefix = trail_info.get('S3KeyPrefix', None)
    # Determine the region from the ARN (e.g., arn:aws:cloudtrail:REGION:...)
    trail_region = trail_arn.split(':')[3]
    # Determine the name from the ARN (the last part after "/")
    trail_name = trail_arn.split('/')[-1]
    digest_provider = DigestProvider(
        account_id=account_id, trail_name=trail_name,
        s3_client_provider=s3_client_provider,
        trail_source_region=trail_source_region,
        trail_home_region=trail_region)
    return DigestTraverser(
        digest_provider=digest_provider, starting_bucket=bucket,
        starting_prefix=prefix, on_invalid=on_invalid, on_gap=on_gap,
        on_missing=on_missing,
        public_key_provider=PublicKeyProvider(cloudtrail_client))


class S3ClientProvider(object):
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
            client = self._session.create_client('s3', region_name)
            # Remove the CLI error event that prevents exceptions.
            remove_cli_error_event(client)
            self._client_cache[region_name] = client
        return self._client_cache[region_name]


class DigestError(ValueError):
    """Exception raised when a digest fails to validate"""
    pass


class DigestSignatureError(DigestError):
    """Exception raised when a digest signature is invalid"""
    def __init__(self, bucket, key):
        message = ('Digest file\ts3://%s/%s\tINVALID: signature verification '
                   'failed') % (bucket, key)
        super(DigestSignatureError, self).__init__(message)


class InvalidDigestFormat(DigestError):
    """Exception raised when a digest has an invalid format"""
    def __init__(self, bucket, key):
        message = 'Digest file\ts3://%s/%s\tINVALID: invalid format' % (bucket,
                                                                        key)
        super(InvalidDigestFormat, self).__init__(message)


class PublicKeyProvider(object):
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
            StartTime=start_date, EndTime=end_date)
        public_keys_in_range = public_keys['PublicKeyList']
        LOG.debug('Loaded public keys in range: %s', public_keys_in_range)
        return dict((key['Fingerprint'], key) for key in public_keys_in_range)


class DigestProvider(object):
    """
    Retrieves digest keys and digests from Amazon S3.

    This class is responsible for determining the full list of digest files
    in a bucket and loading digests from the bucket into a JSON decoded
    dict. This class is not responsible for validation or iterating from
    one digest to the next.
    """
    def __init__(self, s3_client_provider, account_id, trail_name,
                 trail_home_region, trail_source_region=None):
        self._client_provider = s3_client_provider
        self.trail_name = trail_name
        self.account_id = account_id
        self.trail_home_region = trail_home_region
        self.trail_source_region = trail_source_region or trail_home_region

    def load_digest_keys_in_range(self, bucket, prefix, start_date, end_date):
        """Returns a list of digest keys in the date range.

        This method uses a list_objects API call and provides a Marker
        parameter that is calculated based on the start_date provided.
        Amazon S3 then returns all keys in the bucket that start after
        the given key (non-inclusive). We then iterate over the keys
        until the date extracted from the yielded keys is greater than
        the given end_date.
        """
        digests = []
        marker = self._create_digest_key(start_date, prefix)
        client = self._client_provider.get_client(bucket)
        paginator = client.get_paginator('list_objects')
        page_iterator = paginator.paginate(Bucket=bucket, Marker=marker)
        key_filter = page_iterator.search('Contents[*].Key')
        # Create a target start end end date
        target_start_date = format_date(normalize_date(start_date))
        # Add one hour to the end_date to get logs that spilled over to next.
        target_end_date = format_date(
            normalize_date(end_date + timedelta(hours=1)))
        # Ensure digests are from the same trail.
        digest_key_regex = re.compile(self._create_digest_key_regex(prefix))
        for key in key_filter:
            if digest_key_regex.match(key):
                # Use a lexicographic comparison to know when to stop.
                extracted_date = extract_digest_key_date(key)
                if extracted_date > target_end_date:
                    break
                # Only append digests after the start date.
                if extracted_date >= target_start_date:
                    digests.append(key)
        return digests

    def fetch_digest(self, bucket, key):
        """Loads a digest by key from S3.

        Returns the JSON decode data and GZIP inflated raw content.
        """
        client = self._client_provider.get_client(bucket)
        result = client.get_object(Bucket=bucket, Key=key)
        try:
            digest = zlib.decompress(result['Body'].read(),
                                     zlib.MAX_WBITS | 16)
            digest_data = json.loads(digest.decode())
        except (ValueError, ZLibError):
            # Cannot gzip decode or JSON parse.
            raise InvalidDigestFormat(bucket, key)
        # Add the expected digest signature and algorithm to the dict.
        if 'signature' not in result['Metadata'] \
                or 'signature-algorithm' not in result['Metadata']:
            raise DigestSignatureError(bucket, key)
        digest_data['_signature'] = result['Metadata']['signature']
        digest_data['_signature_algorithm'] = \
            result['Metadata']['signature-algorithm']
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
        template = ('AWSLogs/{account}/CloudTrail-Digest/{source_region}/'
                    '{ymd}/{account}_CloudTrail-Digest_{source_region}_{name}_'
                    '{home_region}_{date}.json.gz')
        key = template.format(account=self.account_id, date=format_date(date),
                              ymd=date.strftime('%Y/%m/%d'),
                              source_region=self.trail_source_region,
                              home_region=self.trail_home_region,
                              name=self.trail_name)
        if key_prefix:
            key = key_prefix + '/' + key
        return key

    def _create_digest_key_regex(self, key_prefix):
        """Creates a regular expression used to match against S3 keys"""
        template = ('AWSLogs/{account}/CloudTrail\\-Digest/{source_region}/'
                    '\\d+/\\d+/\\d+/{account}_CloudTrail\\-Digest_'
                    '{source_region}_{name}_{home_region}_.+\\.json\\.gz')
        key = template.format(
            account=re.escape(self.account_id),
            source_region=re.escape(self.trail_source_region),
            home_region=re.escape(self.trail_home_region),
            name=re.escape(self.trail_name))
        if key_prefix:
            key = re.escape(key_prefix) + '/' + key
        return '^' + key + '$'


class DigestTraverser(object):
    """Retrieves and validates digests within a date range."""
    # These keys are required to be present before validating the contents
    # of a digest.
    required_digest_keys = ['digestPublicKeyFingerprint', 'digestS3Bucket',
                            'digestS3Object', 'previousDigestSignature',
                            'digestEndTime', 'digestStartTime']

    def __init__(self, digest_provider, starting_bucket, starting_prefix,
                 public_key_provider, digest_validator=None,
                 on_invalid=None, on_gap=None, on_missing=None):
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

    def traverse(self, start_date, end_date=None):
        """Creates and returns a generator that yields validated digest data.

        Each yielded digest dictionary contains information about the digest
        and the log file associated with the digest. Digest files are validated
        before they are yielded. Whether or not the digest is successfully
        validated is stated in the "isValid" key value pair of the yielded
        dictionary.

        :type start_date: datetime
        :param start_date: Date to start validating from (inclusive).
        :type start_date: datetime
        :param end_date: Date to stop validating at (inclusive).
        """
        if end_date is None:
            end_date = datetime.utcnow()
        end_date = normalize_date(end_date)
        start_date = normalize_date(start_date)
        bucket = self.starting_bucket
        prefix = self.starting_prefix
        digests = self._load_digests(bucket, prefix, start_date, end_date)
        public_keys = self._load_public_keys(start_date, end_date)
        key, end_date = self._get_last_digest(digests)
        last_start_date = end_date
        while key and start_date <= last_start_date:
            try:
                digest, end_date = self._load_and_validate_digest(
                    public_keys, bucket, key)
                last_start_date = normalize_date(
                    parse_date(digest['digestStartTime']))
                previous_bucket = digest.get('previousDigestS3Bucket', None)
                yield digest
                if previous_bucket is None:
                    # The chain is broken, so find next in digest store.
                    key, end_date = self._find_next_digest(
                        digests=digests, bucket=bucket, last_key=key,
                        last_start_date=last_start_date, cb=self._on_gap,
                        is_cb_conditional=True)
                else:
                    key = digest['previousDigestS3Object']
                    if previous_bucket != bucket:
                        bucket = previous_bucket
                        # The bucket changed so reload the digest list.
                        digests = self._load_digests(
                            bucket, prefix, start_date, end_date)
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchKey':
                    raise e
                key, end_date = self._find_next_digest(
                    digests=digests, bucket=bucket, last_key=key,
                    last_start_date=last_start_date, cb=self._on_missing,
                    message=str(e))
            except DigestError as e:
                key, end_date = self._find_next_digest(
                    digests=digests, bucket=bucket, last_key=key,
                    last_start_date=last_start_date, cb=self._on_invalid,
                    message=str(e))
            except Exception as e:
                # Any other unexpected errors.
                key, end_date = self._find_next_digest(
                    digests=digests, bucket=bucket, last_key=key,
                    last_start_date=last_start_date, cb=self._on_invalid,
                    message='Digest file\ts3://%s/%s\tINVALID: %s'
                            % (bucket, key, str(e)))

    def _load_digests(self, bucket, prefix, start_date, end_date):
        return self.digest_provider.load_digest_keys_in_range(
            bucket=bucket, prefix=prefix,
            start_date=start_date, end_date=end_date)

    def _find_next_digest(self, digests, bucket, last_key, last_start_date,
                          cb=None, is_cb_conditional=False, message=None):
        """Finds the next digest in the bucket and invokes any callback."""
        next_key, next_end_date = self._get_last_digest(digests, last_key)
        if cb and (not is_cb_conditional or next_key):
            cb(bucket=bucket, next_key=next_key, last_key=last_key,
               next_end_date=next_end_date, last_start_date=last_start_date,
               message=message)
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
                parse_date(extract_digest_key_date(next_key)))
            return next_key, next_key_date
        # find a key before the given key.
        before_key_date = parse_date(extract_digest_key_date(before_key))
        while digests:
            next_key = digests.pop()
            next_key_date = normalize_date(
                parse_date(extract_digest_key_date(next_key)))
            if next_key_date < before_key_date:
                LOG.debug("Next found key: %s", next_key)
                return next_key, next_key_date
        return None, None

    def _load_and_validate_digest(self, public_keys, bucket, key):
        """Loads and validates a digest from S3.

        :param public_keys: Public key dictionary of fingerprint to dict.
        :return: Returns a tuple of the digest data as a dict and end_date
        :rtype: tuple
        """
        digest_data, digest = self.digest_provider.fetch_digest(bucket, key)
        for required_key in self.required_digest_keys:
            if required_key not in digest_data:
                raise InvalidDigestFormat(bucket, key)
        # Ensure the bucket and key are the same as what's expected.
        if digest_data['digestS3Bucket'] != bucket \
                or digest_data['digestS3Object'] != key:
            raise DigestError(
                ('Digest file\ts3://%s/%s\tINVALID: has been moved from its '
                 'original location') % (bucket, key))
        # Get the public keys in the given time range.
        fingerprint = digest_data['digestPublicKeyFingerprint']
        if fingerprint not in public_keys:
            raise DigestError(
                ('Digest file\ts3://%s/%s\tINVALID: public key not found for '
                 'fingerprint %s') % (bucket, key, fingerprint))
        public_key_hex = public_keys[fingerprint]['Value']
        self._digest_validator.validate(
            bucket, key, public_key_hex, digest_data, digest)
        end_date = normalize_date(parse_date(digest_data['digestEndTime']))
        return digest_data, end_date

    def _load_public_keys(self, start_date, end_date):
        public_keys = self._public_key_provider.get_public_keys(
            start_date, end_date)
        if not public_keys:
            raise RuntimeError(
                'No public keys found between %s and %s' %
                (format_display_date(start_date),
                 format_display_date(end_date)))
        return public_keys


class Sha256RSADigestValidator(object):
    """
    Validates SHA256withRSA signed digests.

    The result of validating the digest is inserted into the digest_data
    dictionary using the isValid key value pair.
    """
    def __init__(self):
        self.hex_decoder = codecs.getdecoder('hex')

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
            signature_bytes = self.hex_decoder(digest_data['_signature'])[0]
            rsa.verify(to_sign, signature_bytes, public_key)
        except PyAsn1Error:
            raise DigestError(
                ('Digest file\ts3://%s/%s\tINVALID: Unable to load PKCS #1 key'
                 ' with fingerprint %s')
                % (bucket, key, digest_data['digestPublicKeyFingerprint']))
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
        string_to_sign = "%s\n%s/%s\n%s\n%s" % (
            digest_data['digestEndTime'],
            digest_data['digestS3Bucket'],
            digest_data['digestS3Object'],
            hashlib.sha256(inflated_digest).hexdigest(),
            previous_signature)
        LOG.debug('Digest string to sign: %s', string_to_sign)
        return string_to_sign.encode()


class CloudTrailValidateLogs(BasicCommand):
    """
    Validates log digests and log files, optionally saving them to disk.
    """
    NAME = 'validate-logs'
    DESCRIPTION = """
    Validates CloudTrail logs for a given period of time.

    This command uses the digest files delivered to your S3 bucket to perform
    the validation.

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
        {'name': 'trail-arn', 'required': True, 'cli_type_name': 'string',
         'help_text': 'Specifies the ARN of the trail to be validated'},
        {'name': 'start-time', 'required': True, 'cli_type_name': 'string',
         'help_text': ('Specifies that log files delivered on or after the '
                       'specified UTC timestamp value will be validated. '
                       'Example: "2015-01-08T05:21:42Z".')},
        {'name': 'end-time', 'cli_type_name': 'string',
         'help_text': ('Optionally specifies that log files delivered on or '
                       'before the specified UTC timestamp value will be '
                       'validated. The default value is the current time. '
                       'Example: "2015-01-08T12:31:41Z".')},
        {'name': 's3-bucket', 'cli_type_name': 'string',
         'help_text': ('Optionally specifies the S3 bucket where the digest '
                       'files are stored. If a bucket name is not specified, '
                       'the CLI will retrieve it by calling describe_trails')},
        {'name': 's3-prefix', 'cli_type_name': 'string',
         'help_text': ('Optionally specifies the optional S3 prefix where the '
                       'digest files are stored. If not specified, the CLI '
                       'will determine the prefix automatically by calling '
                       'describe_trails.')},
        {'name': 'verbose', 'cli_type_name': 'boolean',
         'action': 'store_true',
         'help_text': 'Display verbose log validation information'}
    ]

    def __init__(self, session):
        super(CloudTrailValidateLogs, self).__init__(session)
        self.trail_arn = None
        self.is_verbose = False
        self.start_time = None
        self.end_time = None
        self.s3_bucket = None
        self.s3_prefix = None
        self.s3_client_provider = None
        self.cloudtrail_client = None
        self._source_region = None
        self._valid_digests = 0
        self._invalid_digests = 0
        self._valid_logs = 0
        self._invalid_logs = 0
        self._is_last_status_double_space = True
        self._found_start_time = None
        self._found_end_time = None

    def _run_main(self, args, parsed_globals):
        self.handle_args(args)
        self.setup_services(args, parsed_globals)
        self._call()
        if self._invalid_digests > 0 or self._invalid_logs > 0:
            return 1
        return 0

    def handle_args(self, args):
        self.trail_arn = args.trail_arn
        self.is_verbose = args.verbose
        self.s3_bucket = args.s3_bucket
        self.s3_prefix = args.s3_prefix
        self.start_time = normalize_date(parse_date(args.start_time))
        if args.end_time:
            self.end_time = normalize_date(parse_date(args.end_time))
        else:
            self.end_time = normalize_date(datetime.utcnow())
        if self.start_time > self.end_time:
            raise ValueError(('Invalid time range specified: start-time must '
                              'occur before end-time'))
        # Found start time always defaults to the given start time. This value
        # may change if the earliest found digest is after the given start
        # time. Note that the summary output report of what date ranges were
        # actually found is only shown if a valid digest is encountered,
        # thereby setting self._found_end_time to a value.
        self._found_start_time = self.start_time

    def setup_services(self, args, parsed_globals):
        self._source_region = parsed_globals.region
        # Use the the same region as the region of the CLI to get locations.
        self.s3_client_provider = S3ClientProvider(
            self._session, self._source_region)
        client_args = {'region_name': parsed_globals.region,
                       'verify': parsed_globals.verify_ssl}
        if parsed_globals.endpoint_url is not None:
            client_args['endpoint_url'] = parsed_globals.endpoint_url
        self.cloudtrail_client = self._session.create_client(
            'cloudtrail', **client_args)

    def _call(self):
        traverser = create_digest_traverser(
            trail_arn=self.trail_arn, cloudtrail_client=self.cloudtrail_client,
            trail_source_region=self._source_region,
            s3_client_provider=self.s3_client_provider, bucket=self.s3_bucket,
            prefix=self.s3_prefix, on_missing=self._on_missing_digest,
            on_invalid=self._on_invalid_digest, on_gap=self._on_digest_gap)
        self._write_startup_text()
        digests = traverser.traverse(self.start_time, self.end_time)
        for digest in digests:
            # Only valid digests are yielded and only valid digests can adjust
            # the found times that are reported in the CLI output summary.
            self._track_found_times(digest)
            self._valid_digests += 1
            self._write_status(
                'Digest file\ts3://%s/%s\tvalid'
                % (digest['digestS3Bucket'], digest['digestS3Object']))
            if not digest['logFiles']:
                continue
            for log in digest['logFiles']:
                self._download_log(log, digest)
        self._write_summary_text()

    def _track_found_times(self, digest):
        # Track the earliest found start time, but do not use a date before
        # the user supplied start date.
        digest_start_time = parse_date(digest['digestStartTime'])
        if digest_start_time > self.start_time:
            self._found_start_time = digest_start_time
        # Only use the last found end time if it is less than the
        # user supplied end time (or the current date).
        if not self._found_end_time:
            digest_end_time = parse_date(digest['digestEndTime'])
            self._found_end_time = min(digest_end_time, self.end_time)

    def _download_log(self, log, digest_data):
        """ Download a log, decompress, and compare SHA256 checksums"""
        try:
            # Create a client that can work with this bucket.
            client = self.s3_client_provider.get_client(log['s3Bucket'])
            response = client.get_object(
                Bucket=log['s3Bucket'], Key=log['s3Object'])
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
                self._write_status(('Log file\ts3://%s/%s\tvalid'
                                    % (log['s3Bucket'], log['s3Object'])))
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                raise
            self._on_missing_log(log)
        except Exception:
            self._on_invalid_log_format(log)

    def _write_status(self, message, is_error=False):
        if is_error:
            if self._is_last_status_double_space:
                sys.stderr.write("%s\n\n" % message)
            else:
                sys.stderr.write("\n%s\n\n" % message)
            self._is_last_status_double_space = True
        elif self.is_verbose:
            self._is_last_status_double_space = False
            sys.stdout.write("%s\n" % message)

    def _write_startup_text(self):
        sys.stdout.write(
            'Validating log files for trail %s between %s and %s\n\n'
            % (self.trail_arn, format_display_date(self.start_time),
               format_display_date(self.end_time)))

    def _write_summary_text(self):
        if not self._is_last_status_double_space:
            sys.stdout.write('\n')
        sys.stdout.write('Results requested for %s to %s\n'
                         % (format_display_date(self.start_time),
                            format_display_date(self.end_time)))
        if not self._valid_digests and not self._invalid_digests:
            sys.stdout.write('No digests found\n')
            return
        if not self._found_start_time or not self._found_end_time:
            sys.stdout.write('No valid digests found in range\n')
        else:
            sys.stdout.write('Results found for %s to %s:\n'
                             % (format_display_date(self._found_start_time),
                                format_display_date(self._found_end_time)))
        self._write_ratio(self._valid_digests, self._invalid_digests, 'digest')
        self._write_ratio(self._valid_logs, self._invalid_logs, 'log')
        sys.stdout.write('\n')

    def _write_ratio(self, valid, invalid, name):
        total = valid + invalid
        if total > 0:
            sys.stdout.write('\n%d/%d %s files valid' % (valid, total, name))
            if invalid > 0:
                sys.stdout.write(', %d/%d %s files INVALID' % (invalid, total,
                                                               name))

    def _on_missing_digest(self, bucket, last_key, **kwargs):
        self._invalid_digests += 1
        self._write_status('Digest file\ts3://%s/%s\tINVALID: not found'
                           % (bucket, last_key), True)

    def _on_digest_gap(self, **kwargs):
        self._write_status(
            'No log files were delivered by CloudTrail between %s and %s'
            % (format_display_date(kwargs['next_end_date']),
               format_display_date(kwargs['last_start_date'])), True)

    def _on_invalid_digest(self, message, **kwargs):
        self._invalid_digests += 1
        self._write_status(message, True)

    def _on_invalid_log_format(self, log_data):
        self._invalid_logs += 1
        self._write_status(
            ('Log file\ts3://%s/%s\tINVALID: invalid format'
             % (log_data['s3Bucket'], log_data['s3Object'])), True)

    def _on_log_invalid(self, log_data):
        self._invalid_logs += 1
        self._write_status(
            "Log file\ts3://%s/%s\tINVALID: hash value doesn't match"
            % (log_data['s3Bucket'], log_data['s3Object']), True)

    def _on_missing_log(self, log_data):
        self._invalid_logs += 1
        self._write_status(
            'Log file\ts3://%s/%s\tINVALID: not found'
            % (log_data['s3Bucket'], log_data['s3Object']), True)
