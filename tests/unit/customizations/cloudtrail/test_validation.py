# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License'). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the 'license' file accompanying this file. This file is
# distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import base64
import binascii
import gzip
import hashlib
import json
from argparse import Namespace
from datetime import datetime, timedelta

import rsa
from botocore.exceptions import ClientError
from dateutil import parser, tz

from awscli.compat import BytesIO
from awscli.customizations.cloudtrail.validation import (
    DATE_FORMAT,
    CloudTrailValidateLogs,
    DigestError,
    DigestProvider,
    DigestSignatureError,
    DigestTraverser,
    InvalidDigestFormat,
    PublicKeyProvider,
    S3ClientProvider,
    Sha256RSADigestValidator,
    assert_cloudtrail_arn_is_valid,
    create_digest_traverser,
    extract_digest_key_date,
    format_date,
    is_backfill_digest_key,
    normalize_date,
    parse_date,
)
from awscli.schema import ParameterRequiredError
from awscli.testutils import BaseAWSCommandParamsTest, mock, unittest

START_DATE = parser.parse('20140810T000000Z')
END_DATE = parser.parse('20150810T000000Z')
TEST_ACCOUNT_ID = '123456789012'
TEST_TRAIL_ARN = f'arn:aws:cloudtrail:us-east-1:{TEST_ACCOUNT_ID}:trail/foo'
VALID_TEST_KEY = (
    'MIIBCgKCAQEAn11L2YZ9h7onug2ILi1MWyHiMRsTQjfWE+pHVRLk1QjfW'
    'hirG+lpOa8NrwQ/r7Ah5bNL6HepznOU9XTDSfmmnP97mqyc7z/upfZdS/'
    'AHhYcGaz7n6Wc/RRBU6VmiPCrAUojuSk6/GjvA8iOPFsYDuBtviXarvuL'
    'PlrT9kAd4Lb+rFfR5peEgBEkhlzc5HuWO7S0y+KunqxX6jQBnXGMtxmPB'
    'PP0FylgWGNdFtks/4YSKcgqwH0YDcawP9GGGDAeCIqPWIXDLG1jOjRRzW'
    'fCmD0iJUkz8vTsn4hq/5ZxRFE7UBAUiVcGbdnDdvVfhF9C3dQiDq3k7ad'
    'QIziLT0cShgQIDAQAB'
)
TEST_ORGANIZATION_ACCOUNT_ID = '987654321098'
TEST_ORGANIZATION_ID = 'o-12345'


def create_mock_key_provider(key_list):
    """Creates a mock key provider that yields keys for each in key_list"""
    public_keys = {}
    for k in key_list:
        public_keys[k] = {'Fingerprint': k, 'Value': 'ffaa00'}
    key_provider = mock.Mock()
    key_provider.get_public_keys.return_value = public_keys
    return key_provider


def create_scenario(actions, logs=None):
    """Creates a scenario for a stack of actions

    Each action can be "gap" meaning there is no previous link, "invalid"
    meaning we should simulate an invalid digest, "missing" meaning we
    should simulate a digest is missing from S3, "bucket_change" meaning
    it is a link but the bucket is different than the previous bucket.
    Values are popped one by one off of the list until a terminal "gap"
    action is found.
    """
    keys = [str(i) for i in range(len(actions))]
    key_provider = create_mock_key_provider(keys)
    digest_provider = MockDigestProvider(actions, logs)
    digest_validator = mock.Mock()

    def validate(bucket, key, public_key, digest_data, digest_str):
        if '_invalid' in digest_data:
            raise DigestError('invalid error')

    digest_validator.validate = validate
    return key_provider, digest_provider, digest_validator


def collecting_callback():
    """Create and return a callback and a list populated with call args"""
    calls = []

    def cb(**kwargs):
        calls.append(kwargs)

    return cb, calls


class MockDigestProvider:
    def __init__(self, actions, logs=None):
        self.logs = logs or []
        self.actions = actions
        self.calls = {'fetch_digest': [], 'load_digest_keys_in_range': []}
        self.digests = []
        self.backfill_digests = []
        self.trail_home_region = 'us-east-1'
        for i in range(len(self.actions)):
            self.digests.append(self.get_key_at_position(i))
            self.backfill_digests.append(
                self.get_key_at_position(i, is_backfill=True)
            )

    def get_key_at_position(self, position, is_backfill=False):
        """Get digest key at position, generating backfill keys if needed."""
        dt = START_DATE + timedelta(hours=position)

        if is_backfill:
            key = (
                f'AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1/{dt.strftime("%Y/%m/%d")}/'
                f'{TEST_ACCOUNT_ID}_CloudTrail-Digest_us-east-1_foo_us-east-1_{dt.strftime(DATE_FORMAT)}_backfill.json.gz'
            )
        else:
            key = (
                f'AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1/{dt.strftime("%Y/%m/%d")}/'
                f'{TEST_ACCOUNT_ID}_CloudTrail-Digest_us-east-1_foo_us-east-1_{dt.strftime(DATE_FORMAT)}.json.gz'
            )
        return key

    @staticmethod
    def create_digest(
        fingerprint,
        start_date,
        key,
        bucket,
        next_key=None,
        next_bucket=None,
        logs=None,
    ):
        digest_end_date = start_date + timedelta(hours=1, minutes=30)
        return {
            'digestPublicKeyFingerprint': fingerprint,
            'digestEndTime': digest_end_date.strftime(DATE_FORMAT),
            'digestStartTime': start_date.strftime(DATE_FORMAT),
            'previousDigestS3Bucket': next_bucket,
            'previousDigestS3Object': next_key,
            'digestS3Bucket': bucket,
            'digestS3Object': key,
            'awsAccountId': TEST_ACCOUNT_ID,
            'previousDigestSignature': 'abcd',
            'logFiles': logs or [],
        }

    @staticmethod
    def create_link(
        key, next_key, next_bucket, position, action, logs, bucket
    ):
        """Creates a link in a digest chain for testing."""
        digest_logs = []
        if len(logs) > position:
            digest_logs = logs[position]
        end_date = parse_date(extract_digest_key_date(key))
        # gap actions have no previous link.
        if action == 'gap':
            digest = MockDigestProvider.create_digest(
                key=key,
                bucket=bucket,
                fingerprint=str(position),
                start_date=end_date,
                logs=digest_logs,
            )
        else:
            digest = MockDigestProvider.create_digest(
                key=key,
                bucket=bucket,
                fingerprint=str(position),
                start_date=end_date,
                next_bucket=next_bucket,
                next_key=next_key,
                logs=digest_logs,
            )
            if action == 'invalid':
                digest['_invalid'] = True

        digest['_signature'] = 'mock_signature'
        digest['_signature_algorithm'] = 'SHA256'

        if is_backfill_digest_key(key):
            digest['_backfill_generation_timestamp'] = '2025-09-01T00:00:00Z'

        return digest, json.dumps(digest)

    def load_digest_keys_in_range(
        self, bucket, prefix, start_date, end_date, is_backfill=False
    ):
        self.calls['load_digest_keys_in_range'].append(locals())
        if is_backfill:
            return list(self.backfill_digests)
        return list(self.digests)

    def fetch_digest(self, bucket, key):
        self.calls['fetch_digest'].append(key)
        position = (
            self.backfill_digests.index(key)
            if is_backfill_digest_key(key)
            else self.digests.index(key)
        )
        action = self.actions[position]
        # Simulate a digest missing from S3
        if action == 'missing':
            raise ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'foo'}}, 'GetObject'
            )

        next_key = self.get_key_at_position(
            position - 1, is_backfill_digest_key(key)
        )
        next_bucket = int(bucket)
        if action == 'bucket_change':
            next_bucket += 1

        return self.create_link(
            key,
            next_key,
            str(next_bucket),
            position,
            action,
            self.logs,
            bucket,
        )


class TestValidation(unittest.TestCase):
    def test_formats_dates(self):
        date = datetime(2015, 8, 21, tzinfo=tz.tzutc())
        self.assertEqual('20150821T000000Z', format_date(date))

    def test_parses_dates_with_better_error_message(self):
        try:
            parse_date('foo')
            self.fail('Should have failed to parse')
        except ValueError as e:
            self.assertIn('Unable to parse date value: foo', str(e))

    def test_parses_dates(self):
        date = parse_date('August 25, 2015 00:00:00 UTC')
        self.assertEqual(date, datetime(2015, 8, 25, tzinfo=tz.tzutc()))

    def test_ensures_cloudtrail_arns_are_valid(self):
        try:
            assert_cloudtrail_arn_is_valid('foo:bar:baz')
            self.fail('Should have failed')
        except ValueError as e:
            self.assertIn('Invalid trail ARN provided: foo:bar:baz', str(e))

    def test_ensures_cloudtrail_arns_are_valid_when_missing_resource(self):
        try:
            assert_cloudtrail_arn_is_valid(
                f'arn:aws:cloudtrail:us-east-1:{TEST_ACCOUNT_ID}:foo'
            )
            self.fail('Should have failed')
        except ValueError as e:
            self.assertIn('Invalid trail ARN provided', str(e))

    def test_allows_valid_arns(self):
        assert_cloudtrail_arn_is_valid(
            f'arn:aws:cloudtrail:us-east-1:{TEST_ACCOUNT_ID}:trail/foo'
        )

    def test_normalizes_date_timezones(self):
        date = datetime(2015, 8, 21, tzinfo=tz.tzlocal())
        normalized = normalize_date(date)
        self.assertEqual(tz.tzutc(), normalized.tzinfo)

    def test_extracts_dates_from_digest_keys(self):
        arn = (
            f'AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1/2015/08/'
            f'16/{TEST_ACCOUNT_ID}_CloudTrail-Digest_us-east-1_foo_us-east-1_'
            '20150816T230550Z.json.gz'
        )
        self.assertEqual('20150816T230550Z', extract_digest_key_date(arn))

    def test_is_backfill_digest_key_identifies_standard_digest(self):
        standard_key = (
            f'AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1/2015/08/'
            f'16/{TEST_ACCOUNT_ID}_CloudTrail-Digest_us-east-1_foo_us-east-1_'
            '20150816T230550Z.json.gz'
        )
        self.assertFalse(is_backfill_digest_key(standard_key))

    def test_is_backfill_digest_key_identifies_backfill_digest(self):
        backfill_key = (
            f'AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1/2015/08/'
            f'16/{TEST_ACCOUNT_ID}_CloudTrail-Digest_us-east-1_foo_us-east-1_'
            '20150816T230550Z_backfill.json.gz'
        )
        self.assertTrue(is_backfill_digest_key(backfill_key))

    def test_is_backfill_digest_key_handles_edge_cases(self):
        # Test with different file extensions
        self.assertFalse(is_backfill_digest_key('file.txt'))
        self.assertFalse(is_backfill_digest_key('file_backfill.txt'))
        self.assertFalse(is_backfill_digest_key('file.json.gz'))

        # Test with backfill in middle of filename
        self.assertFalse(is_backfill_digest_key('file_backfill_other.json.gz'))

    def test_extracts_dates_from_backfill_digest_keys(self):
        backfill_key = (
            f'AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1/2015/08/'
            f'16/{TEST_ACCOUNT_ID}_CloudTrail-Digest_us-east-1_foo_us-east-1_'
            '20150816T230550Z_backfill.json.gz'
        )
        self.assertEqual(
            '20150816T230550Z', extract_digest_key_date(backfill_key)
        )

    def test_extracts_dates_from_standard_digest_keys(self):
        standard_key = (
            f'AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1/2015/08/'
            f'16/{TEST_ACCOUNT_ID}_CloudTrail-Digest_us-east-1_foo_us-east-1_'
            '20150816T230550Z.json.gz'
        )
        self.assertEqual(
            '20150816T230550Z', extract_digest_key_date(standard_key)
        )

    def test_creates_traverser(self):
        mock_s3_provider = mock.Mock()
        traverser = create_digest_traverser(
            trail_arn=TEST_TRAIL_ARN,
            cloudtrail_client=mock.Mock(),
            organization_client=mock.Mock(),
            trail_source_region='us-east-1',
            s3_client_provider=mock_s3_provider,
            bucket='bucket',
            prefix='prefix',
        )
        self.assertEqual('bucket', traverser.starting_bucket)
        self.assertEqual('prefix', traverser.starting_prefix)
        digest_provider = traverser.digest_provider
        self.assertEqual('us-east-1', digest_provider.trail_home_region)
        self.assertEqual('foo', digest_provider.trail_name)

    def test_creates_traverser_account_id(self):
        mock_s3_provider = mock.Mock()
        traverser = create_digest_traverser(
            trail_arn=TEST_TRAIL_ARN,
            cloudtrail_client=mock.Mock(),
            organization_client=mock.Mock(),
            trail_source_region='us-east-1',
            s3_client_provider=mock_s3_provider,
            bucket='bucket',
            prefix='prefix',
            account_id=TEST_ORGANIZATION_ACCOUNT_ID,
        )
        self.assertEqual('bucket', traverser.starting_bucket)
        self.assertEqual('prefix', traverser.starting_prefix)
        digest_provider = traverser.digest_provider
        self.assertEqual('us-east-1', digest_provider.trail_home_region)
        self.assertEqual('foo', digest_provider.trail_name)
        self.assertEqual(
            TEST_ORGANIZATION_ACCOUNT_ID, digest_provider.account_id
        )

    def test_creates_traverser_and_gets_trail_by_arn(self):
        cloudtrail_client = mock.Mock()
        cloudtrail_client.describe_trails.return_value = {
            'trailList': [
                {
                    'TrailARN': TEST_TRAIL_ARN,
                    'S3BucketName': 'bucket',
                    'S3KeyPrefix': 'prefix',
                    'IsOrganizationTrail': False,
                }
            ]
        }
        traverser = create_digest_traverser(
            trail_arn=TEST_TRAIL_ARN,
            trail_source_region='us-east-1',
            cloudtrail_client=cloudtrail_client,
            organization_client=mock.Mock(),
            s3_client_provider=mock.Mock(),
        )
        self.assertEqual('bucket', traverser.starting_bucket)
        self.assertEqual('prefix', traverser.starting_prefix)
        digest_provider = traverser.digest_provider
        self.assertEqual('us-east-1', digest_provider.trail_home_region)
        self.assertEqual('foo', digest_provider.trail_name)
        self.assertEqual(TEST_ACCOUNT_ID, digest_provider.account_id)

    def test_create_traverser_organizational_trail_not_launched(self):
        cloudtrail_client = mock.Mock()
        cloudtrail_client.describe_trails.return_value = {
            'trailList': [
                {
                    'TrailARN': TEST_TRAIL_ARN,
                    'S3BucketName': 'bucket',
                    'S3KeyPrefix': 'prefix',
                }
            ]
        }
        traverser = create_digest_traverser(
            trail_arn=TEST_TRAIL_ARN,
            trail_source_region='us-east-1',
            cloudtrail_client=cloudtrail_client,
            organization_client=mock.Mock(),
            s3_client_provider=mock.Mock(),
        )
        self.assertEqual('bucket', traverser.starting_bucket)
        self.assertEqual('prefix', traverser.starting_prefix)
        digest_provider = traverser.digest_provider
        self.assertEqual('us-east-1', digest_provider.trail_home_region)
        self.assertEqual('foo', digest_provider.trail_name)
        self.assertEqual(TEST_ACCOUNT_ID, digest_provider.account_id)

    def test_creates_traverser_and_gets_trail_by_arn_s3_bucket_specified(self):
        cloudtrail_client = mock.Mock()
        traverser = create_digest_traverser(
            trail_arn=TEST_TRAIL_ARN,
            trail_source_region='us-east-1',
            cloudtrail_client=cloudtrail_client,
            organization_client=mock.Mock(),
            s3_client_provider=mock.Mock(),
            bucket="bucket",
        )
        self.assertEqual('bucket', traverser.starting_bucket)
        digest_provider = traverser.digest_provider
        self.assertEqual('us-east-1', digest_provider.trail_home_region)
        self.assertEqual('foo', digest_provider.trail_name)
        self.assertEqual(TEST_ACCOUNT_ID, digest_provider.account_id)

    def test_creates_traverser_and_gets_organization_id(self):
        cloudtrail_client = mock.Mock()
        cloudtrail_client.describe_trails.return_value = {
            'trailList': [
                {
                    'TrailARN': TEST_TRAIL_ARN,
                    'S3BucketName': 'bucket',
                    'S3KeyPrefix': 'prefix',
                    'IsOrganizationTrail': True,
                }
            ]
        }
        organization_client = mock.Mock()
        organization_client.describe_organization.return_value = {
            "Organization": {
                "MasterAccountId": TEST_ACCOUNT_ID,
                "Id": TEST_ORGANIZATION_ID,
            }
        }
        traverser = create_digest_traverser(
            trail_arn=TEST_TRAIL_ARN,
            trail_source_region='us-east-1',
            cloudtrail_client=cloudtrail_client,
            organization_client=organization_client,
            s3_client_provider=mock.Mock(),
            account_id=TEST_ACCOUNT_ID,
        )
        self.assertEqual('bucket', traverser.starting_bucket)
        self.assertEqual('prefix', traverser.starting_prefix)
        digest_provider = traverser.digest_provider
        self.assertEqual('us-east-1', digest_provider.trail_home_region)
        self.assertEqual('foo', digest_provider.trail_name)
        self.assertEqual(TEST_ORGANIZATION_ID, digest_provider.organization_id)

    def test_creates_traverser_organization_trail_missing_account_id(self):
        cloudtrail_client = mock.Mock()
        cloudtrail_client.describe_trails.return_value = {
            'trailList': [
                {
                    'TrailARN': TEST_TRAIL_ARN,
                    'S3BucketName': 'bucket',
                    'S3KeyPrefix': 'prefix',
                    'IsOrganizationTrail': True,
                }
            ]
        }
        organization_client = mock.Mock()
        organization_client.describe_organization.return_value = {
            "Organization": {
                "MasterAccountId": TEST_ACCOUNT_ID,
                "Id": TEST_ORGANIZATION_ID,
            }
        }
        with self.assertRaises(ParameterRequiredError):
            create_digest_traverser(
                trail_arn=TEST_TRAIL_ARN,
                trail_source_region='us-east-1',
                cloudtrail_client=cloudtrail_client,
                organization_client=organization_client,
                s3_client_provider=mock.Mock(),
            )


class TestPublicKeyProvider(unittest.TestCase):
    def test_returns_public_key_in_range(self):
        cloudtrail_client = mock.Mock()
        cloudtrail_client.list_public_keys.return_value = {
            'PublicKeyList': [
                {'Fingerprint': 'a', 'OtherData': 'a', 'Value': 'a'},
                {'Fingerprint': 'b', 'OtherData': 'b', 'Value': 'b'},
                {'Fingerprint': 'c', 'OtherData': 'c', 'Value': 'c'},
            ]
        }
        provider = PublicKeyProvider(cloudtrail_client)
        start_date = START_DATE
        end_date = start_date + timedelta(days=2)
        keys = provider.get_public_keys(start_date, end_date)
        self.assertEqual(
            {
                'a': {'Fingerprint': 'a', 'OtherData': 'a', 'Value': 'a'},
                'b': {'Fingerprint': 'b', 'OtherData': 'b', 'Value': 'b'},
                'c': {'Fingerprint': 'c', 'OtherData': 'c', 'Value': 'c'},
            },
            keys,
        )
        cloudtrail_client.list_public_keys.assert_has_calls(
            [mock.call(EndTime=end_date, StartTime=start_date)]
        )


class TestSha256RSADigestValidator(unittest.TestCase):
    def setUp(self):
        self._digest_data = {
            'digestStartTime': 'baz',
            'digestEndTime': 'foo',
            'awsAccountId': 'account',
            'digestPublicKeyFingerprint': 'abc',
            'digestS3Bucket': 'bucket',
            'digestS3Object': 'object',
            'previousDigestSignature': 'xyz',
        }
        self._inflated_digest = json.dumps(self._digest_data).encode()
        self._digest_data['_signature'] = 'aeff'

    def test_validates_digests(self):
        (public_key, private_key) = rsa.newkeys(512)
        sha256_hash = hashlib.sha256(self._inflated_digest)
        string_to_sign = f"{self._digest_data['digestEndTime']}\n{self._digest_data['digestS3Bucket']}/{self._digest_data['digestS3Object']}\n{sha256_hash.hexdigest()}\n{self._digest_data['previousDigestSignature']}"
        signature = rsa.sign(string_to_sign.encode(), private_key, 'SHA-256')
        self._digest_data['_signature'] = binascii.hexlify(signature)
        validator = Sha256RSADigestValidator()
        public_key_b64 = base64.b64encode(public_key.save_pkcs1(format='DER'))
        validator.validate(
            'b', 'k', public_key_b64, self._digest_data, self._inflated_digest
        )

    def test_does_not_expose_underlying_key_decoding_error(self):
        validator = Sha256RSADigestValidator()
        try:
            validator.validate('b', 'k', 'YQo=', self._digest_data, b'invalid')
            self.fail('Should have failed')
        except DigestError as e:
            self.assertEqual(
                (
                    'Digest file\ts3://b/k\tINVALID: Unable to load '
                    'PKCS #1 key with fingerprint abc'
                ),
                str(e),
            )

    def test_does_not_expose_underlying_validation_error(self):
        validator = Sha256RSADigestValidator()
        try:
            validator.validate(
                'b', 'k', VALID_TEST_KEY, self._digest_data, b'invalid'
            )
            self.fail('Should have failed')
        except DigestSignatureError as e:
            self.assertEqual(
                (
                    'Digest file\ts3://b/k\tINVALID: signature '
                    'verification failed'
                ),
                str(e),
            )

    def test_properly_signs_when_no_previous_signature(self):
        validator = Sha256RSADigestValidator()
        digest_data = {
            'digestEndTime': 'a',
            'digestS3Bucket': 'b',
            'digestS3Object': 'c',
            'previousDigestSignature': None,
        }
        signed = validator._create_string_to_sign(digest_data, b'abc')
        self.assertEqual(
            (
                b'a\nb/c\nba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff6'
                b'1f20015ad\nnull'
            ),
            signed,
        )


class TestDigestProvider(BaseAWSCommandParamsTest):
    def _fake_key(self, date):
        parsed = parser.parse(date)
        return (
            f'prefix/AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1/{parsed.year}/'
            f'{parsed.month}/{parsed.day}/{TEST_ACCOUNT_ID}_CloudTrail-Digest_us-east-1_foo_'
            f'us-east-1_{date}.json.gz'
        )

    def _get_mock_provider(self, s3_client):
        mock_s3_client_provider = mock.Mock()
        mock_s3_client_provider.get_client.return_value = s3_client
        return DigestProvider(
            mock_s3_client_provider, TEST_ACCOUNT_ID, 'foo', 'us-east-1'
        )

    def test_initializes_public_properties(self):
        client = mock.Mock()
        provider = DigestProvider(client, TEST_ACCOUNT_ID, 'foo', 'us-east-1')
        self.assertEqual(TEST_ACCOUNT_ID, provider.account_id)
        self.assertEqual('foo', provider.trail_name)
        self.assertEqual('us-east-1', provider.trail_home_region)

    def test_returns_digests_in_range(self):
        s3_client = self.driver.session.create_client('s3')
        keys = [
            self._fake_key(format_date(START_DATE - timedelta(days=1))),
            self._fake_key(format_date(START_DATE + timedelta(days=1))),
            self._fake_key(format_date(START_DATE + timedelta(days=2))),
            self._fake_key(format_date(START_DATE + timedelta(days=3))),
            self._fake_key(format_date(END_DATE + timedelta(hours=1))),
            self._fake_key(format_date(END_DATE + timedelta(days=1))),
        ]
        # Create a key that looks similar but for a different trail.
        bad_name = keys[3].replace('foo', 'baz')
        # Create a key that looks similar but is from a different trail source
        # region (e.g., CloudTrail-Digest/us-west-2).
        bad_region = keys[3].replace(
            'CloudTrail-Digest/us-east-1', 'CloudTrail-Digest/us-west-2'
        )
        bad_region = bad_region.replace(
            'CloudTrail-Digest_us-east-1', 'CloudTrail-Digest_us-west-2'
        )
        self.parsed_responses = [
            {
                "Contents": [
                    {"Key": keys[0]},  # skip (date <)
                    {"Key": keys[1]},
                    {"Key": keys[2]},
                    {"Key": 'foo/baz/bar'},  # skip (regex (bogus))
                    {"Key": bad_name},  # skip (regex (trail name))
                    {"Key": bad_region},  # skip (regex (source))
                    {"Key": keys[3]},
                    {"Key": keys[4]},  # hour is +1, but keep
                    {"Key": keys[5]},  # skip (date >)
                ]
            }
        ]
        self.patch_make_request()
        provider = self._get_mock_provider(s3_client)
        digests = provider.load_digest_keys_in_range(
            'foo', 'prefix', START_DATE, END_DATE
        )
        self.assertNotIn(bad_name, digests)
        self.assertNotIn(bad_region, digests)
        self.assertEqual(keys[1], digests[0])
        self.assertEqual(keys[2], digests[1])
        self.assertEqual(keys[3], digests[2])
        self.assertEqual(keys[4], digests[3])

    def test_calls_list_objects_correctly(self):
        s3_client = mock.Mock()
        mock_paginate = s3_client.get_paginator.return_value.paginate
        mock_search = mock_paginate.return_value.search
        mock_search.return_value = []
        provider = self._get_mock_provider(s3_client)
        provider.load_digest_keys_in_range('1', 'prefix', START_DATE, END_DATE)
        marker = (
            'prefix/AWSLogs/{account}/CloudTrail-Digest/us-east-1/'
            '2014/08/09/{account}_CloudTrail-Digest_us-east-1_foo_'
            'us-east-1_20140809T235900Z.json.gz'
        )
        prefix = 'prefix/AWSLogs/{account}/CloudTrail-Digest/us-east-1'
        mock_paginate.assert_called_once_with(
            Bucket='1',
            Marker=marker.format(account=TEST_ACCOUNT_ID),
            Prefix=prefix.format(account=TEST_ACCOUNT_ID),
        )

    def test_calls_list_objects_correctly_org_trails(self):
        s3_client = mock.Mock()
        mock_s3_client_provider = mock.Mock()
        mock_paginate = s3_client.get_paginator.return_value.paginate
        mock_search = mock_paginate.return_value.search
        mock_search.return_value = []
        mock_s3_client_provider.get_client.return_value = s3_client
        provider = DigestProvider(
            mock_s3_client_provider,
            TEST_ORGANIZATION_ACCOUNT_ID,
            'foo',
            'us-east-1',
            'us-east-1',
            TEST_ORGANIZATION_ID,
        )
        provider.load_digest_keys_in_range('1', 'prefix', START_DATE, END_DATE)
        marker = (
            'prefix/AWSLogs/{organization_id}/{member_account}/'
            'CloudTrail-Digest/us-east-1/'
            '2014/08/09/{member_account}_CloudTrail-Digest_us-east-1_foo_'
            'us-east-1_20140809T235900Z.json.gz'
        )
        prefix = (
            'prefix/AWSLogs/{organization_id}/{member_account}/'
            'CloudTrail-Digest/us-east-1'
        )
        mock_paginate.assert_called_once_with(
            Bucket='1',
            Marker=marker.format(
                member_account=TEST_ORGANIZATION_ACCOUNT_ID,
                organization_id=TEST_ORGANIZATION_ID,
            ),
            Prefix=prefix.format(
                member_account=TEST_ORGANIZATION_ACCOUNT_ID,
                organization_id=TEST_ORGANIZATION_ID,
            ),
        )

    def test_create_digest_prefix_without_key_prefix(self):
        mock_s3_client_provider = mock.Mock()
        provider = DigestProvider(
            mock_s3_client_provider, TEST_ACCOUNT_ID, 'foo', 'us-east-1'
        )
        prefix = provider._create_digest_prefix(START_DATE, None)
        expected = f'AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1'
        self.assertEqual(expected, prefix)

    def test_create_digest_prefix_with_key_prefix(self):
        mock_s3_client_provider = mock.Mock()
        provider = DigestProvider(
            mock_s3_client_provider, TEST_ACCOUNT_ID, 'foo', 'us-east-1'
        )
        prefix = provider._create_digest_prefix(START_DATE, 'my-prefix')
        expected = (
            f'my-prefix/AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1'
        )
        self.assertEqual(expected, prefix)

    def test_create_digest_prefix_org_trail(self):
        mock_s3_client_provider = mock.Mock()
        provider = DigestProvider(
            mock_s3_client_provider,
            TEST_ORGANIZATION_ACCOUNT_ID,
            'foo',
            'us-east-1',
            'us-east-1',
            TEST_ORGANIZATION_ID,
        )
        prefix = provider._create_digest_prefix(START_DATE, None)
        expected = f'AWSLogs/{TEST_ORGANIZATION_ID}/{TEST_ORGANIZATION_ACCOUNT_ID}/CloudTrail-Digest/us-east-1'
        self.assertEqual(expected, prefix)

    def test_create_digest_prefix_org_trail_with_key_prefix(self):
        mock_s3_client_provider = mock.Mock()
        provider = DigestProvider(
            mock_s3_client_provider,
            TEST_ORGANIZATION_ACCOUNT_ID,
            'foo',
            'us-east-1',
            'us-east-1',
            TEST_ORGANIZATION_ID,
        )
        prefix = provider._create_digest_prefix(START_DATE, 'custom-prefix')
        expected = f'custom-prefix/AWSLogs/{TEST_ORGANIZATION_ID}/{TEST_ORGANIZATION_ACCOUNT_ID}/CloudTrail-Digest/us-east-1'
        self.assertEqual(expected, prefix)

    def test_ensures_digest_has_proper_metadata(self):
        out = BytesIO()
        f = gzip.GzipFile(fileobj=out, mode="wb")
        f.write(b'{"foo":"bar"}')
        f.close()
        gzipped_data = out.getvalue()
        s3_client = mock.Mock()
        s3_client.get_object.return_value = {
            'Body': BytesIO(gzipped_data),
            'Metadata': {},
        }
        provider = self._get_mock_provider(s3_client)
        with self.assertRaises(DigestSignatureError):
            provider.fetch_digest('bucket', 'key')

    def test_ensures_digest_can_be_gzip_inflated(self):
        s3_client = mock.Mock()
        s3_client.get_object.return_value = {
            'Body': BytesIO(b'foo'),
            'Metadata': {},
        }
        provider = self._get_mock_provider(s3_client)
        with self.assertRaises(InvalidDigestFormat):
            provider.fetch_digest('bucket', 'key')

    def test_ensures_digests_can_be_json_parsed(self):
        json_str = '{{{'
        out = BytesIO()
        f = gzip.GzipFile(fileobj=out, mode="wb")
        f.write(json_str.encode())
        f.close()
        gzipped_data = out.getvalue()
        s3_client = mock.Mock()
        s3_client.get_object.return_value = {
            'Body': BytesIO(gzipped_data),
            'Metadata': {'signature': 'abc', 'signature-algorithm': 'SHA256'},
        }
        provider = self._get_mock_provider(s3_client)
        with self.assertRaises(InvalidDigestFormat):
            provider.fetch_digest('bucket', 'key')

    def test_fetches_digests(self):
        json_str = '{"foo":"bar"}'
        out = BytesIO()
        f = gzip.GzipFile(fileobj=out, mode="wb")
        f.write(json_str.encode())
        f.close()
        gzipped_data = out.getvalue()
        s3_client = mock.Mock()
        s3_client.get_object.return_value = {
            'Body': BytesIO(gzipped_data),
            'Metadata': {'signature': 'abc', 'signature-algorithm': 'SHA256'},
        }
        provider = self._get_mock_provider(s3_client)
        result = provider.fetch_digest('bucket', 'key')
        self.assertEqual(
            {
                'foo': 'bar',
                '_signature': 'abc',
                '_signature_algorithm': 'SHA256',
            },
            result[0],
        )
        self.assertEqual(json_str.encode(), result[1])

    def _fake_backfill_key(self, date):
        parsed = parser.parse(date)
        return (
            f'prefix/AWSLogs/{TEST_ACCOUNT_ID}/CloudTrail-Digest/us-east-1/{parsed.year}/'
            f'{parsed.month}/{parsed.day}/{TEST_ACCOUNT_ID}_CloudTrail-Digest_us-east-1_foo_'
            f'us-east-1_{date}_backfill.json.gz'
        )

    def test_load_all_digest_keys_in_range_separates_standard_and_backfill(
        self,
    ):
        s3_client = self.driver.session.create_client('s3')
        standard_keys = [
            self._fake_key(format_date(START_DATE + timedelta(days=1))),
            self._fake_key(format_date(START_DATE + timedelta(days=2))),
        ]
        backfill_keys = [
            self._fake_backfill_key(
                format_date(START_DATE + timedelta(days=1))
            ),
            self._fake_backfill_key(
                format_date(START_DATE + timedelta(days=2))
            ),
        ]

        self.parsed_responses = [
            {
                "Contents": [
                    {"Key": standard_keys[0]},
                    {"Key": backfill_keys[0]},
                    {"Key": standard_keys[1]},
                    {"Key": backfill_keys[1]},
                ]
            }
        ]
        self.patch_make_request()
        provider = self._get_mock_provider(s3_client)

        standard_digests, backfill_digests = (
            provider.load_all_digest_keys_in_range(
                'foo', 'prefix', START_DATE, END_DATE
            )
        )

        self.assertEqual(standard_keys, standard_digests)
        self.assertEqual(backfill_keys, backfill_digests)

    def test_load_digest_keys_in_range_uses_cache(self):
        s3_client = mock.Mock()
        mock_paginate = s3_client.get_paginator.return_value.paginate
        mock_search = mock_paginate.return_value.search
        mock_search.return_value = []
        provider = self._get_mock_provider(s3_client)

        provider.load_digest_keys_in_range(
            'bucket', 'prefix', START_DATE, END_DATE, is_backfill=False
        )
        self.assertEqual(1, mock_paginate.call_count)

        provider.load_digest_keys_in_range(
            'bucket', 'prefix', START_DATE, END_DATE, is_backfill=True
        )
        self.assertEqual(1, mock_paginate.call_count)

        provider.load_digest_keys_in_range(
            'bucket', 'prefix', START_DATE, START_DATE, is_backfill=False
        )
        self.assertEqual(2, mock_paginate.call_count)

    def test_fetches_backfill_digests_with_metadata(self):
        json_str = '{"foo":"bar"}'
        out = BytesIO()
        f = gzip.GzipFile(fileobj=out, mode="wb")
        f.write(json_str.encode())
        f.close()
        gzipped_data = out.getvalue()
        s3_client = mock.Mock()
        s3_client.get_object.return_value = {
            'Body': BytesIO(gzipped_data),
            'Metadata': {
                'signature': 'abc',
                'signature-algorithm': 'SHA256',
                'backfill-generation-timestamp': '2025-09-01T00:00:00Z',
            },
        }
        provider = self._get_mock_provider(s3_client)
        backfill_key = self._fake_backfill_key(format_date(START_DATE))

        result = provider.fetch_digest('bucket', backfill_key)

        self.assertEqual(
            {
                'foo': 'bar',
                '_signature': 'abc',
                '_signature_algorithm': 'SHA256',
                '_backfill_generation_timestamp': '2025-09-01T00:00:00Z',
            },
            result[0],
        )
        self.assertEqual(json_str.encode(), result[1])

    def test_ensures_backfill_digest_has_proper_metadata(self):
        json_str = '{"foo":"bar"}'
        out = BytesIO()
        f = gzip.GzipFile(fileobj=out, mode="wb")
        f.write(json_str.encode())
        f.close()
        gzipped_data = out.getvalue()
        s3_client = mock.Mock()
        s3_client.get_object.return_value = {
            'Body': BytesIO(gzipped_data),
            'Metadata': {
                'signature': 'abc',
                'signature-algorithm': 'SHA256',
                # Missing backfill-generation-timestamp
            },
        }
        provider = self._get_mock_provider(s3_client)
        backfill_key = self._fake_backfill_key(format_date(START_DATE))

        with self.assertRaises(InvalidDigestFormat):
            provider.fetch_digest('bucket', backfill_key)


class TestDigestTraverser(unittest.TestCase):
    def test_initializes_with_default_validator(self):
        provider = mock.Mock()
        traverser = DigestTraverser(
            digest_provider=provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=mock.Mock(),
        )
        self.assertEqual('1', traverser.starting_bucket)
        self.assertEqual('baz', traverser.starting_prefix)
        self.assertEqual(provider, traverser.digest_provider)

    def test_ensures_public_keys_are_loaded(self):
        start_date = START_DATE
        end_date = END_DATE
        digest_provider = mock.Mock()
        key_provider = mock.Mock()
        key_provider.get_public_keys.return_value = []
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
        )
        digest_iter = traverser.traverse_digests(start_date, end_date)
        with self.assertRaises(RuntimeError):
            next(digest_iter)
        key_provider.get_public_keys.assert_called_with(
            start_date, end_date + timedelta(hours=2)
        )

    def test_ensures_public_key_is_found(self):
        start_date = START_DATE
        end_date = END_DATE
        key_name = end_date.strftime(DATE_FORMAT) + '.json.gz'
        region = 'us-west-2'
        digest_provider = mock.Mock()
        digest_provider.trail_home_region = region
        digest_provider.load_digest_keys_in_range.return_value = [key_name]
        digest_provider.fetch_digest.return_value = (
            {
                'digestEndTime': 'foo',
                'digestStartTime': 'foo',
                'awsAccountId': 'account',
                'digestPublicKeyFingerprint': 'abc',
                'digestS3Bucket': '1',
                'digestS3Object': key_name,
                'previousDigestSignature': 'xyz',
            },
            'abc',
        )
        key_provider = mock.Mock()
        key_provider.get_public_keys.return_value = [{'Fingerprint': 'a'}]
        on_invalid, calls = collecting_callback()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            on_invalid=on_invalid,
        )
        digest_iter = traverser.traverse_digests(start_date, end_date)
        with self.assertRaises(StopIteration):
            next(digest_iter)
        self.assertEqual(1, len(calls))
        self.assertEqual(
            f'Digest file\ts3://1/{key_name}\tINVALID: public key not '
            f'found in region {region} for fingerprint abc',
            calls[0]['message'],
        )

    def test_invokes_digest_validator(self):
        start_date = START_DATE
        end_date = END_DATE
        key_name = end_date.strftime(DATE_FORMAT) + '.json.gz'
        digest = {
            'digestPublicKeyFingerprint': 'a',
            'digestS3Bucket': '1',
            'digestS3Object': key_name,
            'previousDigestSignature': '...',
            'digestStartTime': (end_date - timedelta(hours=1)).strftime(
                DATE_FORMAT
            ),
            'digestEndTime': end_date.strftime(DATE_FORMAT),
        }
        digest_provider = mock.Mock()
        digest_provider.load_digest_keys_in_range.return_value = [key_name]
        digest_provider.fetch_digest.return_value = (digest, key_name)
        key_provider = mock.Mock()
        public_keys = {'a': {'Fingerprint': 'a', 'Value': 'a'}}
        key_provider.get_public_keys.return_value = public_keys
        digest_validator = mock.Mock()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=digest_validator,
        )
        digest_iter = traverser.traverse_digests(start_date, end_date)
        self.assertEqual(digest, next(digest_iter))
        digest_validator.validate.assert_called_with(
            '1', key_name, public_keys['a']['Value'], digest, key_name
        )

    def test_ensures_digest_from_same_location_as_json_contents(self):
        start_date = START_DATE
        end_date = END_DATE
        callback, collected = collecting_callback()
        key_name = end_date.strftime(DATE_FORMAT) + '.json.gz'
        digest = {
            'digestPublicKeyFingerprint': 'a',
            'digestS3Bucket': 'not_same',
            'digestS3Object': key_name,
            'digestEndTime': end_date.strftime(DATE_FORMAT),
        }
        digest_provider = mock.Mock()
        digest_provider.load_digest_keys_in_range.return_value = [key_name]
        digest_provider.fetch_digest.return_value = (digest, key_name)
        key_provider = mock.Mock()
        digest_validator = mock.Mock()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=digest_validator,
            on_invalid=callback,
        )
        digest_iter = traverser.traverse_digests(start_date, end_date)
        self.assertIsNone(next(digest_iter, None))
        self.assertEqual(1, len(collected))
        self.assertEqual(
            f'Digest file\ts3://1/{key_name}\tINVALID: invalid format',
            collected[0]['message'],
        )

    def test_loads_digests_in_range(self):
        start_date = START_DATE
        end_date = START_DATE + timedelta(hours=5)
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'link', 'link']
        )
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
        )
        collected = list(traverser.traverse_digests(start_date, end_date))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(
            1, len(digest_provider.calls['load_digest_keys_in_range'])
        )
        self.assertEqual(4, len(digest_provider.calls['fetch_digest']))
        self.assertEqual(4, len(collected))

    def test_invokes_cb_and_continues_when_missing(self):
        start_date = START_DATE
        end_date = END_DATE
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'missing', 'link']
        )
        on_missing, missing_calls = collecting_callback()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
            on_missing=on_missing,
        )
        collected = list(traverser.traverse_digests(start_date, end_date))
        self.assertEqual(3, len(collected))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(1, len(missing_calls))
        # Ensure the keys were provided in the correct order.
        self.assertIn('bucket', missing_calls[0])
        self.assertIn('next_end_date', missing_calls[0])
        # Ensure the keys were provided in the correct order.
        self.assertEqual(
            digest_provider.digests[1], missing_calls[0]['next_key']
        )
        self.assertEqual(
            digest_provider.digests[2], missing_calls[0]['last_key']
        )
        # Ensure the provider was called correctly
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(
            1, len(digest_provider.calls['load_digest_keys_in_range'])
        )
        self.assertEqual(4, len(digest_provider.calls['fetch_digest']))

    def test_invokes_cb_and_continues_when_invalid(self):
        start_date = START_DATE
        end_date = END_DATE
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'invalid', 'link', 'invalid']
        )
        on_invalid, invalid_calls = collecting_callback()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
            on_invalid=on_invalid,
        )
        collected = list(traverser.traverse_digests(start_date, end_date))
        self.assertEqual(3, len(collected))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(2, len(invalid_calls))
        # Ensure it was invoked with all the kwargs we expected.
        self.assertIn('bucket', invalid_calls[0])
        self.assertIn('next_end_date', invalid_calls[0])
        # Ensure the keys were provided in the correct order.
        self.assertEqual(
            digest_provider.digests[4], invalid_calls[0]['last_key']
        )
        self.assertEqual(
            digest_provider.digests[3], invalid_calls[0]['next_key']
        )
        self.assertEqual(
            digest_provider.digests[2], invalid_calls[1]['last_key']
        )
        self.assertEqual(
            digest_provider.digests[1], invalid_calls[1]['next_key']
        )
        # Ensure the provider was called correctly
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(
            1, len(digest_provider.calls['load_digest_keys_in_range'])
        )
        self.assertEqual(5, len(digest_provider.calls['fetch_digest']))

    def test_invokes_cb_and_continues_when_gap(self):
        start_date = START_DATE
        end_date = END_DATE
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'gap', 'gap']
        )
        on_gap, gap_calls = collecting_callback()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
            on_gap=on_gap,
        )
        collected = list(traverser.traverse_digests(start_date, end_date))
        self.assertEqual(4, len(collected))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(2, len(gap_calls))
        # Ensure it was invoked with all the kwargs we expected.
        self.assertIn('bucket', gap_calls[0])
        self.assertIn('next_key', gap_calls[0])
        self.assertIn('next_end_date', gap_calls[0])
        self.assertIn('last_key', gap_calls[0])
        self.assertIn('last_start_date', gap_calls[0])
        # Ensure the keys were provided in the correct order.
        self.assertEqual(digest_provider.digests[3], gap_calls[0]['last_key'])
        self.assertEqual(digest_provider.digests[2], gap_calls[0]['next_key'])
        self.assertEqual(digest_provider.digests[2], gap_calls[1]['last_key'])
        self.assertEqual(digest_provider.digests[1], gap_calls[1]['next_key'])
        # Ensure the provider was called correctly
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(
            1, len(digest_provider.calls['load_digest_keys_in_range'])
        )
        self.assertEqual(4, len(digest_provider.calls['fetch_digest']))

    def test_reloads_objects_on_bucket_change(self):
        start_date = START_DATE
        end_date = END_DATE
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'bucket_change', 'link']
        )
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
        )
        collected = list(traverser.traverse_digests(start_date, end_date))
        self.assertEqual(4, len(collected))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        # Ensure the provider was called correctly
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(
            2, len(digest_provider.calls['load_digest_keys_in_range'])
        )
        self.assertEqual(
            ['1', '1', '2', '2'], [c['digestS3Bucket'] for c in collected]
        )

    def test_does_not_hard_fail_on_invalid_signature(self):
        start_date = START_DATE
        end_date = END_DATE
        end_timestamp = end_date.strftime(DATE_FORMAT) + '.json.gz'
        digest = {
            'digestPublicKeyFingerprint': 'a',
            'digestS3Bucket': '1',
            'digestS3Object': end_timestamp,
            'previousDigestSignature': '...',
            'digestStartTime': (end_date - timedelta(hours=1)).strftime(
                DATE_FORMAT
            ),
            'digestEndTime': end_timestamp,
            '_signature': '123',
        }
        digest_provider = mock.Mock()
        digest_provider.load_digest_keys_in_range.return_value = [
            end_timestamp
        ]
        digest_provider.fetch_digest.return_value = (digest, end_timestamp)
        key_provider = mock.Mock()
        public_keys = {'a': {'Fingerprint': 'a', 'Value': 'a'}}
        key_provider.get_public_keys.return_value = public_keys
        digest_validator = Sha256RSADigestValidator()
        on_invalid, calls = collecting_callback()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=digest_validator,
            on_invalid=on_invalid,
        )
        digest_iter = traverser.traverse_digests(start_date, end_date)
        next(digest_iter, None)
        self.assertIn(
            f'Digest file\ts3://1/{end_timestamp}\tINVALID: ',
            calls[0]['message'],
        )

    def test_traverse_backfill_digests_basic(self):
        start_date = START_DATE
        end_date = START_DATE + timedelta(hours=4)
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'link', 'link']
        )

        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
        )

        collected = list(
            traverser.traverse_digests(start_date, end_date, True)
        )

        self.assertEqual(4, len(collected))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(
            1, len(digest_provider.calls['load_digest_keys_in_range'])
        )
        self.assertEqual(4, len(digest_provider.calls['fetch_digest']))

    def test_traverse_backfill_digests_with_missing(self):
        start_date = START_DATE
        end_date = START_DATE + timedelta(hours=4)
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'missing', 'link']
        )

        on_missing, missing_calls = collecting_callback()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
            on_missing=on_missing,
        )

        collected = list(
            traverser.traverse_digests(start_date, end_date, True)
        )

        self.assertEqual(3, len(collected))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(1, len(missing_calls))
        self.assertIn('bucket', missing_calls[0])
        self.assertIn('next_end_date', missing_calls[0])

    def test_traverse_backfill_digests_with_invalid(self):
        start_date = START_DATE
        end_date = START_DATE + timedelta(hours=5)
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'invalid', 'link', 'invalid']
        )

        on_invalid, invalid_calls = collecting_callback()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
            on_invalid=on_invalid,
        )

        collected = list(
            traverser.traverse_digests(start_date, end_date, True)
        )

        self.assertEqual(3, len(collected))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(2, len(invalid_calls))

    def test_traverse_backfill_digests_with_gaps(self):
        start_date = START_DATE
        end_date = START_DATE + timedelta(hours=4)
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'gap', 'gap']
        )

        on_gap, gap_calls = collecting_callback()
        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
            on_gap=on_gap,
        )

        collected = list(
            traverser.traverse_digests(start_date, end_date, True)
        )

        self.assertEqual(4, len(collected))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(2, len(gap_calls))
        for gap_call in gap_calls:
            self.assertIn('bucket', gap_call)
            self.assertIn('next_key', gap_call)

    def test_traverse_backfill_digests_bucket_change(self):
        start_date = START_DATE
        end_date = START_DATE + timedelta(hours=4)
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'bucket_change', 'link']
        )

        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
        )

        collected = list(
            traverser.traverse_digests(start_date, end_date, True)
        )

        self.assertEqual(4, len(collected))
        self.assertEqual(1, key_provider.get_public_keys.call_count)
        self.assertEqual(
            2, len(digest_provider.calls['load_digest_keys_in_range'])
        )
        self.assertEqual(
            ['1', '1', '2', '2'], [c['digestS3Bucket'] for c in collected]
        )

    def test_traverse_mixed_standard_and_backfill_digests(self):
        start_date = START_DATE
        end_date = START_DATE + timedelta(hours=3)
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'link']
        )

        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
        )

        standard_digests = list(
            traverser.traverse_digests(start_date, end_date)
        )
        backfill_digests = list(
            traverser.traverse_digests(start_date, end_date, True)
        )

        self.assertEqual(3, len(standard_digests))
        self.assertEqual(3, len(backfill_digests))
        self.assertEqual(2, key_provider.get_public_keys.call_count)
        self.assertEqual(
            2, len(digest_provider.calls['load_digest_keys_in_range'])
        )
        self.assertEqual(6, len(digest_provider.calls['fetch_digest']))

    def test_traverse_backfill_digests_cache_miss_triggers_multiple_api_calls(
        self,
    ):
        start_date = START_DATE
        end_date = START_DATE + timedelta(hours=3)
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'link']
        )

        call_count = 0

        def mock_get_public_keys(start_date, end_date):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {'2': {'Fingerprint': '2', 'Value': 'ffaa02'}}
            elif call_count == 2:
                return {'1': {'Fingerprint': '1', 'Value': 'ffaa01'}}
            else:
                return {'0': {'Fingerprint': '0', 'Value': 'ffaa00'}}

        key_provider.get_public_keys.side_effect = mock_get_public_keys

        traverser = DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket='1',
            starting_prefix='baz',
            public_key_provider=key_provider,
            digest_validator=validator,
        )

        collected = list(
            traverser.traverse_digests(start_date, end_date, True)
        )

        self.assertEqual(3, len(collected))
        self.assertEqual(3, key_provider.get_public_keys.call_count)
        self.assertEqual(
            1, len(digest_provider.calls['load_digest_keys_in_range'])
        )
        self.assertEqual(3, len(digest_provider.calls['fetch_digest']))


class TestCloudTrailCommand(BaseAWSCommandParamsTest):
    def test_s3_client_created_lazily(self):
        session = mock.Mock()
        command = CloudTrailValidateLogs(session)
        parsed_globals = mock.Mock(
            region=None, verify_ssl=None, endpoint_url=None
        )
        command.setup_services(parsed_globals)
        create_client_calls = session.create_client.call_args_list
        self.assertEqual(
            create_client_calls,
            [
                mock.call('organizations', verify=None, region_name=None),
                mock.call('cloudtrail', verify=None, region_name=None),
            ],
        )

    def test_endpoint_url_is_used_for_cloudtrail(self):
        endpoint_url = 'https://mycloudtrail.aws.amazon.com/'
        session = mock.Mock()
        command = CloudTrailValidateLogs(session)
        parsed_globals = mock.Mock(
            region='foo', verify_ssl=None, endpoint_url=endpoint_url
        )
        command.setup_services(parsed_globals)
        create_client_calls = session.create_client.call_args_list
        self.assertEqual(
            create_client_calls,
            [
                mock.call('organizations', verify=None, region_name='foo'),
                # Here we should inject the endpoint_url only for cloudtrail.
                mock.call(
                    'cloudtrail',
                    verify=None,
                    region_name='foo',
                    endpoint_url=endpoint_url,
                ),
            ],
        )

    def test_initializes_args(self):
        session = mock.Mock()
        command = CloudTrailValidateLogs(session)
        start_date = START_DATE.strftime(DATE_FORMAT)
        args = Namespace(
            trail_arn='abc',
            verbose=True,
            start_time=start_date,
            s3_bucket='bucket',
            s3_prefix='prefix',
            end_time=None,
            account_id=None,
        )
        command.handle_args(args)
        self.assertEqual('abc', command.trail_arn)
        self.assertEqual(True, command.is_verbose)
        self.assertEqual('bucket', command.s3_bucket)
        self.assertEqual('prefix', command.s3_prefix)
        self.assertEqual(start_date, command.start_time.strftime(DATE_FORMAT))
        self.assertIsNotNone(command.end_time)
        self.assertGreater(command.end_time, command.start_time)


class TestS3ClientProvider(BaseAWSCommandParamsTest):
    def test_creates_clients_for_buckets_in_us_east_1(self):
        session = mock.Mock()
        s3_client = mock.Mock()
        session.create_client.return_value = s3_client
        s3_client.get_bucket_location.return_value = {'LocationConstraint': ''}
        provider = S3ClientProvider(session)
        created_client = provider.get_client('foo')
        self.assertEqual(s3_client, created_client)
        create_client_calls = session.create_client.call_args_list
        self.assertEqual(
            create_client_calls, [mock.call('s3', region_name='us-east-1')]
        )
        self.assertEqual(1, s3_client.get_bucket_location.call_count)

    def test_creates_clients_for_buckets_outside_us_east_1(self):
        session = mock.Mock()
        s3_client = mock.Mock()
        session.create_client.return_value = s3_client
        s3_client.get_bucket_location.return_value = {
            'LocationConstraint': 'us-west-2'
        }
        provider = S3ClientProvider(session, 'us-west-1')
        created_client = provider.get_client('foo')
        self.assertEqual(s3_client, created_client)
        create_client_calls = session.create_client.call_args_list
        self.assertEqual(
            create_client_calls,
            [
                mock.call('s3', region_name='us-west-1'),
                mock.call('s3', region_name='us-west-2'),
            ],
        )
        self.assertEqual(1, s3_client.get_bucket_location.call_count)

    def test_caches_previously_loaded_bucket_regions(self):
        session = mock.Mock()
        s3_client = mock.Mock()
        session.create_client.return_value = s3_client
        s3_client.get_bucket_location.return_value = {'LocationConstraint': ''}
        provider = S3ClientProvider(session)
        provider.get_client('foo')
        self.assertEqual(1, s3_client.get_bucket_location.call_count)
        provider.get_client('foo')
        self.assertEqual(1, s3_client.get_bucket_location.call_count)
        provider.get_client('bar')
        self.assertEqual(2, s3_client.get_bucket_location.call_count)
        provider.get_client('bar')
        self.assertEqual(2, s3_client.get_bucket_location.call_count)

    def test_caches_previously_loaded_clients(self):
        session = mock.Mock()
        s3_client = mock.Mock()
        session.create_client.return_value = s3_client
        s3_client.get_bucket_location.return_value = {'LocationConstraint': ''}
        provider = S3ClientProvider(session)
        client = provider.get_client('foo')
        self.assertEqual(1, session.create_client.call_count)
        self.assertEqual(client, provider.get_client('foo'))
        self.assertEqual(1, session.create_client.call_count)

    def test_removes_cli_error_events(self):
        # We should also remove the error handler for S3.
        # This can be removed once the client switchover is done.
        session = mock.Mock()
        s3_client = mock.Mock()
        session.create_client.return_value = s3_client
        s3_client.get_bucket_location.return_value = {'LocationConstraint': ''}
        provider = S3ClientProvider(session)
        provider.get_client('foo')
