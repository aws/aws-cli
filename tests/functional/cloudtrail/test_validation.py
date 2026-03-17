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
import gzip
import json

from botocore.exceptions import ClientError
from botocore.handlers import parse_get_bucket_location

from awscli.compat import BytesIO
from awscli.customizations.cloudtrail.validation import (
    DATE_FORMAT,
    DigestTraverser,
    S3ClientProvider,
    format_display_date,
)
from awscli.testutils import BaseAWSCommandParamsTest, mock
from tests.unit.customizations.cloudtrail.test_validation import (
    END_DATE,
    START_DATE,
    TEST_ACCOUNT_ID,
    TEST_TRAIL_ARN,
    VALID_TEST_KEY,
    DigestProvider,
    MockDigestProvider,
    create_scenario,
)

RETRIEVER_FUNCTION = (
    'awscli.customizations.cloudtrail.validation.create_digest_traverser'
)
START_TIME_ARG = START_DATE.strftime(DATE_FORMAT)
END_TIME_ARG = END_DATE.strftime(DATE_FORMAT)


def _gz_compress(data):
    out = BytesIO()
    f = gzip.GzipFile(fileobj=out, mode="wb")
    f.write(data.encode())
    f.close()
    return out.getvalue()


def _setup_mock_traverser(
    mock_create_digest_traverser, key_provider, digest_provider, validator
):
    def mock_create(
        trail_arn,
        cloudtrail_client,
        s3_client_provider,
        organization_client,
        trail_source_region,
        bucket,
        prefix,
        on_missing,
        on_invalid,
        on_gap,
        account_id,
    ):
        bucket = bucket or '1'
        return DigestTraverser(
            digest_provider=digest_provider,
            starting_bucket=bucket,
            starting_prefix=prefix,
            public_key_provider=key_provider,
            digest_validator=validator,
            on_invalid=on_invalid,
            on_gap=on_gap,
            on_missing=on_missing,
        )

    mock_create_digest_traverser.side_effect = mock_create


class BaseCloudTrailCommandTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super().setUp()
        # We need to remove this handler to ensure that we can mock out the
        # get_bucket_location operation.
        self.driver.session.unregister(
            'after-call.s3.GetBucketLocation', parse_get_bucket_location
        )
        self._logs = [
            {
                'hashValue': '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a',
                'oldestEventTime': '2015-08-16T22:36:54Z',
                's3Object': 'key1',
                'hashAlgorithm': 'SHA-256',
                's3Bucket': '1',
                'newestEventTime': '2015-08-16T22:36:54Z',
                '_raw_value': '{}',
            },
            {
                'hashValue': '7a38bf81f383f69433ad6e900d35b3e2385593f76a7b7ab5d4355b8ba41ee24b',
                'oldestEventTime': '2015-08-16T22:54:56Z',
                's3Object': 'key2',
                'hashAlgorithm': 'SHA-256',
                's3Bucket': '1',
                'newestEventTime': '2015-08-16T22:55:49Z',
                '_raw_value': '{"foo":"bar"}',
            },
            {
                'hashValue': '5b1070294963f40cb5b3c7a05d3fbaf7ffe4e5d226632026e39cfeb32d349c0c',
                'oldestEventTime': '2015-08-16T21:54:59Z',
                's3Object': 'key3',
                'hashAlgorithm': 'SHA-256',
                's3Bucket': '1',
                'newestEventTime': '2015-08-16T21:54:59Z',
                '_raw_value': '{"baz":"qux"}',
            },
        ]


class TestCloudTrailCommand(BaseCloudTrailCommandTest):
    def setUp(self):
        super().setUp()
        self._traverser_patch = mock.patch(RETRIEVER_FUNCTION)
        self._mock_traverser = self._traverser_patch.start()

    def tearDown(self):
        super().tearDown()
        self._traverser_patch.stop()

    def test_verbose_output_shows_happy_case(self):
        self.parsed_responses = [
            {'LocationConstraint': 'us-east-1'},
            {'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value']))},
            {'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value']))},
        ]
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link'], [[], [self._logs[0]]]
        )
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} "
            "--region us-east-1 --verbose",
            0,
        )
        self.assertIn(
            f'Digest file\ts3://1/{digest_provider.digests[0]}\tvalid',
            stdout,
        )
        self.assertIn('2/2 digest files valid', stdout)
        self.assertIn('2/2 backfill digest files valid', stdout)
        self.assertIn('2/2 log files valid', stdout)
        self.assertIn(
            f'Digest file\ts3://1/{digest_provider.digests[1]}\tvalid',
            stdout,
        )
        self.assertIn('Log file\ts3://1/key1\tvalid', stdout)
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{digest_provider.backfill_digests[0]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{digest_provider.backfill_digests[1]}\tvalid',
            stdout,
        )
        self.assertIn('Log file\ts3://1/key1\tvalid', stdout)

    def test_verbose_output_shows_valid_digests(self):
        key_provider, digest_provider, validator = create_scenario(['gap'], [])
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} --verbose",
            0,
        )
        self.assertIn(
            f'Digest file\ts3://1/{digest_provider.digests[0]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{digest_provider.backfill_digests[0]}\tvalid',
            stdout,
        )
        self.assertIn('1/1 digest files valid', stdout)
        self.assertIn('1/1 backfill digest files valid', stdout)

    def test_warns_when_digest_deleted(self):
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'missing', 'link', 'missing'], []
        )
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} --verbose",
            1,
        )
        self.assertIn(
            f'Digest file\ts3://1/{digest_provider.digests[1]}\tINVALID: not found',
            stderr,
        )
        self.assertIn(
            f'Digest file\ts3://1/{digest_provider.digests[3]}\tINVALID: not found',
            stderr,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{digest_provider.backfill_digests[1]}\tINVALID: not found',
            stderr,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{digest_provider.backfill_digests[3]}\tINVALID: not found',
            stderr,
        )
        self.assertIn(
            '2/4 digest files valid, 2/4 digest files INVALID', stdout
        )
        self.assertIn(
            '2/4 backfill digest files valid, 2/4 backfill digest files INVALID',
            stdout,
        )

    def test_warns_when_no_digests_in_gap(self):
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'gap'], []
        )
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time '{START_TIME_ARG}'",
            0,
        )
        self.assertIn(
            (
                'No log files were delivered by CloudTrail between '
                '2014-08-10T00:00:00Z and 2014-08-10T01:00:00Z'
            ),
            stderr,
        )

    def test_warns_when_digest_invalid(self):
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'invalid', 'link'], []
        )
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG}",
            1,
        )
        self.assertIn('invalid error', stderr)
        self.assertIn(
            f'Results requested for {format_display_date(START_DATE)} to ',
            stdout,
        )
        self.assertIn(
            '2/3 digest files valid, 1/3 digest files INVALID', stdout
        )
        self.assertIn(
            '2/3 backfill digest files valid, 1/3 backfill digest files INVALID',
            stdout,
        )

    def test_shows_successful_summary(self):
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link'], []
        )
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} "
            f"--end-time {END_TIME_ARG} --verbose",
            0,
        )
        self.assertIn(
            (
                'Results requested for 2014-08-10T00:00:00Z to '
                '2015-08-10T00:00:00Z'
            ),
            stdout,
        )
        self.assertIn('2/2 digest files valid', stdout)
        self.assertIn('2/2 backfill digest files valid', stdout)
        self.assertIn(
            'Results found for 2014-08-10T00:00:00Z to 2014-08-10T02:30:00Z',
            stdout,
        )

    def test_warns_when_no_digests_after_start_date(self):
        key_provider = mock.Mock()
        key_provider.get_public_keys.return_value = [{'Fingerprint': 'a'}]
        digest_provider = mock.Mock()
        digest_provider.load_digest_keys_in_range.return_value = []
        validator = mock.Mock()
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f'cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} '
            f'--end-time {END_TIME_ARG}',
            0,
        )
        self.assertIn(
            f'Results requested for {format_display_date(START_DATE)} to {format_display_date(END_DATE)}\nNo digests found',
            stdout,
        )

    def test_warns_when_no_digests_found_in_range(self):
        key_provider = mock.Mock()
        key_provider.get_public_keys.return_value = [{'Fingerprint': 'a'}]
        digest_provider = mock.Mock()
        digest_provider.load_digest_keys_in_range.return_value = []
        validator = mock.Mock()
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time '{START_TIME_ARG}' "
            f"--end-time '{END_TIME_ARG}'",
            0,
        )
        self.assertIn(
            f'Results requested for {format_display_date(START_DATE)} to {format_display_date(END_DATE)}\nNo digests found',
            stdout,
        )

    def test_warns_when_no_valid_digests_found_in_range(self):
        key_provider, digest_provider, validator = create_scenario(
            ['invalid'], []
        )
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time '{START_TIME_ARG}' "
            f"--end-time '{END_TIME_ARG}'",
            1,
        )
        self.assertIn(
            f'Results requested for {format_display_date(START_DATE)} to {format_display_date(END_DATE)}\nNo valid digests found in range',
            stdout,
        )
        self.assertIn('(backfill) invalid error', stderr)
        self.assertIn('invalid error', stderr)
        self.assertIn(
            '0/1 digest files valid, 1/1 digest files INVALID', stdout
        )
        self.assertIn(
            '0/1 backfill digest files valid, 1/1 backfill digest files INVALID',
            stdout,
        )

    def test_fails_and_warns_when_log_hash_is_invalid(self):
        key_provider, digest_provider, validator = create_scenario(
            ['gap'], [[self._logs[0]]]
        )
        self.parsed_responses = [
            {'LocationConstraint': ''},
            {'Body': BytesIO(_gz_compress('does not match'))},
            {'Body': BytesIO(_gz_compress('does not match'))},
        ]
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} --region us-east-1",
            1,
        )
        self.assertIn(
            'Log file\ts3://1/key1\tINVALID: hash value doesn\'t match', stderr
        )
        self.assertIn('1/1 digest files valid', stdout)
        self.assertIn('1/1 backfill digest files valid', stdout)
        self.assertIn('0/2 log files valid, 2/2 log files INVALID', stdout)

    def test_validates_valid_log_files(self):
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link', 'link'],
            [[self._logs[2]], [], [self._logs[0], self._logs[1]]],
        )
        self.parsed_responses = [
            {'LocationConstraint': ''},
            {'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value']))},
            {'Body': BytesIO(_gz_compress(self._logs[1]['_raw_value']))},
            {'Body': BytesIO(_gz_compress(self._logs[2]['_raw_value']))},
            {'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value']))},
            {'Body': BytesIO(_gz_compress(self._logs[1]['_raw_value']))},
            {'Body': BytesIO(_gz_compress(self._logs[2]['_raw_value']))},
        ]
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} --verbose",
            0,
        )
        self.assertIn('s3://1/key1', stdout)
        self.assertIn('s3://1/key2', stdout)
        self.assertIn('s3://1/key3', stdout)
        self.assertIn('Log file\ts3://1/key1\tvalid', stdout)
        self.assertIn('Log file\ts3://1/key2\tvalid', stdout)
        self.assertIn('Log file\ts3://1/key3\tvalid', stdout)
        self.assertIn('3/3 digest files valid', stdout)
        self.assertIn('3/3 backfill digest files valid', stdout)
        self.assertIn('6/6 log files valid', stdout)

    def test_ensures_start_time_before_end_time(self):
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time 2015-01-01 "
            "--end-time 2014-01-01",
            255,
        )
        self.assertIn('start-time must occur before end-time', stderr)

    def test_fails_when_digest_not_from_same_location_as_json_contents(self):
        key_provider, digest_provider, validator = create_scenario(['gap'], [])

        # Use the actual digest keys from the provider
        key_name = digest_provider.digests[0]
        backfill_key_name = digest_provider.backfill_digests[0]
        digest = {
            'digestPublicKeyFingerprint': 'a',
            'digestS3Bucket': 'not_same',
            'digestS3Object': key_name,
            'previousDigestSignature': '...',
            'digestStartTime': '...',
            'digestEndTime': '...',
        }
        backfill_digest = {
            'digestPublicKeyFingerprint': 'a',
            'digestS3Bucket': 'not_same',
            'digestS3Object': backfill_key_name,
            'previousDigestSignature': '...',
            'digestStartTime': '...',
            'digestEndTime': '...',
        }

        def mock_fetch(bucket, key):
            if '_backfill' in key:
                return (backfill_digest, json.dumps(backfill_digest).encode())
            return (digest, json.dumps(digest).encode())

        digest_provider.fetch_digest = mock_fetch

        _setup_mock_traverser(
            self._mock_traverser, mock.Mock(), digest_provider, mock.Mock()
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG}",
            1,
        )
        self.assertIn(
            f'Digest file\ts3://1/{key_name}\tINVALID: has been moved from its '
            'original location',
            stderr,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{backfill_key_name}\tINVALID: has been moved from its '
            'original location',
            stderr,
        )
        self.assertIn(
            '0/1 digest files valid, 1/1 digest files INVALID', stdout
        )
        self.assertIn(
            '0/1 backfill digest files valid, 1/1 backfill digest files INVALID',
            stdout,
        )

    def test_fails_when_digest_is_missing_keys_before_validation(self):
        key_provider, digest_provider, validator = create_scenario(['gap'], [])

        def mock_fetch(bucket, key):
            return ({}, b'{}')

        digest_provider.fetch_digest = mock_fetch

        _setup_mock_traverser(
            self._mock_traverser, mock.Mock(), digest_provider, mock.Mock()
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG}",
            1,
        )
        self.assertIn(
            f'Digest file\ts3://1/{digest_provider.digests[0]}\tINVALID: invalid format',
            stderr,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{digest_provider.backfill_digests[0]}\tINVALID: invalid format',
            stderr,
        )
        self.assertIn(
            '0/1 digest files valid, 1/1 digest files INVALID', stdout
        )
        self.assertIn(
            '0/1 backfill digest files valid, 1/1 backfill digest files INVALID',
            stdout,
        )

    def test_fails_when_digest_metadata_is_missing(self):
        key = MockDigestProvider([]).get_key_at_position(1)
        backfill_key = MockDigestProvider([]).get_key_at_position(
            1, is_backfill=True
        )
        self.parsed_responses = [
            {'LocationConstraint': ''},
            {'Contents': [{'Key': key}, {'Key': backfill_key}]},
            {
                'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value'])),
                'Metadata': {},
            },
            {
                'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value'])),
                'Metadata': {},
            },
        ]
        s3_client_provider = S3ClientProvider(self.driver.session, 'us-east-1')
        digest_provider = DigestProvider(
            s3_client_provider, TEST_ACCOUNT_ID, 'foo', 'us-east-1'
        )
        key_provider = mock.Mock()
        key_provider.get_public_keys.return_value = {
            'a': {'Value': VALID_TEST_KEY}
        }
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, mock.Mock()
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} "
            "--region us-east-1",
            1,
        )
        self.assertIn(
            f'Digest file\ts3://1/{key}\tINVALID: signature verification failed',
            stderr,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{backfill_key}\tINVALID: signature verification failed',
            stderr,
        )
        self.assertIn(
            '0/1 digest files valid, 1/1 digest files INVALID', stdout
        )
        self.assertIn(
            '0/1 backfill digest files valid, 1/1 backfill digest files INVALID',
            stdout,
        )

    def test_follows_trails_when_bucket_changes(self):
        self.parsed_responses = [
            {'LocationConstraint': 'us-east-1'},
            {'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value']))},
            {'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value']))},
        ]
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'bucket_change', 'link', 'bucket_change', 'link'],
            [[], [self._logs[0]], [], [], []],
        )
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} "
            "--region us-east-1 --verbose",
            0,
        )
        self.assertIn(
            f'Digest file\ts3://3/{digest_provider.digests[0]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'Digest file\ts3://2/{digest_provider.digests[1]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'Digest file\ts3://2/{digest_provider.digests[2]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'Digest file\ts3://1/{digest_provider.digests[3]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'Digest file\ts3://1/{digest_provider.digests[4]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://3/{digest_provider.backfill_digests[0]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://2/{digest_provider.backfill_digests[1]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://2/{digest_provider.backfill_digests[2]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{digest_provider.backfill_digests[3]}\tvalid',
            stdout,
        )
        self.assertIn(
            f'(backfill) Digest file\ts3://1/{digest_provider.backfill_digests[4]}\tvalid',
            stdout,
        )
        self.assertIn('Log file\ts3://1/key1\tvalid', stdout)
        self.assertIn('Log file\ts3://1/key1\tvalid', stdout)
        self.assertIn('5/5 digest files valid', stdout)
        self.assertIn('5/5 backfill digest files valid', stdout)
        self.assertIn('2/2 log files valid', stdout)

    def test_validates_standard_digests_only(self):
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link'], [[], [self._logs[0]]]
        )
        original_load = digest_provider.load_digest_keys_in_range

        def mock_load_keys(
            bucket, prefix, start_date, end_date, is_backfill=False
        ):
            if is_backfill:
                return []
            return original_load(
                bucket, prefix, start_date, end_date, is_backfill=False
            )

        digest_provider.load_digest_keys_in_range = mock_load_keys

        self.parsed_responses = [
            {'LocationConstraint': 'us-east-1'},
            {'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value']))},
        ]
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} --verbose",
            0,
        )
        self.assertIn('2/2 digest files valid', stdout)
        self.assertIn('1/1 log files valid', stdout)
        self.assertNotIn('(backfill)', stdout)
        self.assertIn(
            'Results found for 2014-08-10T00:00:00Z to 2014-08-10T02:30:00Z',
            stdout,
        )

    def test_validates_backfill_digests_only(self):
        key_provider, digest_provider, validator = create_scenario(
            ['gap', 'link'], [[], [self._logs[0]]]
        )
        original_load = digest_provider.load_digest_keys_in_range

        def mock_load_keys(
            bucket, prefix, start_date, end_date, is_backfill=False
        ):
            if not is_backfill:
                return []
            return original_load(
                bucket, prefix, start_date, end_date, is_backfill=True
            )

        digest_provider.load_digest_keys_in_range = mock_load_keys

        self.parsed_responses = [
            {'LocationConstraint': 'us-east-1'},
            {'Body': BytesIO(_gz_compress(self._logs[0]['_raw_value']))},
        ]
        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} --verbose",
            0,
        )
        self.assertIn('(backfill) Digest file\ts3://1/', stdout)
        self.assertIn('Log file\ts3://1/key1\tvalid', stdout)
        self.assertIn('2/2 backfill digest files valid', stdout)
        self.assertIn('1/1 log files valid', stdout)
        self.assertIn(
            'Results found for 2014-08-10T00:00:00Z to 2014-08-10T02:30:00Z',
            stdout,
        )

    def _setup_mixed_period_providers(
        self, standard_actions, backfill_actions, logs=None
    ):
        """Helper method to set up mixed period test scenarios with proper key alignment."""
        key_provider, digest_provider, validator = create_scenario(
            standard_actions, logs or []
        )
        key_provider_bf, digest_provider_bf, _ = create_scenario(
            backfill_actions, logs or []
        )

        combined_keys = {}
        combined_keys.update(key_provider.get_public_keys.return_value)
        combined_keys.update(key_provider_bf.get_public_keys.return_value)
        key_provider.get_public_keys.return_value = combined_keys

        original_load = digest_provider.load_digest_keys_in_range
        original_load_bf = digest_provider_bf.load_digest_keys_in_range
        original_fetch = digest_provider.fetch_digest
        original_fetch_bf = digest_provider_bf.fetch_digest

        def mock_load_keys(
            bucket, prefix, start_date, end_date, is_backfill=False
        ):
            if is_backfill:
                return original_load_bf(
                    bucket, prefix, start_date, end_date, is_backfill=True
                )
            return original_load(
                bucket, prefix, start_date, end_date, is_backfill=False
            )

        def mock_fetch(bucket, key):
            if '_backfill' in key:
                return original_fetch_bf(bucket, key)
            return original_fetch(bucket, key)

        digest_provider.load_digest_keys_in_range = mock_load_keys
        digest_provider.fetch_digest = mock_fetch

        return key_provider, digest_provider, validator

    def test_validates_mixed_digests_standard_smaller_period(self):
        """Test validation when standard digests have smaller time period than backfill digests."""
        key_provider, digest_provider, validator = (
            self._setup_mixed_period_providers(
                ['gap'], ['gap', 'link', 'link'], [[]] * 4
            )
        )

        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} --verbose",
            0,
        )
        self.assertIn('1/1 digest files valid', stdout)
        self.assertIn('3/3 backfill digest files valid', stdout)
        self.assertIn(
            'Results found for 2014-08-10T00:00:00Z to 2014-08-10T03:30:00Z',
            stdout,
        )

    def test_validates_mixed_digests_backfill_smaller_period(self):
        key_provider, digest_provider, validator = (
            self._setup_mixed_period_providers(
                ['gap', 'link', 'link'], ['gap'], [[], [], [], []]
            )
        )

        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG} --verbose",
            0,
        )
        self.assertIn('3/3 digest files valid', stdout)
        self.assertIn('1/1 backfill digest files valid', stdout)
        self.assertIn(
            'Results found for 2014-08-10T00:00:00Z to 2014-08-10T03:30:00Z',
            stdout,
        )

    def test_fails_when_digest_public_key_not_found(self):
        key_provider, digest_provider, validator = create_scenario(['gap'], [])
        key_provider.get_public_keys.return_value = {
            'wrong_fp': {'Fingerprint': 'wrong_fp', 'Value': 'wrong_key'}
        }

        _setup_mock_traverser(
            self._mock_traverser, key_provider, digest_provider, validator
        )
        stdout, stderr, rc = self.run_cmd(
            f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time {START_TIME_ARG}",
            1,
        )
        error_lines = stderr.split('\n')
        standard_errors = [
            line
            for line in error_lines
            if 'public key not found' in line and '(backfill)' not in line
        ]
        backfill_errors = [
            line
            for line in error_lines
            if 'public key not found' in line and '(backfill)' in line
        ]

        self.assertEqual(1, len(standard_errors))
        self.assertEqual(1, len(backfill_errors))
        self.assertIn('public key not found', standard_errors[0])
        self.assertIn('public key not found', backfill_errors[0])

        self.assertIn(
            '0/1 digest files valid, 1/1 digest files INVALID', stdout
        )
        self.assertIn(
            '0/1 backfill digest files valid, 1/1 backfill digest files INVALID',
            stdout,
        )


class TestCloudTrailCommandWithMissingLogs(BaseCloudTrailCommandTest):
    """This test class is necessary in order to override the default patching
    behavior of BaseAWSCommandParamsTest. Instead of returning responses from
    a queue, we want to raise a ClientError.
    """

    def test_fails_and_warns_when_log_is_deleted(self):
        # Override the default request patching because we need to
        # raise a ClientError exception.
        key_provider, digest_provider, validator = create_scenario(
            ['gap'], [[self._logs[0]]]
        )
        with mock.patch(RETRIEVER_FUNCTION) as mock_create_digest_traverser:
            _setup_mock_traverser(
                mock_create_digest_traverser,
                key_provider,
                digest_provider,
                validator,
            )
            stdout, stderr, rc = self.run_cmd(
                f"cloudtrail validate-logs --trail-arn {TEST_TRAIL_ARN} --start-time '{START_TIME_ARG}'",
                1,
            )
            self.assertIn(
                'Log file\ts3://1/key1\tINVALID: not found\n\n', stderr
            )
            self.assertIn(
                'Log file\ts3://1/key1\tINVALID: not found\n\n',
                stderr,
            )
            self.assertIn('1/1 digest files valid', stdout)
            self.assertIn('1/1 backfill digest files valid', stdout)
            self.assertIn('0/2 log files valid, 2/2 log files INVALID', stdout)

    def patch_make_request(self):
        """Override the default request patching because we need to
        raise a ClientError exception.
        """
        self.make_request_is_patched = True
        make_request_patch = self.make_request_patch.start()
        make_request_patch.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'foo'}}, 'GetObject'
        )
