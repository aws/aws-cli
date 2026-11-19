# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import botocore.exceptions
import botocore.session
import pytest
from botocore import credentials
from botocore.compat import json
from botocore.configprovider import (
    ConfigChainFactory,
    ConfigValueStore,
    create_botocore_default_config_mapping,
)
from botocore.credentials import (
    AssumeRoleProvider,
    AssumeRoleWithWebIdentityProvider,
    BaseAssumeRoleCredentialFetcher,
    ConfigProvider,
    CredentialProvider,
    Credentials,
    EnvProvider,
    LoginProvider,
    ProcessProvider,
    ProfileProviderBuilder,
    SharedCredentialProvider,
    SSOCredentialFetcher,
    SSOProvider,
    create_assume_role_refresher,
)
from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    LoginError,
    LoginInvalidCachedTokenError,
    RefreshNonRecoverableError,
    SSOTokenLoadError,
    TokenRetrievalError,
    UnauthorizedSSOTokenError,
)
from botocore.session import Session
from botocore.stub import Stubber
from botocore.utils import (
    ContainerMetadataFetcher,
    FileWebIdentityTokenLoader,
    SSOTokenLoader,
    datetime2timestamp,
)
from dateutil.tz import tzlocal, tzutc

from tests import BaseEnvVar, IntegerRefresher, mock, skip_if_windows, unittest

# Passed to session to keep it from finding default config file
TESTENVVARS = {'config_file': (None, 'AWS_CONFIG_FILE', None)}

SAMPLE_SIGN_IN_DPOP_PEM = (
    '-----BEGIN EC PRIVATE KEY-----\n'
    'MHcCAQEEIDXxfh2F6vl+AX+tK/jvY5ll6aZ9n8sI2ODsWCmrsx'
    'SDoAoGCCqGSM49\nAwEHoUQDQgAERKnl1X15pEx7ebbMQ0dFw6'
    'VeOuCjEuh3NT8dwnBHYyF/7YDy8+Fu\nCx+4wgiSs9sRD3LaDK'
    'CjIbbmEq07Jw59YQ==\n-----END EC PRIVATE KEY-----\n'
)


raw_metadata = {
    'foobar': {
        'Code': 'Success',
        'LastUpdated': '2012-12-03T14:38:21Z',
        'AccessKeyId': 'foo',
        'SecretAccessKey': 'bar',
        'Token': 'foobar',
        'Expiration': '2012-12-03T20:48:03Z',
        'Type': 'AWS-HMAC',
    }
}
post_processed_metadata = {
    'role_name': 'foobar',
    'access_key': raw_metadata['foobar']['AccessKeyId'],
    'secret_key': raw_metadata['foobar']['SecretAccessKey'],
    'token': raw_metadata['foobar']['Token'],
    'expiry_time': raw_metadata['foobar']['Expiration'],
}


def path(filename):
    return os.path.join(os.path.dirname(__file__), 'cfg', filename)


class PausingRefreshableCredentials(credentials.RefreshableCredentials):
    def _publish_refresh(self):
        self.publish_started.set()
        if not self.resume_publish.wait(timeout=1):
            raise AssertionError("Timed out waiting to publish credentials")
        super()._publish_refresh()


class PausingResilientRefreshableCredentials(
    credentials._ResilientRefreshableCredentials
):
    def _publish_refresh(self):
        self.publish_started.set()
        if not self.resume_publish.wait(timeout=1):
            raise AssertionError("Timed out waiting to publish credentials")
        super()._publish_refresh()


class TestCredentials(BaseEnvVar):
    def _ensure_credential_is_normalized_as_unicode(self, access, secret):
        c = credentials.Credentials(access, secret)
        self.assertTrue(isinstance(c.access_key, str))
        self.assertTrue(isinstance(c.secret_key, str))

    def test_detect_nonascii_character(self):
        self._ensure_credential_is_normalized_as_unicode(
            'foo\xe2\x80\x99', 'bar\xe2\x80\x99'
        )

    def test_unicode_input(self):
        self._ensure_credential_is_normalized_as_unicode('foo', 'bar')


class TestRefreshableCredentials(TestCredentials):
    def setUp(self):
        super().setUp()
        self.refresher = mock.Mock()
        self.future_time = datetime.now(tzlocal()) + timedelta(hours=24)
        self.expiry_time = datetime.now(tzlocal()) - timedelta(minutes=30)
        self.metadata = {
            'access_key': 'NEW-ACCESS',
            'secret_key': 'NEW-SECRET',
            'token': 'NEW-TOKEN',
            'expiry_time': self.future_time.isoformat(),
            'role_name': 'rolename',
        }
        self.refresher.return_value = self.metadata
        self.mock_time = mock.Mock()
        self.creds = credentials.RefreshableCredentials(
            'ORIGINAL-ACCESS',
            'ORIGINAL-SECRET',
            'ORIGINAL-TOKEN',
            self.expiry_time,
            self.refresher,
            'iam-role',
            time_fetcher=self.mock_time,
        )

    def test_refresh_needed(self):
        # The expiry time was set for 30 minutes ago, so if we
        # say the current time is utcnow(), then we should need
        # a refresh.
        self.mock_time.return_value = datetime.now(tzlocal())
        self.assertTrue(self.creds.refresh_needed())
        # We should refresh creds, if we try to access "access_key"
        # or any of the cred vars.
        self.assertEqual(self.creds.access_key, 'NEW-ACCESS')
        self.assertEqual(self.creds.secret_key, 'NEW-SECRET')
        self.assertEqual(self.creds.token, 'NEW-TOKEN')

    def test_no_expiration(self):
        creds = credentials.RefreshableCredentials(
            'ORIGINAL-ACCESS',
            'ORIGINAL-SECRET',
            'ORIGINAL-TOKEN',
            None,
            self.refresher,
            'iam-role',
            time_fetcher=self.mock_time,
        )
        self.assertFalse(creds.refresh_needed())

    def test_no_refresh_needed(self):
        # The expiry time was 30 minutes ago, let's say it's an hour
        # ago currently.  That would mean we don't need a refresh.
        self.mock_time.return_value = datetime.now(tzlocal()) - timedelta(
            minutes=60
        )
        self.assertTrue(not self.creds.refresh_needed())

        self.assertEqual(self.creds.access_key, 'ORIGINAL-ACCESS')
        self.assertEqual(self.creds.secret_key, 'ORIGINAL-SECRET')
        self.assertEqual(self.creds.token, 'ORIGINAL-TOKEN')

    def test_get_credentials_set(self):
        # We need to return a consistent set of credentials to use during the
        # signing process.
        self.mock_time.return_value = datetime.now(tzlocal()) - timedelta(
            minutes=60
        )
        self.assertTrue(not self.creds.refresh_needed())
        credential_set = self.creds.get_frozen_credentials()
        self.assertEqual(credential_set.access_key, 'ORIGINAL-ACCESS')
        self.assertEqual(credential_set.secret_key, 'ORIGINAL-SECRET')
        self.assertEqual(credential_set.token, 'ORIGINAL-TOKEN')

    def test_concurrent_reader_gets_refreshed_frozen_credentials(self):
        self.mock_time.return_value = self.expiry_time + timedelta(hours=1)
        creds = PausingRefreshableCredentials(
            'ORIGINAL-ACCESS',
            'ORIGINAL-SECRET',
            'ORIGINAL-TOKEN',
            self.expiry_time,
            self.refresher,
            'iam-role',
            time_fetcher=self.mock_time,
        )
        creds.publish_started = threading.Event()
        creds.resume_publish = threading.Event()
        expected_credentials = credentials.ReadOnlyCredentials(
            'NEW-ACCESS',
            'NEW-SECRET',
            'NEW-TOKEN',
        )

        with ThreadPoolExecutor(max_workers=2) as executor:
            refresh = executor.submit(creds.get_frozen_credentials)
            try:
                self.assertTrue(creds.publish_started.wait(timeout=1))
                reader = executor.submit(creds.get_frozen_credentials)
                self.assertTrue(creds.refresh_needed())
            finally:
                creds.resume_publish.set()

            self.assertEqual(refresh.result(timeout=1), expected_credentials)
            self.assertEqual(reader.result(timeout=1), expected_credentials)

        self.assertEqual(self.refresher.call_count, 1)

    def test_refresh_returns_empty_dict(self):
        self.refresher.return_value = {}
        self.mock_time.return_value = datetime.now(tzlocal())
        self.assertTrue(self.creds.refresh_needed())

        with self.assertRaises(botocore.exceptions.CredentialRetrievalError):
            self.creds.access_key

    def test_refresh_returns_none(self):
        self.refresher.return_value = None
        self.mock_time.return_value = datetime.now(tzlocal())
        self.assertTrue(self.creds.refresh_needed())

        with self.assertRaises(botocore.exceptions.CredentialRetrievalError):
            self.creds.access_key

    def test_refresh_returns_partial_credentials(self):
        self.refresher.return_value = {'access_key': 'akid'}
        self.mock_time.return_value = datetime.now(tzlocal())
        self.assertTrue(self.creds.refresh_needed())

        with self.assertRaises(botocore.exceptions.CredentialRetrievalError):
            self.creds.access_key

    def test_create_from_metadata_uses_default_advisory_window(self):
        now = datetime.now(tzlocal())
        initial_metadata = {
            'access_key': 'ORIGINAL-ACCESS',
            'secret_key': 'ORIGINAL-SECRET',
            'token': 'ORIGINAL-TOKEN',
            'expiry_time': (
                now + timedelta(minutes=15, seconds=3)
            ).isoformat(),
        }
        self.refresher.return_value = {
            'access_key': 'NEW-ACCESS',
            'secret_key': 'NEW-SECRET',
            'token': 'NEW-TOKEN',
            'expiry_time': (now + timedelta(minutes=120)).isoformat(),
        }
        creds = credentials.RefreshableCredentials.create_from_metadata(
            initial_metadata,
            refresh_using=self.refresher,
            method='custom',
        )
        creds._time_fetcher = self.mock_time

        self.mock_time.return_value = now
        self.assertEqual(
            creds.get_frozen_credentials().access_key, 'ORIGINAL-ACCESS'
        )
        self.refresher.assert_not_called()

        self.mock_time.return_value = now + timedelta(seconds=6)
        self.assertEqual(
            creds.get_frozen_credentials().access_key, 'NEW-ACCESS'
        )
        self.refresher.assert_called_once_with()

    def test_create_from_metadata_mandatory_refresh_failure_raises(self):
        now = datetime.now(tzlocal())
        metadata = {
            'access_key': 'ORIGINAL-ACCESS',
            'secret_key': 'ORIGINAL-SECRET',
            'token': 'ORIGINAL-TOKEN',
            'expiry_time': (now + timedelta(minutes=5)).isoformat(),
        }
        self.refresher.side_effect = (
            botocore.exceptions.CredentialRetrievalError(
                provider='custom', error_msg='source down'
            )
        )
        creds = credentials.RefreshableCredentials.create_from_metadata(
            metadata,
            refresh_using=self.refresher,
            method='custom',
        )
        creds._time_fetcher = self.mock_time
        self.mock_time.return_value = now

        with self.assertRaises(botocore.exceptions.CredentialRetrievalError):
            creds.get_frozen_credentials()


class TestDeferredRefreshableCredentials(unittest.TestCase):
    def setUp(self):
        self.refresher = mock.Mock()
        self.future_time = datetime.now(tzlocal()) + timedelta(hours=24)
        self.metadata = {
            'access_key': 'NEW-ACCESS',
            'secret_key': 'NEW-SECRET',
            'token': 'NEW-TOKEN',
            'expiry_time': self.future_time.isoformat(),
            'role_name': 'rolename',
        }
        self.refresher.return_value = self.metadata
        self.mock_time = mock.Mock()
        self.mock_time.return_value = datetime.now(tzlocal())

    def test_refresh_using_called_on_first_access(self):
        creds = credentials.DeferredRefreshableCredentials(
            self.refresher, 'iam-role', self.mock_time
        )

        # The credentials haven't been accessed, so there should be no calls.
        self.refresher.assert_not_called()

        # Now that the object has been accessed, it should have called the
        # refresher
        creds.get_frozen_credentials()
        self.assertEqual(self.refresher.call_count, 1)

    def test_refresh_only_called_once(self):
        creds = credentials.DeferredRefreshableCredentials(
            self.refresher, 'iam-role', self.mock_time
        )

        for _ in range(5):
            creds.get_frozen_credentials()

        # The credentials were accessed several times in a row, but only
        # should call refresh once.
        self.assertEqual(self.refresher.call_count, 1)

    def test_uses_default_advisory_window_after_first_fetch(self):
        now = datetime.now(tzlocal())
        self.mock_time.return_value = now
        self.refresher.side_effect = [
            {
                'access_key': 'FIRST-ACCESS',
                'secret_key': 'FIRST-SECRET',
                'token': 'FIRST-TOKEN',
                'expiry_time': (
                    now + timedelta(minutes=15, seconds=3)
                ).isoformat(),
            },
            {
                'access_key': 'SECOND-ACCESS',
                'secret_key': 'SECOND-SECRET',
                'token': 'SECOND-TOKEN',
                'expiry_time': (now + timedelta(minutes=120)).isoformat(),
            },
        ]
        creds = credentials.DeferredRefreshableCredentials(
            self.refresher, 'custom', self.mock_time
        )

        self.assertEqual(
            creds.get_frozen_credentials().access_key, 'FIRST-ACCESS'
        )
        self.assertEqual(self.refresher.call_count, 1)

        self.mock_time.return_value = now + timedelta(seconds=6)
        self.assertEqual(
            creds.get_frozen_credentials().access_key, 'SECOND-ACCESS'
        )
        self.assertEqual(self.refresher.call_count, 2)

    def test_mandatory_refresh_failure_after_first_fetch_raises(self):
        now = datetime.now(tzlocal())
        self.mock_time.return_value = now
        self.refresher.side_effect = [
            {
                'access_key': 'FIRST-ACCESS',
                'secret_key': 'FIRST-SECRET',
                'token': 'FIRST-TOKEN',
                'expiry_time': (now + timedelta(minutes=5)).isoformat(),
            },
            botocore.exceptions.CredentialRetrievalError(
                provider='custom', error_msg='source down'
            ),
        ]
        creds = credentials.DeferredRefreshableCredentials(
            self.refresher, 'custom', self.mock_time
        )

        self.assertEqual(
            creds.get_frozen_credentials().access_key, 'FIRST-ACCESS'
        )
        with self.assertRaises(botocore.exceptions.CredentialRetrievalError):
            creds.get_frozen_credentials()


class TestAssumeRoleCredentialFetcher(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.source_creds = credentials.Credentials('a', 'b', 'c')
        self.role_arn = 'myrole'

    def create_client_creator(self, with_response):
        # Create a mock sts client that returns a specific response
        # for assume_role.
        client = mock.Mock()
        if isinstance(with_response, list):
            client.assume_role.side_effect = with_response
        else:
            client.assume_role.return_value = with_response
        return mock.Mock(return_value=client)

    def get_expected_creds_from_response(self, response):
        expiration = response['Credentials']['Expiration']
        if isinstance(expiration, datetime):
            expiration = expiration.isoformat()
        return {
            'access_key': response['Credentials']['AccessKeyId'],
            'secret_key': response['Credentials']['SecretAccessKey'],
            'token': response['Credentials']['SessionToken'],
            'expiry_time': expiration,
            'account_id': response.get('Credentials', {}).get('AccountId'),
        }

    def some_future_time(self):
        timeobj = datetime.now(tzlocal())
        return timeobj + timedelta(hours=24)

    def test_no_cache(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator, self.source_creds, self.role_arn
        )

        expected_response = self.get_expected_creds_from_response(response)
        response = refresher.fetch_credentials()

        self.assertEqual(response, expected_response)

    def test_expiration_in_datetime_format(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                # Note the lack of isoformat(), we're using
                # a datetime.datetime type.  This will ensure
                # we test both parsing as well as serializing
                # from a given datetime because the credentials
                # are immediately expired.
                'Expiration': self.some_future_time(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator, self.source_creds, self.role_arn
        )

        expected_response = self.get_expected_creds_from_response(response)
        response = refresher.fetch_credentials()

        self.assertEqual(response, expected_response)

    def test_retrieves_from_cache(self):
        date_in_future = datetime.utcnow() + timedelta(seconds=1000)
        utc_timestamp = date_in_future.isoformat() + 'Z'
        cache_key = '793d6e2f27667ab2da104824407e486bfec24a47'
        cache = {
            cache_key: {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': utc_timestamp,
                }
            }
        }
        client_creator = mock.Mock()
        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator, self.source_creds, self.role_arn, cache=cache
        )

        expected_response = self.get_expected_creds_from_response(
            cache[cache_key]
        )
        response = refresher.fetch_credentials()

        self.assertEqual(response, expected_response)
        client_creator.assert_not_called()

    def test_cache_key_is_windows_safe(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        cache = {}
        client_creator = self.create_client_creator(with_response=response)

        role_arn = 'arn:aws:iam::role/foo-role'
        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator, self.source_creds, role_arn, cache=cache
        )

        refresher.fetch_credentials()

        # On windows, you cannot use a a ':' in the filename, so
        # we need to make sure that it doesn't make it into the cache key.
        cache_key = '75c539f0711ba78c5b9e488d0add95f178a54d74'
        self.assertIn(cache_key, cache)
        self.assertEqual(cache[cache_key], response)

    def test_cache_key_with_role_session_name(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        cache = {}
        client_creator = self.create_client_creator(with_response=response)
        role_session_name = 'my_session_name'

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator,
            self.source_creds,
            self.role_arn,
            cache=cache,
            extra_args={'RoleSessionName': role_session_name},
        )
        refresher.fetch_credentials()

        # This is the sha256 hex digest of the expected assume role args.
        cache_key = '2964201f5648c8be5b9460a9cf842d73a266daf2'
        self.assertIn(cache_key, cache)
        self.assertEqual(cache[cache_key], response)

    def test_cache_key_with_policy(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        cache = {}
        client_creator = self.create_client_creator(with_response=response)
        policy = json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": "*", "Resource": "*"}
                ],
            }
        )

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator,
            self.source_creds,
            self.role_arn,
            cache=cache,
            extra_args={'Policy': policy},
        )
        refresher.fetch_credentials()

        # This is the sha256 hex digest of the expected assume role args.
        cache_key = '176f223d915e82456c253545e192aa21d68f5ab8'
        self.assertIn(cache_key, cache)
        self.assertEqual(cache[cache_key], response)

    def test_assume_role_in_cache_but_expired(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        cache = {
            'development--myrole': {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': datetime.now(tzlocal()),
                }
            }
        }

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator, self.source_creds, self.role_arn, cache=cache
        )
        expected = self.get_expected_creds_from_response(response)
        response = refresher.fetch_credentials()

        self.assertEqual(response, expected)

    def test_role_session_name_can_be_provided(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        role_session_name = 'myname'

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator,
            self.source_creds,
            self.role_arn,
            extra_args={'RoleSessionName': role_session_name},
        )
        refresher.fetch_credentials()

        client = client_creator.return_value
        client.assume_role.assert_called_with(
            RoleArn=self.role_arn, RoleSessionName=role_session_name
        )

    def test_external_id_can_be_provided(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        external_id = 'my_external_id'

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator,
            self.source_creds,
            self.role_arn,
            extra_args={'ExternalId': external_id},
        )
        refresher.fetch_credentials()

        client = client_creator.return_value
        client.assume_role.assert_called_with(
            RoleArn=self.role_arn,
            ExternalId=external_id,
            RoleSessionName=mock.ANY,
        )

    def test_policy_can_be_provided(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        policy = json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": "*", "Resource": "*"}
                ],
            }
        )

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator,
            self.source_creds,
            self.role_arn,
            extra_args={'Policy': policy},
        )
        refresher.fetch_credentials()

        client = client_creator.return_value
        client.assume_role.assert_called_with(
            RoleArn=self.role_arn, Policy=policy, RoleSessionName=mock.ANY
        )

    def test_duration_seconds_can_be_provided(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        duration = 1234

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator,
            self.source_creds,
            self.role_arn,
            extra_args={'DurationSeconds': duration},
        )
        refresher.fetch_credentials()

        client = client_creator.return_value
        client.assume_role.assert_called_with(
            RoleArn=self.role_arn,
            DurationSeconds=duration,
            RoleSessionName=mock.ANY,
        )

    def test_mfa(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        prompter = mock.Mock(return_value='token-code')
        mfa_serial = 'mfa'

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator,
            self.source_creds,
            self.role_arn,
            extra_args={'SerialNumber': mfa_serial},
            mfa_prompter=prompter,
        )
        refresher.fetch_credentials()

        client = client_creator.return_value
        # In addition to the normal assume role args, we should also
        # inject the serial number from the config as well as the
        # token code that comes from prompting the user (the prompter
        # object).
        client.assume_role.assert_called_with(
            RoleArn='myrole',
            RoleSessionName=mock.ANY,
            SerialNumber='mfa',
            TokenCode='token-code',
        )

    def test_refreshes(self):
        responses = [
            {
                'Credentials': {
                    'AccessKeyId': 'foo',
                    'SecretAccessKey': 'bar',
                    'SessionToken': 'baz',
                    # We're creating an expiry time in the past so as
                    # soon as we try to access the credentials, the
                    # refresh behavior will be triggered.
                    'Expiration': (
                        datetime.now(tzlocal()) - timedelta(seconds=100)
                    ).isoformat(),
                },
            },
            {
                'Credentials': {
                    'AccessKeyId': 'foo',
                    'SecretAccessKey': 'bar',
                    'SessionToken': 'baz',
                    'Expiration': self.some_future_time().isoformat(),
                }
            },
        ]
        client_creator = self.create_client_creator(with_response=responses)

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator, self.source_creds, self.role_arn
        )

        # The first call will simply use whatever credentials it is given.
        # The second will check the cache, and only make a call if the
        # cached credentials are expired.
        refresher.fetch_credentials()
        refresher.fetch_credentials()

        client = client_creator.return_value
        assume_role_calls = client.assume_role.call_args_list
        self.assertEqual(len(assume_role_calls), 2, assume_role_calls)

    def test_mfa_refresh_enabled(self):
        responses = [
            {
                'Credentials': {
                    'AccessKeyId': 'foo',
                    'SecretAccessKey': 'bar',
                    'SessionToken': 'baz',
                    # We're creating an expiry time in the past so as
                    # soon as we try to access the credentials, the
                    # refresh behavior will be triggered.
                    'Expiration': (
                        datetime.now(tzlocal()) - timedelta(seconds=100)
                    ).isoformat(),
                },
            },
            {
                'Credentials': {
                    'AccessKeyId': 'foo',
                    'SecretAccessKey': 'bar',
                    'SessionToken': 'baz',
                    'Expiration': self.some_future_time().isoformat(),
                }
            },
        ]
        client_creator = self.create_client_creator(with_response=responses)

        token_code = 'token-code-1'
        prompter = mock.Mock(side_effect=[token_code])
        mfa_serial = 'mfa'

        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator,
            self.source_creds,
            self.role_arn,
            extra_args={'SerialNumber': mfa_serial},
            mfa_prompter=prompter,
        )

        # This is will refresh credentials if they're expired. Because
        # we set the expiry time to something in the past, this will
        # trigger the refresh behavior.
        refresher.fetch_credentials()

        assume_role = client_creator.return_value.assume_role
        calls = [c[1] for c in assume_role.call_args_list]
        expected_calls = [
            {
                'RoleArn': self.role_arn,
                'RoleSessionName': mock.ANY,
                'SerialNumber': mfa_serial,
                'TokenCode': token_code,
            }
        ]
        self.assertEqual(calls, expected_calls)

    def test_account_id_with_valid_arn(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
                'AccountId': '123456789012',
            },
            'AssumedRoleUser': {
                'AssumedRoleId': 'myroleid',
                'Arn': 'arn:aws:iam::123456789012:role/RoleA',
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator, self.source_creds, self.role_arn
        )
        expected_response = self.get_expected_creds_from_response(response)
        response = refresher.fetch_credentials()
        self.assertEqual(response, expected_response)
        self.assertEqual(response['account_id'], '123456789012')

    def test_account_id_with_invalid_arn(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
            'AssumedRoleUser': {
                'AssumedRoleId': 'myroleid',
                'Arn': 'invalid-arn',
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        refresher = credentials.AssumeRoleCredentialFetcher(
            client_creator, self.source_creds, self.role_arn
        )
        expected_response = self.get_expected_creds_from_response(response)
        response = refresher.fetch_credentials()
        self.assertEqual(response, expected_response)
        self.assertEqual(response['account_id'], None)

    @mock.patch('botocore.credentials.register_feature_ids')
    def test_feature_ids_registered_during_get_credentials(
        self, mock_register
    ):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time(),
            }
        }
        client_creator = self.create_client_creator(with_response=response)
        fetcher = credentials.AssumeRoleCredentialFetcher(
            client_creator, self.source_creds, self.role_arn
        )

        test_feature_ids = {'test_feature_1', 'test_feature_2'}
        fetcher.feature_ids = test_feature_ids

        fetcher.fetch_credentials()
        # Verify register_credential_feature_ids was called with test feature IDs
        mock_register.assert_called_once_with(test_feature_ids)


class TestAssumeRoleWithWebIdentityCredentialFetcher(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.role_arn = 'myrole'

    def load_token(self):
        return 'totally.a.token'

    def some_future_time(self):
        timeobj = datetime.now(tzlocal())
        return timeobj + timedelta(hours=24)

    def create_client_creator(self, with_response):
        # Create a mock sts client that returns a specific response
        # for assume_role.
        client = mock.Mock()
        if isinstance(with_response, list):
            client.assume_role_with_web_identity.side_effect = with_response
        else:
            client.assume_role_with_web_identity.return_value = with_response
        return mock.Mock(return_value=client)

    def get_expected_creds_from_response(self, response):
        expiration = response['Credentials']['Expiration']
        if isinstance(expiration, datetime):
            expiration = expiration.isoformat()
        return {
            'access_key': response['Credentials']['AccessKeyId'],
            'secret_key': response['Credentials']['SecretAccessKey'],
            'token': response['Credentials']['SessionToken'],
            'expiry_time': expiration,
            'account_id': response.get('Credentials', {}).get('AccountId'),
        }

    def test_no_cache(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        refresher = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, self.load_token, self.role_arn
        )
        expected_response = self.get_expected_creds_from_response(response)
        response = refresher.fetch_credentials()

        self.assertEqual(response, expected_response)

    def test_retrieves_from_cache(self):
        date_in_future = datetime.utcnow() + timedelta(seconds=1000)
        utc_timestamp = date_in_future.isoformat() + 'Z'
        cache_key = '3f7f13ece7d7b07c65483f4ea63d31c8bdb894f4'
        cache = {
            cache_key: {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': utc_timestamp,
                }
            }
        }
        client_creator = mock.Mock()
        refresher = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, self.load_token, self.role_arn, cache=cache
        )
        expected_response = self.get_expected_creds_from_response(
            cache[cache_key]
        )
        response = refresher.fetch_credentials()

        self.assertEqual(response, expected_response)
        client_creator.assert_not_called()

    def test_different_tokens_produce_different_cache_keys(self):
        client_creator = mock.Mock()
        fetcher_a = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, lambda: 'token-a', self.role_arn
        )
        fetcher_b = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, lambda: 'token-b', self.role_arn
        )
        self.assertNotEqual(fetcher_a._cache_key, fetcher_b._cache_key)

    def test_different_token_does_not_reuse_cached_credentials(self):
        cache = {}
        response_a = {
            'Credentials': {
                'AccessKeyId': 'akid-a',
                'SecretAccessKey': 'sk-a',
                'SessionToken': 'st-a',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        response_b = {
            'Credentials': {
                'AccessKeyId': 'akid-b',
                'SecretAccessKey': 'sk-b',
                'SessionToken': 'st-b',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator_a = self.create_client_creator(with_response=response_a)
        fetcher_a = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator_a, lambda: 'token-a', self.role_arn, cache=cache
        )
        fetcher_a.fetch_credentials()

        client_creator_b = self.create_client_creator(with_response=response_b)
        fetcher_b = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator_b, lambda: 'token-b', self.role_arn, cache=cache
        )
        creds_b = fetcher_b.fetch_credentials()

        client = client_creator_b.return_value
        client.assume_role_with_web_identity.assert_called_once()
        self.assertEqual(creds_b['access_key'], 'akid-b')

    def test_same_token_still_hits_cache(self):
        cache = {}
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        fetcher_1 = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, self.load_token, self.role_arn, cache=cache
        )
        fetcher_1.fetch_credentials()
        self.assertEqual(len(cache), 1)

        fetcher_2 = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, self.load_token, self.role_arn, cache=cache
        )
        self.assertEqual(fetcher_1._cache_key, fetcher_2._cache_key)
        self.assertIn(fetcher_2._cache_key, cache)

    def test_token_material_not_present_in_cache_key(self):
        client_creator = mock.Mock()
        fetcher = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, lambda: 'super-secret-token', self.role_arn
        )
        self.assertNotIn('super-secret-token', fetcher._cache_key)

    def test_assume_role_in_cache_but_expired(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        cache = {
            'development--myrole': {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': datetime.now(tzlocal()),
                }
            }
        }

        refresher = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, self.load_token, self.role_arn, cache=cache
        )
        expected = self.get_expected_creds_from_response(response)
        response = refresher.fetch_credentials()

        self.assertEqual(response, expected)

    def test_account_id_with_valid_arn(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
                'AccountId': '123456789012',
            },
            'AssumedRoleUser': {
                'AssumedRoleId': 'myroleid',
                'Arn': 'arn:aws:iam::123456789012:role/RoleA',
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        refresher = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, self.load_token, self.role_arn
        )
        expected_response = self.get_expected_creds_from_response(response)
        response = refresher.fetch_credentials()
        self.assertEqual(response, expected_response)
        self.assertEqual(response['account_id'], '123456789012')

    def test_account_id_with_invalid_arn(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
            'AssumedRoleUser': {
                'AssumedRoleId': 'myroleid',
                'Arn': 'invalid-arn',
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        refresher = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator,
            self.load_token,
            self.role_arn,
        )
        expected_response = self.get_expected_creds_from_response(response)
        response = refresher.fetch_credentials()
        self.assertEqual(response, expected_response)
        self.assertEqual(response['account_id'], None)

    @mock.patch('botocore.credentials.register_feature_ids')
    def test_feature_ids_registered_during_get_credentials(
        self, mock_register
    ):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time(),
            }
        }
        client_creator = self.create_client_creator(with_response=response)
        fetcher = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, self.load_token, self.role_arn
        )

        test_feature_ids = {'test_feature_1', 'test_feature_2'}
        fetcher.feature_ids = test_feature_ids

        fetcher.fetch_credentials()
        # Verify register_credential_feature_ids was called with test feature IDs
        mock_register.assert_called_once_with(test_feature_ids)


class TestAssumeRoleWithWebIdentityCredentialProvider(unittest.TestCase):
    def setUp(self):
        self.profile_name = 'some-profile'
        self.config = {
            'role_arn': 'arn:aws:iam::123:role/role-name',
            'web_identity_token_file': '/some/path/token.jwt',
        }

    def create_client_creator(self, with_response):
        # Create a mock sts client that returns a specific response
        # for assume_role.
        client = mock.Mock()
        if isinstance(with_response, list):
            client.assume_role_with_web_identity.side_effect = with_response
        else:
            client.assume_role_with_web_identity.return_value = with_response
        return mock.Mock(return_value=client)

    def some_future_time(self):
        timeobj = datetime.now(tzlocal())
        return timeobj + timedelta(hours=24)

    def _mock_loader_cls(self, token=''):
        mock_loader = mock.Mock(spec=FileWebIdentityTokenLoader)
        mock_loader.return_value = token
        mock_cls = mock.Mock()
        mock_cls.return_value = mock_loader
        return mock_cls

    def _load_config(self):
        return {
            'profiles': {
                self.profile_name: self.config,
            }
        }

    def test_assume_role_with_no_cache(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        mock_loader_cls = self._mock_loader_cls('totally.a.token')
        provider = credentials.AssumeRoleWithWebIdentityProvider(
            load_config=self._load_config,
            client_creator=client_creator,
            cache={},
            profile_name=self.profile_name,
            token_loader_cls=mock_loader_cls,
        )

        creds = provider.load()

        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        mock_loader_cls.assert_called_with('/some/path/token.jwt')

    def test_assume_role_retrieves_from_cache(self):
        date_in_future = datetime.utcnow() + timedelta(seconds=1000)
        utc_timestamp = date_in_future.isoformat() + 'Z'

        cache_key = '28500c163dbc087f6ccd4a6c1e103f76c300b953'
        cache = {
            cache_key: {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': utc_timestamp,
                }
            }
        }
        mock_loader_cls = self._mock_loader_cls('totally.a.token')
        client_creator = mock.Mock()
        provider = credentials.AssumeRoleWithWebIdentityProvider(
            load_config=self._load_config,
            client_creator=client_creator,
            cache=cache,
            profile_name=self.profile_name,
            token_loader_cls=mock_loader_cls,
        )

        creds = provider.load()

        self.assertEqual(creds.access_key, 'foo-cached')
        self.assertEqual(creds.secret_key, 'bar-cached')
        self.assertEqual(creds.token, 'baz-cached')
        client_creator.assert_not_called()

    def test_assume_role_in_cache_but_expired(self):
        expired_creds = datetime.now(tzlocal())
        valid_creds = expired_creds + timedelta(hours=1)
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': valid_creds,
            },
        }
        cache = {
            'development--myrole': {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': expired_creds,
                }
            }
        }
        client_creator = self.create_client_creator(with_response=response)
        mock_loader_cls = self._mock_loader_cls('totally.a.token')
        provider = credentials.AssumeRoleWithWebIdentityProvider(
            load_config=self._load_config,
            client_creator=client_creator,
            cache=cache,
            profile_name=self.profile_name,
            token_loader_cls=mock_loader_cls,
        )

        creds = provider.load()

        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        mock_loader_cls.assert_called_with('/some/path/token.jwt')

    def test_role_session_name_provided(self):
        self.config['role_session_name'] = 'myname'
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        mock_loader_cls = self._mock_loader_cls('totally.a.token')
        provider = credentials.AssumeRoleWithWebIdentityProvider(
            load_config=self._load_config,
            client_creator=client_creator,
            cache={},
            profile_name=self.profile_name,
            token_loader_cls=mock_loader_cls,
        )
        # The credentials won't actually be assumed until they're requested.
        provider.load().get_frozen_credentials()

        client = client_creator.return_value
        client.assume_role_with_web_identity.assert_called_with(
            RoleArn='arn:aws:iam::123:role/role-name',
            RoleSessionName='myname',
            WebIdentityToken='totally.a.token',
        )

    def test_refresh_failure_returns_cached_credentials(self):
        expiration_time = self.some_future_time()
        responses = [
            {
                'Credentials': {
                    'AccessKeyId': 'foo',
                    'SecretAccessKey': 'bar',
                    'SessionToken': 'baz',
                    'Expiration': expiration_time.isoformat(),
                },
            },
            Exception("sts down"),
        ]
        client_creator = self.create_client_creator(with_response=responses)
        mock_loader_cls = self._mock_loader_cls('totally.a.token')
        provider = credentials.AssumeRoleWithWebIdentityProvider(
            load_config=self._load_config,
            client_creator=client_creator,
            cache={},
            profile_name=self.profile_name,
            token_loader_cls=mock_loader_cls,
        )

        local_now = mock.Mock(return_value=datetime.now(tzlocal()))
        with mock.patch('botocore.credentials._local_now', local_now):
            creds = provider.load()
            first = creds.get_frozen_credentials()

            local_now.return_value = expiration_time
            second = creds.get_frozen_credentials()

        client = client_creator.return_value
        self.assertEqual(first.access_key, 'foo')
        self.assertEqual(second.access_key, 'foo')
        self.assertEqual(client.assume_role_with_web_identity.call_count, 2)
        mock_loader_cls.assert_called_with('/some/path/token.jwt')

    def test_role_arn_not_set(self):
        del self.config['role_arn']
        client_creator = self.create_client_creator(with_response={})
        provider = credentials.AssumeRoleWithWebIdentityProvider(
            load_config=self._load_config,
            client_creator=client_creator,
            cache={},
            profile_name=self.profile_name,
        )
        # If the role arn isn't set but the token path is raise an error
        with self.assertRaises(botocore.exceptions.InvalidConfigError):
            provider.load()


class TestEnvVar(BaseEnvVar):
    def test_envvars_are_found_no_token(self):
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.method, 'env')

    def test_envvars_found_with_security_token(self):
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SECURITY_TOKEN': 'baz',
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.method, 'env')

    def test_envvars_found_with_session_token(self):
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SESSION_TOKEN': 'baz',
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.method, 'env')

    def test_envvars_found_with_account_id(self):
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_ACCOUNT_ID': 'baz',
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.account_id, 'baz')
        self.assertEqual(creds.method, 'env')

    def test_envvars_not_found(self):
        provider = credentials.EnvProvider(environ={})
        creds = provider.load()
        self.assertIsNone(creds)

    def test_envvars_empty_string(self):
        environ = {
            'AWS_ACCESS_KEY_ID': '',
            'AWS_SECRET_ACCESS_KEY': '',
            'AWS_SECURITY_TOKEN': '',
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()
        self.assertIsNone(creds)

    def test_expiry_omitted_if_envvar_empty(self):
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SESSION_TOKEN': 'baz',
            'AWS_CREDENTIAL_EXPIRATION': '',
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()
        # Because we treat empty env vars the same as not being provided,
        # we should return static credentials and not a refreshable
        # credential.
        self.assertNotIsInstance(creds, credentials.RefreshableCredentials)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')

    def test_error_when_expiry_required_but_empty(self):
        expiry_time = datetime.now(tzlocal()) - timedelta(hours=1)
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_CREDENTIAL_EXPIRATION': expiry_time.isoformat(),
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()

        del environ['AWS_CREDENTIAL_EXPIRATION']

        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            creds.get_frozen_credentials()

    def test_can_override_env_var_mapping(self):
        # We can change the env var provider to
        # use our specified env var names.
        environ = {
            'FOO_ACCESS_KEY': 'foo',
            'FOO_SECRET_KEY': 'bar',
            'FOO_SESSION_TOKEN': 'baz',
        }
        mapping = {
            'access_key': 'FOO_ACCESS_KEY',
            'secret_key': 'FOO_SECRET_KEY',
            'token': 'FOO_SESSION_TOKEN',
        }
        provider = credentials.EnvProvider(environ, mapping)
        creds = provider.load()
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')

    def test_can_override_partial_env_var_mapping(self):
        # Only changing the access key mapping.
        # The other 2 use the default values of
        # AWS_SECRET_ACCESS_KEY and AWS_SESSION_TOKEN
        # use our specified env var names.
        environ = {
            'FOO_ACCESS_KEY': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SESSION_TOKEN': 'baz',
        }
        provider = credentials.EnvProvider(
            environ, {'access_key': 'FOO_ACCESS_KEY'}
        )
        creds = provider.load()
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')

    def test_can_override_expiry_env_var_mapping(self):
        expiry_time = datetime.now(tzlocal()) - timedelta(hours=1)
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SESSION_TOKEN': 'baz',
            'FOO_EXPIRY': expiry_time.isoformat(),
        }
        provider = credentials.EnvProvider(
            environ, {'expiry_time': 'FOO_EXPIRY'}
        )
        creds = provider.load()

        # Since the credentials are expired, we'll trigger a refresh whenever
        # we try to access them. Since the environment credentials are still
        # expired, this will raise an error.
        error_message = (
            "Credentials were refreshed, but the refreshed credentials are "
            "still expired."
        )
        with self.assertRaisesRegex(RuntimeError, error_message):
            creds.get_frozen_credentials()

    def test_can_override_account_id_env_var_mapping(self):
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SESSION_TOKEN': 'baz',
            'FOO_ACCOUNT_ID': 'bin',
        }
        provider = credentials.EnvProvider(
            environ, {'account_id': 'FOO_ACCOUNT_ID'}
        )
        creds = provider.load()
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.account_id, 'bin')

    def test_partial_creds_is_an_error(self):
        # If the user provides an access key, they must also
        # provide a secret key.  Not doing so will generate an
        # error.
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            # Missing the AWS_SECRET_ACCESS_KEY
        }
        provider = credentials.EnvProvider(environ)
        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            provider.load()

    def test_partial_creds_is_an_error_empty_string(self):
        # If the user provides an access key, they must also
        # provide a secret key.  Not doing so will generate an
        # error.
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': '',
        }
        provider = credentials.EnvProvider(environ)
        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            provider.load()

    def test_missing_access_key_id_raises_error(self):
        expiry_time = datetime.now(tzlocal()) - timedelta(hours=1)
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_CREDENTIAL_EXPIRATION': expiry_time.isoformat(),
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()

        del environ['AWS_ACCESS_KEY_ID']

        # Since the credentials are expired, we'll trigger a refresh
        # whenever we try to access them. At that refresh time, the relevant
        # environment variables are incomplete, so an error will be raised.
        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            creds.get_frozen_credentials()

    def test_credentials_refresh(self):
        # First initialize the credentials with an expired credential set.
        expiry_time = datetime.now(tzlocal()) - timedelta(hours=1)
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SESSION_TOKEN': 'baz',
            'AWS_CREDENTIAL_EXPIRATION': expiry_time.isoformat(),
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()
        self.assertIsInstance(creds, credentials.RefreshableCredentials)

        # Since the credentials are expired, we'll trigger a refresh whenever
        # we try to access them. But at this point the environment hasn't been
        # updated, so when it refreshes it will trigger an exception because
        # the new creds are still expired.
        error_message = (
            "Credentials were refreshed, but the refreshed credentials are "
            "still expired."
        )
        with self.assertRaisesRegex(RuntimeError, error_message):
            creds.get_frozen_credentials()

        # Now we update the environment with non-expired credentials,
        # so when we access the creds it will refresh and grab the new ones.
        expiry_time = datetime.now(tzlocal()) + timedelta(hours=1)
        environ.update(
            {
                'AWS_ACCESS_KEY_ID': 'bin',
                'AWS_SECRET_ACCESS_KEY': 'bam',
                'AWS_SESSION_TOKEN': 'biz',
                'AWS_CREDENTIAL_EXPIRATION': expiry_time.isoformat(),
            }
        )

        frozen = creds.get_frozen_credentials()
        self.assertEqual(frozen.access_key, 'bin')
        self.assertEqual(frozen.secret_key, 'bam')
        self.assertEqual(frozen.token, 'biz')

    def test_credentials_only_refresh_when_needed(self):
        expiry_time = datetime.now(tzlocal()) + timedelta(hours=2)
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SESSION_TOKEN': 'baz',
            'AWS_CREDENTIAL_EXPIRATION': expiry_time.isoformat(),
        }
        provider = credentials.EnvProvider(environ)

        # Perform the initial credential load
        creds = provider.load()

        # Now that the initial load has been performed, we go ahead and
        # change the environment. If the credentials were expired,
        # they would immediately refresh upon access and we'd get the new
        # ones. Since they've got plenty of time, they shouldn't refresh.
        expiry_time = datetime.now(tzlocal()) + timedelta(hours=3)
        environ.update(
            {
                'AWS_ACCESS_KEY_ID': 'bin',
                'AWS_SECRET_ACCESS_KEY': 'bam',
                'AWS_SESSION_TOKEN': 'biz',
                'AWS_CREDENTIAL_EXPIRATION': expiry_time.isoformat(),
            }
        )

        frozen = creds.get_frozen_credentials()
        self.assertEqual(frozen.access_key, 'foo')
        self.assertEqual(frozen.secret_key, 'bar')
        self.assertEqual(frozen.token, 'baz')

    def test_credentials_not_refreshable_if_no_expiry_present(self):
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SESSION_TOKEN': 'baz',
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()
        self.assertNotIsInstance(creds, credentials.RefreshableCredentials)
        self.assertIsInstance(creds, credentials.Credentials)

    def test_credentials_do_not_become_refreshable(self):
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_SESSION_TOKEN': 'baz',
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()
        frozen = creds.get_frozen_credentials()
        self.assertEqual(frozen.access_key, 'foo')
        self.assertEqual(frozen.secret_key, 'bar')
        self.assertEqual(frozen.token, 'baz')

        expiry_time = datetime.now(tzlocal()) - timedelta(hours=1)
        environ.update(
            {
                'AWS_ACCESS_KEY_ID': 'bin',
                'AWS_SECRET_ACCESS_KEY': 'bam',
                'AWS_SESSION_TOKEN': 'biz',
                'AWS_CREDENTIAL_EXPIRATION': expiry_time.isoformat(),
            }
        )

        frozen = creds.get_frozen_credentials()
        self.assertEqual(frozen.access_key, 'foo')
        self.assertEqual(frozen.secret_key, 'bar')
        self.assertEqual(frozen.token, 'baz')
        self.assertNotIsInstance(creds, credentials.RefreshableCredentials)

    def test_credentials_throw_error_if_expiry_goes_away(self):
        expiry_time = datetime.now(tzlocal()) - timedelta(hours=1)
        environ = {
            'AWS_ACCESS_KEY_ID': 'foo',
            'AWS_SECRET_ACCESS_KEY': 'bar',
            'AWS_CREDENTIAL_EXPIRATION': expiry_time.isoformat(),
        }
        provider = credentials.EnvProvider(environ)
        creds = provider.load()

        del environ['AWS_CREDENTIAL_EXPIRATION']

        with self.assertRaises(credentials.PartialCredentialsError):
            creds.get_frozen_credentials()


class TestSharedCredentialsProvider(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.ini_parser = mock.Mock()

    def test_credential_file_exists_default_profile(self):
        self.ini_parser.return_value = {
            'default': {
                'aws_access_key_id': 'foo',
                'aws_secret_access_key': 'bar',
            }
        }
        provider = credentials.SharedCredentialProvider(
            creds_filename='~/.aws/creds',
            profile_name='default',
            ini_parser=self.ini_parser,
        )
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertIsNone(creds.token)
        self.assertEqual(creds.method, 'shared-credentials-file')

    def test_partial_creds_raise_error(self):
        self.ini_parser.return_value = {
            'default': {
                'aws_access_key_id': 'foo',
                # Missing 'aws_secret_access_key'.
            }
        }
        provider = credentials.SharedCredentialProvider(
            creds_filename='~/.aws/creds',
            profile_name='default',
            ini_parser=self.ini_parser,
        )
        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            provider.load()

    def test_credentials_file_exists_with_session_token(self):
        self.ini_parser.return_value = {
            'default': {
                'aws_access_key_id': 'foo',
                'aws_secret_access_key': 'bar',
                'aws_session_token': 'baz',
            }
        }
        provider = credentials.SharedCredentialProvider(
            creds_filename='~/.aws/creds',
            profile_name='default',
            ini_parser=self.ini_parser,
        )
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.method, 'shared-credentials-file')

    def test_credentials_file_with_multiple_profiles(self):
        self.ini_parser.return_value = {
            # Here the user has a 'default' and a 'dev' profile.
            'default': {
                'aws_access_key_id': 'a',
                'aws_secret_access_key': 'b',
                'aws_session_token': 'c',
            },
            'dev': {
                'aws_access_key_id': 'd',
                'aws_secret_access_key': 'e',
                'aws_session_token': 'f',
            },
        }
        # And we specify a profile_name of 'dev'.
        provider = credentials.SharedCredentialProvider(
            creds_filename='~/.aws/creds',
            profile_name='dev',
            ini_parser=self.ini_parser,
        )
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'd')
        self.assertEqual(creds.secret_key, 'e')
        self.assertEqual(creds.token, 'f')
        self.assertEqual(creds.method, 'shared-credentials-file')

    def test_credentials_file_does_not_exist_returns_none(self):
        # It's ok if the credentials file does not exist, we should
        # just catch the appropriate errors and return None.
        self.ini_parser.side_effect = botocore.exceptions.ConfigNotFound(
            path='foo'
        )
        provider = credentials.SharedCredentialProvider(
            creds_filename='~/.aws/creds',
            profile_name='dev',
            ini_parser=self.ini_parser,
        )
        creds = provider.load()
        self.assertIsNone(creds)

    def test_credentials_file_exists_with_account_id(self):
        self.ini_parser.return_value = {
            'default': {
                'aws_access_key_id': 'foo',
                'aws_secret_access_key': 'bar',
                'aws_session_token': 'baz',
                'aws_account_id': 'bin',
            }
        }
        provider = credentials.SharedCredentialProvider(
            creds_filename='~/.aws/creds',
            profile_name='default',
            ini_parser=self.ini_parser,
        )
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.method, 'shared-credentials-file')
        self.assertEqual(creds.account_id, 'bin')


class TestConfigFileProvider(BaseEnvVar):
    def setUp(self):
        super().setUp()
        profile_config = {
            'aws_access_key_id': 'a',
            'aws_secret_access_key': 'b',
            'aws_session_token': 'c',
            # Non creds related configs can be in a session's # config.
            'region': 'us-west-2',
            'output': 'json',
        }
        parsed = {'profiles': {'default': profile_config}}
        parser = mock.Mock()
        parser.return_value = parsed
        self.parser = parser

    def test_config_file_exists(self):
        provider = credentials.ConfigProvider(
            'cli.cfg', 'default', self.parser
        )
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertEqual(creds.token, 'c')
        self.assertEqual(creds.method, 'config-file')

    def test_config_file_missing_profile_config(self):
        # Referring to a profile that's not in the config file
        # will result in session.config returning an empty dict.
        profile_name = 'NOT-default'
        provider = credentials.ConfigProvider(
            'cli.cfg', profile_name, self.parser
        )
        creds = provider.load()
        self.assertIsNone(creds)

    def test_config_file_errors_ignored(self):
        # We should move on to the next provider if the config file
        # can't be found.
        self.parser.side_effect = botocore.exceptions.ConfigNotFound(
            path='cli.cfg'
        )
        provider = credentials.ConfigProvider(
            'cli.cfg', 'default', self.parser
        )
        creds = provider.load()
        self.assertIsNone(creds)

    def test_partial_creds_is_error(self):
        profile_config = {
            'aws_access_key_id': 'a',
            # Missing aws_secret_access_key
        }
        parsed = {'profiles': {'default': profile_config}}
        parser = mock.Mock()
        parser.return_value = parsed
        provider = credentials.ConfigProvider('cli.cfg', 'default', parser)
        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            provider.load()

    def test_config_file_with_account_id(self):
        profile_config = {
            'aws_access_key_id': 'foo',
            'aws_secret_access_key': 'bar',
            'aws_session_token': 'baz',
            'aws_account_id': 'bin',
        }
        parsed = {'profiles': {'default': profile_config}}
        parser = mock.Mock()
        parser.return_value = parsed
        provider = credentials.ConfigProvider('cli.cfg', 'default', parser)
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.method, 'config-file')
        self.assertEqual(creds.account_id, 'bin')


class TestBotoProvider(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.ini_parser = mock.Mock()

    def test_boto_config_file_exists_in_home_dir(self):
        environ = {}
        self.ini_parser.return_value = {
            'Credentials': {
                # boto's config file does not support a session token
                # so we only test for access_key/secret_key.
                'aws_access_key_id': 'a',
                'aws_secret_access_key': 'b',
            }
        }
        provider = credentials.BotoProvider(
            environ=environ, ini_parser=self.ini_parser
        )
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertIsNone(creds.token)
        self.assertEqual(creds.method, 'boto-config')

    def test_env_var_set_for_boto_location(self):
        environ = {'BOTO_CONFIG': 'alternate-config.cfg'}
        self.ini_parser.return_value = {
            'Credentials': {
                # boto's config file does not support a session token
                # so we only test for access_key/secret_key.
                'aws_access_key_id': 'a',
                'aws_secret_access_key': 'b',
            }
        }
        provider = credentials.BotoProvider(
            environ=environ, ini_parser=self.ini_parser
        )
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertIsNone(creds.token)
        self.assertEqual(creds.method, 'boto-config')

        # Assert that the parser was called with the filename specified
        # in the env var.
        self.ini_parser.assert_called_with('alternate-config.cfg')

    def test_no_boto_config_file_exists(self):
        self.ini_parser.side_effect = botocore.exceptions.ConfigNotFound(
            path='foo'
        )
        provider = credentials.BotoProvider(
            environ={}, ini_parser=self.ini_parser
        )
        creds = provider.load()
        self.assertIsNone(creds)

    def test_partial_creds_is_error(self):
        ini_parser = mock.Mock()
        ini_parser.return_value = {
            'Credentials': {
                'aws_access_key_id': 'a',
                # Missing aws_secret_access_key.
            }
        }
        provider = credentials.BotoProvider(environ={}, ini_parser=ini_parser)
        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            provider.load()


class TestOriginalEC2Provider(BaseEnvVar):
    def test_load_ec2_credentials_file_not_exist(self):
        provider = credentials.OriginalEC2Provider(environ={})
        creds = provider.load()
        self.assertIsNone(creds)

    def test_load_ec2_credentials_file_exists(self):
        environ = {
            'AWS_CREDENTIAL_FILE': 'foo.cfg',
        }
        parser = mock.Mock()
        parser.return_value = {
            'AWSAccessKeyId': 'a',
            'AWSSecretKey': 'b',
        }
        provider = credentials.OriginalEC2Provider(
            environ=environ, parser=parser
        )
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertIsNone(creds.token)
        self.assertEqual(creds.method, 'ec2-credentials-file')


class TestInstanceMetadataProvider(BaseEnvVar):
    def test_load_from_instance_metadata(self):
        timeobj = datetime.now(tzlocal())
        timestamp = (timeobj + timedelta(hours=24)).isoformat()
        fetcher = mock.Mock()
        fetcher.retrieve_iam_role_credentials.return_value = {
            'access_key': 'a',
            'secret_key': 'b',
            'token': 'c',
            'expiry_time': timestamp,
            'role_name': 'myrole',
        }
        provider = credentials.InstanceMetadataProvider(
            iam_role_fetcher=fetcher
        )
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertEqual(creds.token, 'c')
        self.assertEqual(creds.method, 'iam-role')

    def test_no_role_creds_exist(self):
        fetcher = mock.Mock()
        fetcher.retrieve_iam_role_credentials.return_value = {}
        provider = credentials.InstanceMetadataProvider(
            iam_role_fetcher=fetcher
        )
        creds = provider.load()
        self.assertIsNone(creds)
        fetcher.retrieve_iam_role_credentials.assert_called_with()

    def test_refresh_failure_returns_cached_credentials(self):
        fetcher = mock.Mock()
        fetcher.retrieve_iam_role_credentials.side_effect = [
            {
                'access_key': 'a',
                'secret_key': 'b',
                'token': 'c',
                'expiry_time': '2000-01-01T00:00:00Z',
                'role_name': 'myrole',
            },
            Exception("imds down"),
        ]
        provider = credentials.InstanceMetadataProvider(
            iam_role_fetcher=fetcher
        )

        creds = provider.load()

        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(fetcher.retrieve_iam_role_credentials.call_count, 2)


class CredentialResolverTest(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.provider1 = mock.Mock()
        self.provider1.METHOD = 'provider1'
        self.provider1.CANONICAL_NAME = 'CustomProvider1'
        self.provider2 = mock.Mock()
        self.provider2.METHOD = 'provider2'
        self.provider2.CANONICAL_NAME = 'CustomProvider2'
        self.fake_creds = credentials.Credentials('a', 'b', 'c')

    def test_load_credentials_single_provider(self):
        self.provider1.load.return_value = self.fake_creds
        resolver = credentials.CredentialResolver(providers=[self.provider1])
        creds = resolver.load_credentials()
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertEqual(creds.token, 'c')

    def test_get_provider_by_name(self):
        resolver = credentials.CredentialResolver(providers=[self.provider1])
        result = resolver.get_provider('provider1')
        self.assertIs(result, self.provider1)

    def test_get_unknown_provider_raises_error(self):
        resolver = credentials.CredentialResolver(providers=[self.provider1])
        with self.assertRaises(botocore.exceptions.UnknownCredentialError):
            resolver.get_provider('unknown-foo')

    def test_first_credential_non_none_wins(self):
        self.provider1.load.return_value = None
        self.provider2.load.return_value = self.fake_creds
        resolver = credentials.CredentialResolver(
            providers=[self.provider1, self.provider2]
        )
        creds = resolver.load_credentials()
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertEqual(creds.token, 'c')
        self.provider1.load.assert_called_with()
        self.provider2.load.assert_called_with()

    def test_no_creds_loaded(self):
        self.provider1.load.return_value = None
        self.provider2.load.return_value = None
        resolver = credentials.CredentialResolver(
            providers=[self.provider1, self.provider2]
        )
        creds = resolver.load_credentials()
        self.assertIsNone(creds)

    def test_inject_additional_providers_after_existing(self):
        self.provider1.load.return_value = None
        self.provider2.load.return_value = self.fake_creds
        resolver = credentials.CredentialResolver(
            providers=[self.provider1, self.provider2]
        )
        # Now, if we were to call resolver.load() now, provider2 would
        # win because it's returning a non None response.
        # However we can inject a new provider before provider2 to
        # override this process.
        # Providers can be added by the METHOD name of each provider.
        new_provider = mock.Mock()
        new_provider.METHOD = 'new_provider'
        new_provider.load.return_value = credentials.Credentials('d', 'e', 'f')

        resolver.insert_after('provider1', new_provider)

        creds = resolver.load_credentials()
        self.assertIsNotNone(creds)

        self.assertEqual(creds.access_key, 'd')
        self.assertEqual(creds.secret_key, 'e')
        self.assertEqual(creds.token, 'f')
        # Provider 1 should have been called, but provider2 should
        # *not* have been called because new_provider already returned
        # a non-None response.
        self.provider1.load.assert_called_with()
        self.assertTrue(not self.provider2.called)

    def test_inject_provider_before_existing(self):
        new_provider = mock.Mock()
        new_provider.METHOD = 'override'
        new_provider.load.return_value = credentials.Credentials('x', 'y', 'z')

        resolver = credentials.CredentialResolver(
            providers=[self.provider1, self.provider2]
        )
        resolver.insert_before(self.provider1.METHOD, new_provider)
        creds = resolver.load_credentials()
        self.assertEqual(creds.access_key, 'x')
        self.assertEqual(creds.secret_key, 'y')
        self.assertEqual(creds.token, 'z')

    def test_can_remove_providers(self):
        self.provider1.load.return_value = credentials.Credentials(
            'a', 'b', 'c'
        )
        self.provider2.load.return_value = credentials.Credentials(
            'd', 'e', 'f'
        )
        resolver = credentials.CredentialResolver(
            providers=[self.provider1, self.provider2]
        )
        resolver.remove('provider1')
        creds = resolver.load_credentials()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'd')
        self.assertEqual(creds.secret_key, 'e')
        self.assertEqual(creds.token, 'f')
        self.assertTrue(not self.provider1.load.called)
        self.provider2.load.assert_called_with()

    def test_provider_unknown(self):
        resolver = credentials.CredentialResolver(
            providers=[self.provider1, self.provider2]
        )
        # No error is raised if you try to remove an unknown provider.
        resolver.remove('providerFOO')
        # But an error IS raised if you try to insert after an unknown
        # provider.
        with self.assertRaises(botocore.exceptions.UnknownCredentialError):
            resolver.insert_after('providerFoo', None)


class TestCreateCredentialResolver(BaseEnvVar):
    def setUp(self):
        super().setUp()

        self.session = mock.Mock(spec=botocore.session.Session)
        self.session.get_component = self.fake_get_component

        self.fake_instance_variables = {
            'credentials_file': 'a',
            'legacy_config_file': 'b',
            'config_file': 'c',
            'metadata_service_timeout': 1,
            'metadata_service_num_attempts': 1,
            'imds_use_ipv6': 'false',
        }
        self.config_loader = ConfigValueStore()
        for name, value in self.fake_instance_variables.items():
            self.config_loader.set_config_variable(name, value)

        self.session.get_config_variable = (
            self.config_loader.get_config_variable
        )
        self.session.set_config_variable = self.fake_set_config_variable
        self.session.instance_variables = self.fake_instance_variable_lookup

    def fake_get_component(self, key):
        if key == 'config_provider':
            return self.config_loader
        return None

    def fake_instance_variable_lookup(self):
        return self.fake_instance_variables

    def fake_set_config_variable(self, logical_name, value):
        self.fake_instance_variables[logical_name] = value

    def test_create_credential_resolver(self):
        resolver = credentials.create_credential_resolver(self.session)
        self.assertIsInstance(resolver, credentials.CredentialResolver)

    def test_explicit_profile_ignores_env_provider(self):
        self.session.set_config_variable('profile', 'dev')
        resolver = credentials.create_credential_resolver(self.session)

        self.assertTrue(
            all(not isinstance(p, EnvProvider) for p in resolver.providers)
        )

    def test_no_profile_checks_env_provider(self):
        # If no profile is provided,
        self.config_loader.set_config_variable('profile', None)
        resolver = credentials.create_credential_resolver(self.session)
        # Then an EnvProvider should be part of our credential lookup chain.
        self.assertTrue(
            any(isinstance(p, EnvProvider) for p in resolver.providers)
        )

    def test_default_cache(self):
        resolver = credentials.create_credential_resolver(self.session)
        cache = resolver.get_provider('assume-role').cache
        self.assertIsInstance(cache, dict)
        self.assertEqual(cache, {})

    def test_custom_cache(self):
        custom_cache = credentials.JSONFileCache()
        resolver = credentials.create_credential_resolver(
            self.session, custom_cache
        )
        cache = resolver.get_provider('assume-role').cache
        self.assertIs(cache, custom_cache)


class TestCanonicalNameSourceProvider(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.custom_provider1 = mock.Mock(spec=CredentialProvider)
        self.custom_provider1.METHOD = 'provider1'
        self.custom_provider1.CANONICAL_NAME = 'CustomProvider1'
        self.custom_provider2 = mock.Mock(spec=CredentialProvider)
        self.custom_provider2.METHOD = 'provider2'
        self.custom_provider2.CANONICAL_NAME = 'CustomProvider2'
        self.fake_creds = credentials.Credentials('a', 'b', 'c')

    def test_load_source_credentials(self):
        provider = credentials.CanonicalNameCredentialSourcer(
            providers=[self.custom_provider1, self.custom_provider2]
        )
        self.custom_provider1.load.return_value = self.fake_creds
        result = provider.source_credentials('CustomProvider1')
        self.assertIs(result, self.fake_creds)

    def test_load_source_credentials_case_insensitive(self):
        provider = credentials.CanonicalNameCredentialSourcer(
            providers=[self.custom_provider1, self.custom_provider2]
        )
        self.custom_provider1.load.return_value = self.fake_creds
        result = provider.source_credentials('cUsToMpRoViDeR1')
        self.assertIs(result, self.fake_creds)

    def test_load_unknown_canonical_name_raises_error(self):
        provider = credentials.CanonicalNameCredentialSourcer(
            providers=[self.custom_provider1]
        )
        with self.assertRaises(botocore.exceptions.UnknownCredentialError):
            provider.source_credentials('CustomUnknown')

    def _assert_assume_role_creds_returned_with_shared_file(self, provider):
        assume_role_provider = mock.Mock(spec=AssumeRoleProvider)
        assume_role_provider.METHOD = 'assume-role'
        assume_role_provider.CANONICAL_NAME = None

        source = credentials.CanonicalNameCredentialSourcer(
            providers=[assume_role_provider, provider]
        )

        # If the assume role provider returns credentials, those should be
        # what is returned.
        assume_role_provider.load.return_value = self.fake_creds
        provider.load.return_value = credentials.Credentials('d', 'e', 'f')

        creds = source.source_credentials(provider.CANONICAL_NAME)
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertEqual(creds.token, 'c')
        self.assertFalse(provider.load.called)

    def _assert_returns_creds_if_assume_role_not_used(self, provider):
        assume_role_provider = mock.Mock(spec=AssumeRoleProvider)
        assume_role_provider.METHOD = 'assume-role'
        assume_role_provider.CANONICAL_NAME = None

        source = credentials.CanonicalNameCredentialSourcer(
            providers=[assume_role_provider, provider]
        )

        # If the assume role provider returns nothing, then whatever is in
        # the config provider should be returned.
        assume_role_provider.load.return_value = None
        provider.load.return_value = credentials.Credentials('d', 'e', 'f')

        creds = source.source_credentials(provider.CANONICAL_NAME)
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'd')
        self.assertEqual(creds.secret_key, 'e')
        self.assertEqual(creds.token, 'f')
        self.assertTrue(assume_role_provider.load.called)

    def test_assume_role_creds_returned_with_config_file(self):
        provider = mock.Mock(spec=ConfigProvider)
        provider.METHOD = 'config-file'
        provider.CANONICAL_NAME = 'SharedConfig'
        self._assert_assume_role_creds_returned_with_shared_file(provider)

    def test_config_file_returns_creds_if_assume_role_not_used(self):
        provider = mock.Mock(spec=ConfigProvider)
        provider.METHOD = 'config-file'
        provider.CANONICAL_NAME = 'SharedConfig'
        self._assert_returns_creds_if_assume_role_not_used(provider)

    def test_assume_role_creds_returned_with_cred_file(self):
        provider = mock.Mock(spec=SharedCredentialProvider)
        provider.METHOD = 'credentials-file'
        provider.CANONICAL_NAME = 'SharedCredentials'
        self._assert_assume_role_creds_returned_with_shared_file(provider)

    def test_creds_file_returns_creds_if_assume_role_not_used(self):
        provider = mock.Mock(spec=SharedCredentialProvider)
        provider.METHOD = 'credentials-file'
        provider.CANONICAL_NAME = 'SharedCredentials'
        self._assert_returns_creds_if_assume_role_not_used(provider)

    def test_get_canonical_assume_role_without_shared_files(self):
        assume_role_provider = mock.Mock(spec=AssumeRoleProvider)
        assume_role_provider.METHOD = 'assume-role'
        assume_role_provider.CANONICAL_NAME = None
        assume_role_provider.load.return_value = self.fake_creds

        provider = credentials.CanonicalNameCredentialSourcer(
            providers=[assume_role_provider]
        )

        creds = provider.source_credentials('SharedConfig')
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertEqual(creds.token, 'c')

        creds = provider.source_credentials('SharedCredentials')
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'a')
        self.assertEqual(creds.secret_key, 'b')
        self.assertEqual(creds.token, 'c')

    def test_get_canonical_shared_files_without_assume_role(self):
        provider = credentials.CanonicalNameCredentialSourcer(
            providers=[self.custom_provider1]
        )
        with self.assertRaises(botocore.exceptions.UnknownCredentialError):
            provider.source_credentials('SharedConfig')
        with self.assertRaises(botocore.exceptions.UnknownCredentialError):
            provider.source_credentials('SharedCredentials')


class TestAssumeRoleCredentialProvider(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.fake_config = {
            'profiles': {
                'development': {
                    'role_arn': 'myrole',
                    'source_profile': 'longterm',
                },
                'longterm': {
                    'aws_access_key_id': 'akid',
                    'aws_secret_access_key': 'skid',
                },
                'non-static': {
                    'role_arn': 'myrole',
                    'credential_source': 'Environment',
                },
                'chained': {
                    'role_arn': 'chained-role',
                    'source_profile': 'development',
                },
            }
        }

    def create_config_loader(self, with_config=None):
        if with_config is None:
            with_config = self.fake_config
        load_config = mock.Mock()
        load_config.return_value = with_config
        return load_config

    def create_client_creator(self, with_response):
        # Create a mock sts client that returns a specific response
        # for assume_role.
        client = mock.Mock()
        if isinstance(with_response, list):
            client.assume_role.side_effect = with_response
        else:
            client.assume_role.return_value = with_response
        return mock.Mock(return_value=client)

    def some_future_time(self):
        timeobj = datetime.now(tzlocal())
        return timeobj + timedelta(hours=24)

    def test_assume_role_with_no_cache(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
        )

        creds = provider.load()

        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')

    def test_assume_role_with_datetime(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                # Note the lack of isoformat(), we're using
                # a datetime.datetime type.  This will ensure
                # we test both parsing as well as serializing
                # from a given datetime because the credentials
                # are immediately expired.
                'Expiration': datetime.now(tzlocal()) + timedelta(hours=20),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
        )

        creds = provider.load()

        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')

    def test_assume_role_refresher_serializes_datetime(self):
        client = mock.Mock()
        time_zone = tzutc()
        expiration = datetime(
            year=2016, month=11, day=6, hour=1, minute=30, tzinfo=time_zone
        )
        client.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': expiration,
            }
        }
        refresh = create_assume_role_refresher(client, {})
        expiry_time = refresh()['expiry_time']
        self.assertEqual(expiry_time, '2016-11-06T01:30:00UTC')

    def test_assume_role_retrieves_from_cache(self):
        date_in_future = datetime.utcnow() + timedelta(seconds=1000)
        utc_timestamp = date_in_future.isoformat() + 'Z'
        self.fake_config['profiles']['development']['role_arn'] = 'myrole'

        cache_key = '793d6e2f27667ab2da104824407e486bfec24a47'
        cache = {
            cache_key: {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': utc_timestamp,
                }
            }
        }
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(),
            cache=cache,
            profile_name='development',
        )

        creds = provider.load()

        self.assertEqual(creds.access_key, 'foo-cached')
        self.assertEqual(creds.secret_key, 'bar-cached')
        self.assertEqual(creds.token, 'baz-cached')

    def test_chain_prefers_cache(self):
        date_in_future = datetime.utcnow() + timedelta(seconds=1000)
        utc_timestamp = date_in_future.isoformat() + 'Z'

        # The profile we will be using has a cache entry, but the profile it
        # is sourcing from does not. This should result in the cached
        # credentials being used, and the source profile not being called.
        cache_key = '3d440bf424caf7a5ee664fbf89139a84409f95c2'
        cache = {
            cache_key: {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': utc_timestamp,
                }
            }
        }

        client_creator = self.create_client_creator(
            [Exception("Attempted to call assume role when not needed.")]
        )

        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache=cache,
            profile_name='chained',
        )

        creds = provider.load()

        self.assertEqual(creds.access_key, 'foo-cached')
        self.assertEqual(creds.secret_key, 'bar-cached')
        self.assertEqual(creds.token, 'baz-cached')

    def test_cache_key_is_windows_safe(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        cache = {}
        self.fake_config['profiles']['development']['role_arn'] = (
            'arn:aws:iam::foo-role'
        )

        client_creator = self.create_client_creator(with_response=response)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache=cache,
            profile_name='development',
        )

        provider.load().get_frozen_credentials()
        # On windows, you cannot use a a ':' in the filename, so
        # we need to make sure it doesn't come up in the cache key.
        cache_key = '3f8e35c8dca6211d496e830a2de723b2387921e3'
        self.assertIn(cache_key, cache)
        self.assertEqual(cache[cache_key], response)

    def test_cache_key_with_role_session_name(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        cache = {}
        self.fake_config['profiles']['development']['role_arn'] = (
            'arn:aws:iam::foo-role'
        )
        self.fake_config['profiles']['development']['role_session_name'] = (
            'foo_role_session_name'
        )

        client_creator = self.create_client_creator(with_response=response)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache=cache,
            profile_name='development',
        )

        # The credentials won't actually be assumed until they're requested.
        provider.load().get_frozen_credentials()

        cache_key = '5e75ce21b6a64ab183b29c4a159b6f0248121d51'
        self.assertIn(cache_key, cache)
        self.assertEqual(cache[cache_key], response)

    def test_assume_role_in_cache_but_expired(self):
        expired_creds = datetime.now(tzlocal())
        valid_creds = expired_creds + timedelta(hours=1)
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': valid_creds,
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        cache = {
            'development--myrole': {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': expired_creds,
                }
            }
        }
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache=cache,
            profile_name='development',
        )

        creds = provider.load()

        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')

    def test_role_session_name_provided(self):
        dev_profile = self.fake_config['profiles']['development']
        dev_profile['role_session_name'] = 'myname'
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
        )

        # The credentials won't actually be assumed until they're requested.
        provider.load().get_frozen_credentials()

        client = client_creator.return_value
        client.assume_role.assert_called_with(
            RoleArn='myrole', RoleSessionName='myname'
        )

    def test_external_id_provided(self):
        self.fake_config['profiles']['development']['external_id'] = 'myid'
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
        )

        # The credentials won't actually be assumed until they're requested.
        provider.load().get_frozen_credentials()

        client = client_creator.return_value
        client.assume_role.assert_called_with(
            RoleArn='myrole', ExternalId='myid', RoleSessionName=mock.ANY
        )

    def test_assume_role_with_duration(self):
        self.fake_config['profiles']['development']['duration_seconds'] = 7200
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
        )

        # The credentials won't actually be assumed until they're requested.
        provider.load().get_frozen_credentials()

        client = client_creator.return_value
        client.assume_role.assert_called_with(
            RoleArn='myrole', RoleSessionName=mock.ANY, DurationSeconds=7200
        )

    def test_assume_role_with_bad_duration(self):
        self.fake_config['profiles']['development']['duration_seconds'] = (
            'garbage value'
        )
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
        )

        # The credentials won't actually be assumed until they're requested.
        provider.load().get_frozen_credentials()

        client = client_creator.return_value
        client.assume_role.assert_called_with(
            RoleArn='myrole', RoleSessionName=mock.ANY
        )

    def test_assume_role_with_mfa(self):
        self.fake_config['profiles']['development']['mfa_serial'] = 'mfa'
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        prompter = mock.Mock(return_value='token-code')
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
            prompter=prompter,
        )

        # The credentials won't actually be assumed until they're requested.
        provider.load().get_frozen_credentials()

        client = client_creator.return_value
        # In addition to the normal assume role args, we should also
        # inject the serial number from the config as well as the
        # token code that comes from prompting the user (the prompter
        # object).
        client.assume_role.assert_called_with(
            RoleArn='myrole',
            RoleSessionName=mock.ANY,
            SerialNumber='mfa',
            TokenCode='token-code',
        )

    def test_assume_role_populates_session_name_on_refresh(self):
        expiration_time = self.some_future_time()
        next_expiration_time = expiration_time + timedelta(hours=4)
        responses = [
            {
                'Credentials': {
                    'AccessKeyId': 'foo',
                    'SecretAccessKey': 'bar',
                    'SessionToken': 'baz',
                    # We're creating an expiry time in the past so as
                    # soon as we try to access the credentials, the
                    # refresh behavior will be triggered.
                    'Expiration': expiration_time.isoformat(),
                },
            },
            {
                'Credentials': {
                    'AccessKeyId': 'foo',
                    'SecretAccessKey': 'bar',
                    'SessionToken': 'baz',
                    'Expiration': next_expiration_time.isoformat(),
                }
            },
        ]
        client_creator = self.create_client_creator(with_response=responses)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
            prompter=mock.Mock(return_value='token-code'),
        )

        local_now = mock.Mock(return_value=datetime.now(tzlocal()))
        with mock.patch('botocore.credentials._local_now', local_now):
            # This will trigger the first assume_role() call.  It returns
            # credentials that are expired and will trigger a refresh.
            creds = provider.load()
            creds.get_frozen_credentials()

            # This will trigger the second assume_role() call because
            # a refresh is needed.
            local_now.return_value = expiration_time
            creds.get_frozen_credentials()

        client = client_creator.return_value
        assume_role_calls = client.assume_role.call_args_list
        self.assertEqual(len(assume_role_calls), 2, assume_role_calls)
        # The args should be identical.  That is, the second
        # assume_role call should have the exact same args as the
        # initial assume_role call.
        self.assertEqual(assume_role_calls[0], assume_role_calls[1])

    def test_assume_role_refresh_failure_returns_cached_credentials(self):
        expiration_time = self.some_future_time()
        responses = [
            {
                'Credentials': {
                    'AccessKeyId': 'foo',
                    'SecretAccessKey': 'bar',
                    'SessionToken': 'baz',
                    'Expiration': expiration_time.isoformat(),
                },
            },
            Exception("sts down"),
        ]
        client_creator = self.create_client_creator(with_response=responses)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
        )

        local_now = mock.Mock(return_value=datetime.now(tzlocal()))
        with mock.patch('botocore.credentials._local_now', local_now):
            creds = provider.load()
            first = creds.get_frozen_credentials()

            local_now.return_value = expiration_time
            second = creds.get_frozen_credentials()

        client = client_creator.return_value
        self.assertEqual(first.access_key, 'foo')
        self.assertEqual(second.access_key, 'foo')
        self.assertEqual(client.assume_role.call_count, 2)

    def test_assume_role_mfa_cannot_refresh_credentials(self):
        # Note: we should look into supporting optional behavior
        # in the future that allows for reprompting for credentials.
        # But for now, if we get temp creds with MFA then when those
        # creds expire, we can't refresh the credentials.
        self.fake_config['profiles']['development']['mfa_serial'] = 'mfa'
        expiration_time = self.some_future_time()
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                # We're creating an expiry time in the past so as
                # soon as we try to access the credentials, the
                # refresh behavior will be triggered.
                'Expiration': expiration_time.isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
            prompter=mock.Mock(return_value='token-code'),
        )

        local_now = mock.Mock(return_value=datetime.now(tzlocal()))
        with mock.patch('botocore.credentials._local_now', local_now):
            # Loads the credentials, resulting in the first assume role call.
            creds = provider.load()
            creds.get_frozen_credentials()

            local_now.return_value = expiration_time
            with self.assertRaises(credentials.RefreshWithMFAUnsupportedError):
                # access_key is a property that will refresh credentials
                # if they're expired.  Because we set the expiry time to
                # something in the past, this will trigger the refresh
                # behavior, with with MFA will currently raise an exception.
                creds.access_key

    def test_no_config_is_noop(self):
        self.fake_config['profiles']['development'] = {
            'aws_access_key_id': 'foo',
            'aws_secret_access_key': 'bar',
        }
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(),
            cache={},
            profile_name='development',
        )

        # Because a role_arn was not specified, the AssumeRoleProvider
        # is a noop and will not return credentials (which means we
        # move on to the next provider).
        creds = provider.load()
        self.assertIsNone(creds)

    def test_source_profile_not_provided(self):
        del self.fake_config['profiles']['development']['source_profile']
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(),
            cache={},
            profile_name='development',
        )

        # source_profile is required, we shoudl get an error.
        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            provider.load()

    def test_source_profile_does_not_exist(self):
        dev_profile = self.fake_config['profiles']['development']
        dev_profile['source_profile'] = 'does-not-exist'
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(),
            cache={},
            profile_name='development',
        )

        # source_profile is required, we shoudl get an error.
        with self.assertRaises(botocore.exceptions.InvalidConfigError):
            provider.load()

    def test_incomplete_source_credentials_raises_error(self):
        del self.fake_config['profiles']['longterm']['aws_access_key_id']
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(),
            cache={},
            profile_name='development',
        )

        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            provider.load()

    def test_source_profile_and_credential_source_provided(self):
        profile = self.fake_config['profiles']['development']
        profile['credential_source'] = 'SomeCredentialProvider'
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(),
            cache={},
            profile_name='development',
        )

        with self.assertRaises(botocore.exceptions.InvalidConfigError):
            provider.load()

    def test_credential_source_with_no_resolver_configured(self):
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(),
            cache={},
            profile_name='non-static',
        )

        with self.assertRaises(botocore.exceptions.InvalidConfigError):
            provider.load()

    def test_credential_source_with_no_providers_configured(self):
        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(),
            cache={},
            profile_name='non-static',
            credential_sourcer=credentials.CanonicalNameCredentialSourcer([]),
        )

        with self.assertRaises(botocore.exceptions.InvalidConfigError):
            provider.load()

    def test_credential_source_not_among_providers(self):
        fake_provider = mock.Mock()
        fake_provider.CANONICAL_NAME = 'CustomFakeProvider'

        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(),
            cache={},
            profile_name='non-static',
            credential_sourcer=credentials.CanonicalNameCredentialSourcer(
                [fake_provider]
            ),
        )

        # We configured the assume role provider with a single fake source
        # provider, CustomFakeProvider. The profile we are attempting to use
        # calls for the Environment credential provider as the credentials
        # source. Since that isn't one of the configured source providers,
        # an error is thrown.
        with self.assertRaises(botocore.exceptions.InvalidConfigError):
            provider.load()

    def test_assume_role_with_credential_source(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)

        config = {
            'profiles': {
                'sourced': {
                    'role_arn': 'myrole',
                    'credential_source': 'CustomMockProvider',
                }
            }
        }
        config_loader = self.create_config_loader(with_config=config)

        fake_provider = mock.Mock()
        fake_provider.CANONICAL_NAME = 'CustomMockProvider'
        fake_creds = credentials.Credentials('akid', 'skid', 'token')
        fake_provider.load.return_value = fake_creds

        provider = credentials.AssumeRoleProvider(
            config_loader,
            client_creator,
            cache={},
            profile_name='sourced',
            credential_sourcer=credentials.CanonicalNameCredentialSourcer(
                [fake_provider]
            ),
        )

        creds = provider.load()
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        client_creator.assert_called_with(
            'sts',
            aws_access_key_id=fake_creds.access_key,
            aws_secret_access_key=fake_creds.secret_key,
            aws_session_token=fake_creds.token,
        )

    def test_credential_source_returns_none(self):
        config = {
            'profiles': {
                'sourced': {
                    'role_arn': 'myrole',
                    'credential_source': 'CustomMockProvider',
                }
            }
        }
        config_loader = self.create_config_loader(with_config=config)

        fake_provider = mock.Mock()
        fake_provider.CANONICAL_NAME = 'CustomMockProvider'
        fake_provider.load.return_value = None

        provider = credentials.AssumeRoleProvider(
            config_loader,
            mock.Mock(),
            cache={},
            profile_name='sourced',
            credential_sourcer=credentials.CanonicalNameCredentialSourcer(
                [fake_provider]
            ),
        )

        with self.assertRaises(botocore.exceptions.CredentialRetrievalError):
            provider.load()

    def test_source_profile_can_reference_self(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)

        config = {
            'profiles': {
                'self-referencial': {
                    'aws_access_key_id': 'akid',
                    'aws_secret_access_key': 'skid',
                    'role_arn': 'myrole',
                    'source_profile': 'self-referencial',
                }
            }
        }

        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(config),
            client_creator,
            cache={},
            profile_name='self-referencial',
        )

        creds = provider.load()
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')

    def test_infinite_looping_profiles_raises_error(self):
        config = {
            'profiles': {
                'first': {'role_arn': 'first', 'source_profile': 'second'},
                'second': {'role_arn': 'second', 'source_profile': 'first'},
            }
        }

        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(config),
            mock.Mock(),
            cache={},
            profile_name='first',
        )

        with self.assertRaises(botocore.credentials.InfiniteLoopConfigError):
            provider.load()

    def test_recursive_assume_role(self):
        assume_responses = [
            Credentials('foo', 'bar', 'baz'),
            Credentials('spam', 'eggs', 'spamandegss'),
        ]
        responses = []
        for credential_set in assume_responses:
            responses.append(
                {
                    'Credentials': {
                        'AccessKeyId': credential_set.access_key,
                        'SecretAccessKey': credential_set.secret_key,
                        'SessionToken': credential_set.token,
                        'Expiration': self.some_future_time().isoformat(),
                    }
                }
            )
        client_creator = self.create_client_creator(with_response=responses)

        static_credentials = Credentials('akid', 'skid')
        config = {
            'profiles': {
                'first': {'role_arn': 'first', 'source_profile': 'second'},
                'second': {'role_arn': 'second', 'source_profile': 'third'},
                'third': {
                    'aws_access_key_id': static_credentials.access_key,
                    'aws_secret_access_key': static_credentials.secret_key,
                },
            }
        }

        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(config),
            client_creator,
            cache={},
            profile_name='first',
        )

        creds = provider.load()
        expected_creds = assume_responses[-1]
        self.assertEqual(creds.access_key, expected_creds.access_key)
        self.assertEqual(creds.secret_key, expected_creds.secret_key)
        self.assertEqual(creds.token, expected_creds.token)

        client_creator.assert_has_calls(
            [
                mock.call(
                    'sts',
                    aws_access_key_id=static_credentials.access_key,
                    aws_secret_access_key=static_credentials.secret_key,
                    aws_session_token=static_credentials.token,
                ),
                mock.call(
                    'sts',
                    aws_access_key_id=assume_responses[0].access_key,
                    aws_secret_access_key=assume_responses[0].secret_key,
                    aws_session_token=assume_responses[0].token,
                ),
            ]
        )

    def test_assume_role_with_profile_provider(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': self.some_future_time().isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        mock_builder = mock.Mock(spec=ProfileProviderBuilder)
        mock_builder.providers.return_value = [ProfileProvider('foo-profile')]

        provider = credentials.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator,
            cache={},
            profile_name='development',
            profile_provider_builder=mock_builder,
        )

        creds = provider.load().get_frozen_credentials()

        self.assertEqual(client_creator.call_count, 1)
        client_creator.assert_called_with(
            'sts',
            aws_access_key_id='foo-profile-access-key',
            aws_secret_access_key='foo-profile-secret-key',
            aws_session_token='foo-profile-token',
        )

        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')


class ProfileProvider:
    METHOD = 'fake'

    def __init__(self, profile_name):
        self._profile_name = profile_name

    def load(self):
        return Credentials(
            f'{self._profile_name}-access-key',
            f'{self._profile_name}-secret-key',
            f'{self._profile_name}-token',
            self.METHOD,
        )


class TestJSONCache(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.cache = credentials.JSONFileCache(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_supports_contains_check(self):
        # By default the cache is empty because we're
        # using a new temp dir everytime.
        self.assertTrue('mykey' not in self.cache)

    def test_add_key_and_contains_check(self):
        self.cache['mykey'] = {'foo': 'bar'}
        self.assertTrue('mykey' in self.cache)

    def test_added_key_can_be_retrieved(self):
        self.cache['mykey'] = {'foo': 'bar'}
        self.assertEqual(self.cache['mykey'], {'foo': 'bar'})

    def test_only_accepts_json_serializable_data(self):
        with self.assertRaises(ValueError):
            # set()'s cannot be serialized to a JSON string.
            self.cache['mykey'] = set()

    def test_can_override_existing_values(self):
        self.cache['mykey'] = {'foo': 'bar'}
        self.cache['mykey'] = {'baz': 'newvalue'}
        self.assertEqual(self.cache['mykey'], {'baz': 'newvalue'})

    def test_can_add_multiple_keys(self):
        self.cache['mykey'] = {'foo': 'bar'}
        self.cache['mykey2'] = {'baz': 'qux'}
        self.assertEqual(self.cache['mykey'], {'foo': 'bar'})
        self.assertEqual(self.cache['mykey2'], {'baz': 'qux'})

    def test_working_dir_does_not_exist(self):
        working_dir = os.path.join(self.tempdir, 'foo')
        cache = credentials.JSONFileCache(working_dir)
        cache['foo'] = {'bar': 'baz'}
        self.assertEqual(cache['foo'], {'bar': 'baz'})

    def test_working_dir_created_concurrently(self):
        # Simulate another process creating the directory between the
        # isdir() check and the makedirs() call.
        working_dir = os.path.join(self.tempdir, 'foo')
        cache = credentials.JSONFileCache(working_dir)
        real_isdir = os.path.isdir
        checked = []

        def racing_isdir(path):
            if not checked:
                checked.append(path)
                result = real_isdir(path)
                os.makedirs(working_dir)
                return result
            return real_isdir(path)

        with mock.patch('os.path.isdir', side_effect=racing_isdir):
            cache['foo'] = {'bar': 'baz'}
        self.assertEqual(cache['foo'], {'bar': 'baz'})

    def test_key_error_raised_when_cache_key_does_not_exist(self):
        with self.assertRaises(KeyError):
            self.cache['foo']

    def test_file_is_truncated_before_writing(self):
        self.cache['mykey'] = {
            'really long key in the cache': 'really long value in cache'
        }
        # Now overwrite it with a smaller value.
        self.cache['mykey'] = {'a': 'b'}
        self.assertEqual(self.cache['mykey'], {'a': 'b'})

    @skip_if_windows('File permissions tests not supported on Windows.')
    def test_permissions_for_file_restricted(self):
        self.cache['mykey'] = {'foo': 'bar'}
        filename = os.path.join(self.tempdir, 'mykey.json')
        self.assertEqual(os.stat(filename).st_mode & 0xFFF, 0o600)

    def test_cache_with_custom_dumps_func(self):
        def _custom_serializer(obj):
            return "custom foo"

        def _custom_dumps(obj):
            return json.dumps(obj, default=_custom_serializer)

        custom_dir = os.path.join(self.tempdir, 'custom')
        custom_cache = credentials.JSONFileCache(
            custom_dir, dumps_func=_custom_dumps
        )
        custom_cache['test'] = {'bar': object()}
        self.assertEqual(custom_cache['test'], {'bar': 'custom foo'})


class TestRefreshLogic(unittest.TestCase):
    def test_mandatory_refresh_needed(self):
        creds = IntegerRefresher(
            # These values will immediately trigger
            # a manadatory refresh.
            creds_last_for=2,
            mandatory_refresh=3,
            advisory_refresh=3,
        )
        temp = creds.get_frozen_credentials()
        self.assertEqual(temp, credentials.ReadOnlyCredentials('1', '1', '1'))

    def test_advisory_refresh_needed(self):
        creds = IntegerRefresher(
            # These values will immediately trigger
            # a manadatory refresh.
            creds_last_for=4,
            mandatory_refresh=2,
            advisory_refresh=5,
        )
        temp = creds.get_frozen_credentials()
        self.assertEqual(temp, credentials.ReadOnlyCredentials('1', '1', '1'))

    def test_refresh_fails_is_not_an_error_during_advisory_period(self):
        fail_refresh = mock.Mock(side_effect=Exception("refresh failed"))
        creds = IntegerRefresher(
            creds_last_for=5,
            advisory_refresh=7,
            mandatory_refresh=3,
            refresh_function=fail_refresh,
        )
        temp = creds.get_frozen_credentials()
        # We should have called the refresh function.
        self.assertTrue(fail_refresh.called)
        # The fail_refresh function will raise an exception.
        # Because we're in the advisory period we'll not propogate
        # the exception and return the current set of credentials
        # (generation '1').
        self.assertEqual(temp, credentials.ReadOnlyCredentials('0', '0', '0'))

    def test_exception_propogated_on_error_during_mandatory_period(self):
        fail_refresh = mock.Mock(side_effect=Exception("refresh failed"))
        creds = IntegerRefresher(
            creds_last_for=5,
            advisory_refresh=10,
            # Note we're in the mandatory period now (5 < 7< 10).
            mandatory_refresh=7,
            refresh_function=fail_refresh,
        )
        with self.assertRaisesRegex(Exception, 'refresh failed'):
            creds.get_frozen_credentials()

    def test_exception_propogated_on_expired_credentials(self):
        fail_refresh = mock.Mock(side_effect=Exception("refresh failed"))
        creds = IntegerRefresher(
            # Setting this to 0 mean the credentials are immediately
            # expired.
            creds_last_for=0,
            advisory_refresh=10,
            mandatory_refresh=7,
            refresh_function=fail_refresh,
        )
        with self.assertRaisesRegex(Exception, 'refresh failed'):
            # Because credentials are actually expired, any
            # failure to refresh should be propagated.
            creds.get_frozen_credentials()

    def test_refresh_giving_expired_credentials_raises_exception(self):
        # This verifies an edge cases where refreshed credentials
        # still give expired credentials:
        # 1. We see credentials are expired.
        # 2. We try to refresh the credentials.
        # 3. The "refreshed" credentials are still expired.
        #
        # In this case, we hard fail and let the user know what
        # happened.
        creds = IntegerRefresher(
            # Negative number indicates that the credentials
            # have already been expired for 2 seconds, even
            # on refresh.
            creds_last_for=-2,
        )
        err_msg = 'refreshed credentials are still expired'
        with self.assertRaisesRegex(RuntimeError, err_msg):
            # Because credentials are actually expired, any
            # failure to refresh should be propagated.
            creds.get_frozen_credentials()


class TestContainerProvider(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.tempdir)

    def test_noop_if_env_var_is_not_set(self):
        # The 'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI' env var
        # is not present as an env var.
        environ = {}
        provider = credentials.ContainerProvider(environ)
        creds = provider.load()
        self.assertIsNone(creds)

    def full_url(self, url):
        return f'http://{ContainerMetadataFetcher.IP_ADDRESS}{url}'

    def create_fetcher(self):
        fetcher = mock.Mock(spec=ContainerMetadataFetcher)
        fetcher.full_url = self.full_url
        return fetcher

    def test_retrieve_from_provider_if_env_var_present(self):
        environ = {
            'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI': '/latest/credentials?id=foo'
        }
        fetcher = self.create_fetcher()
        timeobj = datetime.now(tzlocal())
        timestamp = (timeobj + timedelta(hours=24)).isoformat()
        fetcher.retrieve_full_uri.return_value = {
            "AccessKeyId": "access_key",
            "SecretAccessKey": "secret_key",
            "Token": "token",
            "Expiration": timestamp,
        }
        provider = credentials.ContainerProvider(environ, fetcher)
        creds = provider.load()

        fetcher.retrieve_full_uri.assert_called_with(
            self.full_url('/latest/credentials?id=foo'), headers=None
        )
        self.assertEqual(creds.access_key, 'access_key')
        self.assertEqual(creds.secret_key, 'secret_key')
        self.assertEqual(creds.token, 'token')
        self.assertEqual(creds.method, 'container-role')

    def test_creds_refresh_when_needed(self):
        environ = {
            'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI': '/latest/credentials?id=foo'
        }
        fetcher = mock.Mock(spec=credentials.ContainerMetadataFetcher)
        timeobj = datetime.now(tzlocal())
        expired_timestamp = (timeobj - timedelta(hours=23)).isoformat()
        future_timestamp = (timeobj + timedelta(hours=1)).isoformat()
        fetcher.retrieve_full_uri.side_effect = [
            {
                "AccessKeyId": "access_key_old",
                "SecretAccessKey": "secret_key_old",
                "Token": "token_old",
                "Expiration": expired_timestamp,
            },
            {
                "AccessKeyId": "access_key_new",
                "SecretAccessKey": "secret_key_new",
                "Token": "token_new",
                "Expiration": future_timestamp,
            },
        ]
        provider = credentials.ContainerProvider(environ, fetcher)
        creds = provider.load()
        frozen_creds = creds.get_frozen_credentials()
        self.assertEqual(frozen_creds.access_key, 'access_key_new')
        self.assertEqual(frozen_creds.secret_key, 'secret_key_new')
        self.assertEqual(frozen_creds.token, 'token_new')

    def test_http_error_propagated(self):
        environ = {
            'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI': '/latest/credentials?id=foo'
        }
        fetcher = mock.Mock(spec=credentials.ContainerMetadataFetcher)
        exception = botocore.exceptions.CredentialRetrievalError
        fetcher.retrieve_full_uri.side_effect = exception(
            provider='ecs-role', error_msg='fake http error'
        )
        with self.assertRaises(exception):
            provider = credentials.ContainerProvider(environ, fetcher)
            provider.load()

    def test_http_error_on_refresh_uses_cached_credentials(self):
        # If refresh fails after credentials are loaded, keep using the last
        # credential set instead of failing the caller.
        environ = {
            'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI': '/latest/credentials?id=foo'
        }
        fetcher = mock.Mock(spec=credentials.ContainerMetadataFetcher)
        timeobj = datetime.now(tzlocal())
        expired_timestamp = (timeobj - timedelta(hours=23)).isoformat()
        http_exception = botocore.exceptions.MetadataRetrievalError
        fetcher.retrieve_full_uri.side_effect = [
            {
                "AccessKeyId": "access_key_old",
                "SecretAccessKey": "secret_key_old",
                "Token": "token_old",
                "Expiration": expired_timestamp,
            },
            http_exception(error_msg='HTTP connection timeout'),
        ]
        provider = credentials.ContainerProvider(environ, fetcher)
        # First time works with no issues.
        creds = provider.load()
        # Second time with a refresh should fall back to cached credentials.
        frozen = creds.get_frozen_credentials()
        self.assertEqual(frozen.access_key, 'access_key_old')

    def test_can_use_full_url(self):
        environ = {
            'AWS_CONTAINER_CREDENTIALS_FULL_URI': 'http://localhost/foo'
        }
        fetcher = self.create_fetcher()
        timeobj = datetime.now(tzlocal())
        timestamp = (timeobj + timedelta(hours=24)).isoformat()
        fetcher.retrieve_full_uri.return_value = {
            "AccessKeyId": "access_key",
            "SecretAccessKey": "secret_key",
            "Token": "token",
            "Expiration": timestamp,
        }
        provider = credentials.ContainerProvider(environ, fetcher)
        creds = provider.load()

        fetcher.retrieve_full_uri.assert_called_with(
            'http://localhost/foo', headers=None
        )
        self.assertEqual(creds.access_key, 'access_key')
        self.assertEqual(creds.secret_key, 'secret_key')
        self.assertEqual(creds.token, 'token')
        self.assertEqual(creds.method, 'container-role')

    def test_can_pass_basic_auth_token(self):
        environ = {
            'AWS_CONTAINER_CREDENTIALS_FULL_URI': 'http://localhost/foo',
            'AWS_CONTAINER_AUTHORIZATION_TOKEN': 'Basic auth-token',
        }
        fetcher = self.create_fetcher()
        timeobj = datetime.now(tzlocal())
        timestamp = (timeobj + timedelta(hours=24)).isoformat()
        fetcher.retrieve_full_uri.return_value = {
            "AccessKeyId": "access_key",
            "SecretAccessKey": "secret_key",
            "Token": "token",
            "Expiration": timestamp,
        }
        provider = credentials.ContainerProvider(environ, fetcher)
        creds = provider.load()

        fetcher.retrieve_full_uri.assert_called_with(
            'http://localhost/foo',
            headers={'Authorization': 'Basic auth-token'},
        )
        self.assertEqual(creds.access_key, 'access_key')
        self.assertEqual(creds.secret_key, 'secret_key')
        self.assertEqual(creds.token, 'token')
        self.assertEqual(creds.method, 'container-role')

    def test_can_pass_auth_token_from_file(self):
        token_file_path = os.path.join(self.tempdir, 'token.jwt')
        with open(token_file_path, 'w') as token_file:
            token_file.write('Basic auth-token')
        environ = {
            'AWS_CONTAINER_CREDENTIALS_FULL_URI': 'http://localhost/foo',
            'AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE': token_file_path,
        }
        fetcher = self.create_fetcher()
        timeobj = datetime.now(tzlocal())
        timestamp = (timeobj + timedelta(hours=24)).isoformat()
        fetcher.retrieve_full_uri.return_value = {
            "AccessKeyId": "access_key",
            "SecretAccessKey": "secret_key",
            "Token": "token",
            "Expiration": timestamp,
        }
        provider = credentials.ContainerProvider(environ, fetcher)
        creds = provider.load()

        fetcher.retrieve_full_uri.assert_called_with(
            'http://localhost/foo',
            headers={'Authorization': 'Basic auth-token'},
        )
        self.assertEqual(creds.access_key, 'access_key')
        self.assertEqual(creds.secret_key, 'secret_key')
        self.assertEqual(creds.token, 'token')
        self.assertEqual(creds.method, 'container-role')

    def test_throws_error_on_invalid_token_file(self):
        token_file_path = '/some/path/token.jwt'
        environ = {
            'AWS_CONTAINER_CREDENTIALS_FULL_URI': 'http://localhost/foo',
            'AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE': token_file_path,
        }
        fetcher = self.create_fetcher()
        provider = credentials.ContainerProvider(environ, fetcher)

        with self.assertRaises(FileNotFoundError):
            provider.load()

    def test_throws_error_on_illegal_header(self):
        environ = {
            'AWS_CONTAINER_CREDENTIALS_FULL_URI': 'http://localhost/foo',
            'AWS_CONTAINER_AUTHORIZATION_TOKEN': 'invalid\r\ntoken',
        }
        fetcher = self.create_fetcher()
        provider = credentials.ContainerProvider(environ, fetcher)

        with self.assertRaises(ValueError):
            provider.load()

    def test_can_retrieve_account_id(self):
        environ = {
            'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI': '/latest/credentials?id=foo'
        }
        fetcher = self.create_fetcher()
        timeobj = datetime.now(tzlocal())
        timestamp = (timeobj + timedelta(hours=24)).isoformat()
        fetcher.retrieve_full_uri.return_value = {
            "AccessKeyId": "access_key",
            "SecretAccessKey": "secret_key",
            "Token": "token",
            "Expiration": timestamp,
            "AccountId": "account_id",
        }
        provider = credentials.ContainerProvider(environ, fetcher)
        creds = provider.load()

        fetcher.retrieve_full_uri.assert_called_with(
            self.full_url('/latest/credentials?id=foo'), headers=None
        )
        self.assertEqual(creds.access_key, 'access_key')
        self.assertEqual(creds.secret_key, 'secret_key')
        self.assertEqual(creds.token, 'token')
        self.assertEqual(creds.method, 'container-role')
        self.assertEqual(creds.account_id, 'account_id')


class TestProcessProvider(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.loaded_config = {}
        self.load_config = mock.Mock(return_value=self.loaded_config)
        self.invoked_process = mock.Mock()
        self.popen_mock = mock.Mock(
            return_value=self.invoked_process, spec=subprocess.Popen
        )

    def create_process_provider(self, profile_name='default'):
        provider = ProcessProvider(
            profile_name, self.load_config, popen=self.popen_mock
        )
        return provider

    def _get_output(self, stdout, stderr=''):
        return json.dumps(stdout).encode('utf-8'), stderr.encode('utf-8')

    def _set_process_return_value(self, stdout, stderr='', rc=0):
        output = self._get_output(stdout, stderr)
        self.invoked_process.communicate.return_value = output
        self.invoked_process.returncode = rc

    def test_process_not_invoked_if_profile_does_not_exist(self):
        # self.loaded_config is an empty dictionary with no profile
        # information.
        provider = self.create_process_provider()
        self.assertIsNone(provider.load())

    def test_process_not_invoked_if_not_configured_for_empty_config(self):
        # No credential_process configured so we skip this provider.
        self.loaded_config['profiles'] = {'default': {}}
        provider = self.create_process_provider()
        self.assertIsNone(provider.load())

    def test_can_retrieve_via_process(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        self._set_process_return_value(
            {
                'Version': 1,
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': '2999-01-01T00:00:00Z',
            }
        )

        provider = self.create_process_provider()
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.method, 'custom-process')
        self.popen_mock.assert_called_with(
            ['my-process'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    def test_can_pass_arguments_through(self):
        self.loaded_config['profiles'] = {
            'default': {
                'credential_process': 'my-process --foo --bar "one two"'
            }
        }
        self._set_process_return_value(
            {
                'Version': 1,
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': '2999-01-01T00:00:00Z',
            }
        )

        provider = self.create_process_provider()
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.popen_mock.assert_called_with(
            ['my-process', '--foo', '--bar', 'one two'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_can_refresh_credentials(self):
        # We given a time that's already expired so .access_key
        # will trigger the refresh worfklow.  We just need to verify
        # that the refresh function gives the same result as the
        # initial retrieval.
        expired_date = '2016-01-01T00:00:00Z'
        future_date = str(datetime.now(tzlocal()) + timedelta(hours=24))
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        old_creds = self._get_output(
            {
                'Version': 1,
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': expired_date,
            }
        )
        new_creds = self._get_output(
            {
                'Version': 1,
                'AccessKeyId': 'foo2',
                'SecretAccessKey': 'bar2',
                'SessionToken': 'baz2',
                'Expiration': future_date,
            }
        )
        self.invoked_process.communicate.side_effect = [old_creds, new_creds]
        self.invoked_process.returncode = 0

        provider = self.create_process_provider()
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo2')
        self.assertEqual(creds.secret_key, 'bar2')
        self.assertEqual(creds.token, 'baz2')
        self.assertEqual(creds.method, 'custom-process')

    def test_non_zero_rc_raises_exception(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        self._set_process_return_value('', 'Error Message', 1)

        provider = self.create_process_provider()
        exception = botocore.exceptions.CredentialRetrievalError
        with self.assertRaisesRegex(exception, 'Error Message'):
            provider.load()

    def test_unsupported_version_raises_mismatch(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        bad_version = 100
        self._set_process_return_value(
            {
                'Version': bad_version,
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': '2999-01-01T00:00:00Z',
            }
        )

        provider = self.create_process_provider()
        exception = botocore.exceptions.CredentialRetrievalError
        with self.assertRaisesRegex(exception, 'Unsupported version'):
            provider.load()

    def test_missing_version_in_payload_returned_raises_exception(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        self._set_process_return_value(
            {
                # Let's say they forget a 'Version' key.
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': '2999-01-01T00:00:00Z',
            }
        )

        provider = self.create_process_provider()
        exception = botocore.exceptions.CredentialRetrievalError
        with self.assertRaisesRegex(exception, 'Unsupported version'):
            provider.load()

    def test_missing_access_key_raises_exception(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        self._set_process_return_value(
            {
                'Version': 1,
                # Missing access key.
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': '2999-01-01T00:00:00Z',
            }
        )

        provider = self.create_process_provider()
        exception = botocore.exceptions.CredentialRetrievalError
        with self.assertRaisesRegex(exception, 'Missing required key'):
            provider.load()

    def test_missing_secret_key_raises_exception(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        self._set_process_return_value(
            {
                'Version': 1,
                'AccessKeyId': 'foo',
                # Missing secret key.
                'SessionToken': 'baz',
                'Expiration': '2999-01-01T00:00:00Z',
            }
        )

        provider = self.create_process_provider()
        exception = botocore.exceptions.CredentialRetrievalError
        with self.assertRaisesRegex(exception, 'Missing required key'):
            provider.load()

    def test_missing_session_token(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        self._set_process_return_value(
            {
                'Version': 1,
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                # Missing session token.
                'Expiration': '2999-01-01T00:00:00Z',
            }
        )

        provider = self.create_process_provider()
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertIsNone(creds.token)
        self.assertEqual(creds.method, 'custom-process')

    def test_missing_expiration(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        self._set_process_return_value(
            {
                'Version': 1,
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                # Missing expiration.
            }
        )

        provider = self.create_process_provider()
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.method, 'custom-process')

    def test_missing_expiration_and_session_token(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        self._set_process_return_value(
            {
                'Version': 1,
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                # Missing session token and expiration
            }
        )

        provider = self.create_process_provider()
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertIsNone(creds.token)
        self.assertEqual(creds.method, 'custom-process')

    def test_can_retrieve_account_id(self):
        self.loaded_config['profiles'] = {
            'default': {'credential_process': 'my-process'}
        }
        self._set_process_return_value(
            {
                'Version': 1,
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': '2999-01-01T00:00:00Z',
                'AccountId': '123456789012',
            }
        )

        provider = self.create_process_provider()
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.method, 'custom-process')
        self.assertEqual(creds.account_id, '123456789012')

    def test_can_retrieve_account_id_via_profile_config(self):
        self.loaded_config['profiles'] = {
            'default': {
                'credential_process': 'my-process',
                'aws_account_id': '123456789012',
            }
        }
        self._set_process_return_value(
            {
                'Version': 1,
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': '2999-01-01T00:00:00Z',
            }
        )

        provider = self.create_process_provider()
        creds = provider.load()
        self.assertIsNotNone(creds)
        self.assertEqual(creds.access_key, 'foo')
        self.assertEqual(creds.secret_key, 'bar')
        self.assertEqual(creds.token, 'baz')
        self.assertEqual(creds.method, 'custom-process')
        self.assertEqual(creds.account_id, '123456789012')


class TestProfileProviderBuilder(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.mock_session = mock.Mock(spec=Session)
        self.builder = ProfileProviderBuilder(self.mock_session)

    def test_profile_provider_builder_order(self):
        providers = self.builder.providers('some-profile')
        expected_providers = [
            AssumeRoleWithWebIdentityProvider,
            SSOProvider,
            SharedCredentialProvider,
            LoginProvider,
            ProcessProvider,
            ConfigProvider,
        ]
        self.assertEqual(len(providers), len(expected_providers))
        zipped_providers = zip(providers, expected_providers)
        for provider, expected_type in zipped_providers:
            self.assertTrue(isinstance(provider, expected_type))


class TestSSOCredentialFetcher(unittest.TestCase):
    def setUp(self):
        self.sso = Session().create_client('sso', region_name='us-east-1')
        self.stubber = Stubber(self.sso)
        self.mock_session = mock.Mock(spec=Session)
        self.mock_session.create_client.return_value = self.sso

        self.cache = {}
        self.sso_region = 'us-east-1'
        self.start_url = 'https://d-92671207e4.awsapps.com/start'
        self.role_name = 'test-role'
        self.account_id = '1234567890'
        self.access_token = {
            'accessToken': 'some.sso.token',
            'expiresAt': '2018-10-18T22:26:40Z',
        }
        # This is just an arbitrary point in time we can pin to
        self.now = datetime(2008, 9, 23, 12, 26, 40, tzinfo=tzutc())
        # The SSO endpoint uses ms whereas the OIDC endpoint uses seconds
        self.now_timestamp = 1222172800000
        self.mock_time_fetcher = mock.Mock(return_value=self.now)

        self.loader = mock.Mock(spec=SSOTokenLoader)
        self.loader.return_value = self.access_token
        self.fetcher = SSOCredentialFetcher(
            self.start_url,
            self.sso_region,
            self.role_name,
            self.account_id,
            self.mock_session.create_client,
            token_loader=self.loader,
            cache=self.cache,
            time_fetcher=self.mock_time_fetcher,
        )

    def test_can_fetch_credentials(self):
        expected_params = {
            'roleName': self.role_name,
            'accountId': self.account_id,
            'accessToken': self.access_token['accessToken'],
        }
        expected_response = {
            'roleCredentials': {
                'accessKeyId': 'foo',
                'secretAccessKey': 'bar',
                'sessionToken': 'baz',
                'expiration': self.now_timestamp + 1000000,
            }
        }
        self.stubber.add_response(
            'get_role_credentials',
            expected_response,
            expected_params=expected_params,
        )
        with self.stubber:
            credentials = self.fetcher.fetch_credentials()
        self.assertEqual(credentials['access_key'], 'foo')
        self.assertEqual(credentials['secret_key'], 'bar')
        self.assertEqual(credentials['token'], 'baz')
        self.assertEqual(credentials['expiry_time'], '2008-09-23T12:43:20Z')
        cache_key = '048db75bbe50955c16af7aba6ff9c41a3131bb7e'
        expected_cached_credentials = {
            'ProviderType': 'sso',
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': '2008-09-23T12:43:20Z',
                'AccountId': '1234567890',
            },
        }
        self.assertEqual(self.cache[cache_key], expected_cached_credentials)

    def test_raises_helpful_message_on_unauthorized_exception(self):
        expected_params = {
            'roleName': self.role_name,
            'accountId': self.account_id,
            'accessToken': self.access_token['accessToken'],
        }
        self.stubber.add_client_error(
            'get_role_credentials',
            service_error_code='UnauthorizedException',
            expected_params=expected_params,
        )
        with self.assertRaises(botocore.exceptions.UnauthorizedSSOTokenError):
            with self.stubber:
                self.fetcher.fetch_credentials()

    def test_expired_legacy_token_has_expected_behavior(self):
        # Mock the current time to be in the future after the access token has expired
        now = datetime(2018, 10, 19, 12, 26, 40, tzinfo=tzutc())
        mock_client = mock.Mock()
        create_mock_client = mock.Mock(return_value=mock_client)
        fetcher = SSOCredentialFetcher(
            self.start_url,
            self.sso_region,
            self.role_name,
            self.account_id,
            create_mock_client,
            token_loader=self.loader,
            cache=self.cache,
            time_fetcher=mock.Mock(return_value=now),
        )
        # since the cached token is expired, an UnauthorizedSSOTokenError should be
        # raised and GetRoleCredentials should not be called.
        with self.assertRaises(botocore.exceptions.UnauthorizedSSOTokenError):
            fetcher.fetch_credentials()
        self.assertFalse(mock_client.get_role_credentials.called)

    @mock.patch('botocore.credentials.register_feature_ids')
    def test_feature_ids_registered_during_get_credentials(
        self, mock_register
    ):
        response = {
            'roleCredentials': {
                'accessKeyId': 'foo',
                'secretAccessKey': 'bar',
                'sessionToken': 'baz',
                'expiration': self.now_timestamp + 1000000,
            }
        }
        params = {
            'roleName': self.role_name,
            'accountId': self.account_id,
            'accessToken': self.access_token['accessToken'],
        }
        self.stubber.add_response(
            'get_role_credentials',
            response,
            expected_params=params,
        )

        self.stubber.activate()
        try:
            fetcher = SSOCredentialFetcher(
                self.start_url,
                self.sso_region,
                self.role_name,
                self.account_id,
                self.mock_session.create_client,
                token_loader=self.loader,
                cache=self.cache,
                time_fetcher=self.mock_time_fetcher,
            )
            test_feature_ids = {'test_feature_1', 'test_feature_2'}
            fetcher.feature_ids = test_feature_ids
            fetcher.fetch_credentials()
            mock_register.assert_called_once_with(test_feature_ids)
        finally:
            self.stubber.deactivate()


class TestSSOProvider(unittest.TestCase):
    def setUp(self):
        with mock.patch(
            'botocore.credentials.LoginProvider.load',
            return_value=None,
        ):
            self.sso = Session().create_client('sso', region_name='us-east-1')
        self.stubber = Stubber(self.sso)
        self.mock_session = mock.Mock(spec=Session)
        self.mock_session.create_client.return_value = self.sso

        self.sso_region = 'us-east-1'
        self.start_url = 'https://d-92671207e4.awsapps.com/start'
        self.role_name = 'test-role'
        self.account_id = '1234567890'
        self.access_token = 'some.sso.token'

        self.profile_name = 'sso-profile'
        self.config = {
            'sso_region': self.sso_region,
            'sso_start_url': self.start_url,
            'sso_role_name': self.role_name,
            'sso_account_id': self.account_id,
        }
        self.expires_at = datetime.now(tzutc()) + timedelta(hours=24)
        self.cached_creds_key = '048db75bbe50955c16af7aba6ff9c41a3131bb7e'
        self.cached_token_key = '13f9d35043871d073ab260e020f0ffde092cb14b'
        self.cache = {
            self.cached_token_key: {
                'accessToken': self.access_token,
                'expiresAt': self.expires_at.strftime('%Y-%m-%dT%H:%M:%S%Z'),
            }
        }
        self.provider = SSOProvider(
            load_config=self._mock_load_config,
            client_creator=self.mock_session.create_client,
            profile_name=self.profile_name,
            cache=self.cache,
            token_cache=self.cache,
        )

        self.expected_get_role_credentials_params = {
            'roleName': self.role_name,
            'accountId': self.account_id,
            'accessToken': self.access_token,
        }
        expiration = datetime2timestamp(self.expires_at)
        self.expected_get_role_credentials_response = {
            'roleCredentials': {
                'accessKeyId': 'foo',
                'secretAccessKey': 'bar',
                'sessionToken': 'baz',
                'expiration': int(expiration * 1000),
            }
        }

    def _mock_load_config(self):
        return {
            'profiles': {
                self.profile_name: self.config,
            }
        }

    def _add_get_role_credentials_response(self):
        self.stubber.add_response(
            'get_role_credentials',
            self.expected_get_role_credentials_response,
            self.expected_get_role_credentials_params,
        )

    def test_load_sso_credentials_without_cache(self):
        self._add_get_role_credentials_response()
        with self.stubber:
            credentials = self.provider.load()
            self.assertEqual(credentials.access_key, 'foo')
            self.assertEqual(credentials.secret_key, 'bar')
            self.assertEqual(credentials.token, 'baz')

    def test_load_sso_credentials_with_cache(self):
        cached_creds = {
            'Credentials': {
                'AccessKeyId': 'cached-akid',
                'SecretAccessKey': 'cached-sak',
                'SessionToken': 'cached-st',
                'Expiration': self.expires_at.strftime('%Y-%m-%dT%H:%M:%S%Z'),
            }
        }
        self.cache[self.cached_creds_key] = cached_creds
        credentials = self.provider.load()
        self.assertEqual(credentials.access_key, 'cached-akid')
        self.assertEqual(credentials.secret_key, 'cached-sak')
        self.assertEqual(credentials.token, 'cached-st')

    def test_load_sso_credentials_with_cache_expired(self):
        cached_creds = {
            'Credentials': {
                'AccessKeyId': 'expired-akid',
                'SecretAccessKey': 'expired-sak',
                'SessionToken': 'expired-st',
                'Expiration': '2002-10-22T20:52:11UTC',
            }
        }
        self.cache[self.cached_creds_key] = cached_creds

        self._add_get_role_credentials_response()
        with self.stubber:
            credentials = self.provider.load()
            self.assertEqual(credentials.access_key, 'foo')
            self.assertEqual(credentials.secret_key, 'bar')
            self.assertEqual(credentials.token, 'baz')

    def test_refresh_failure_returns_cached_credentials(self):
        self._add_get_role_credentials_response()
        self.stubber.add_client_error(
            'get_role_credentials',
            service_error_code='TooManyRequestsException',
            expected_params=self.expected_get_role_credentials_params,
        )

        local_now = mock.Mock(return_value=datetime.now(tzlocal()))
        with self.stubber:
            with mock.patch('botocore.credentials._local_now', local_now):
                credentials = self.provider.load()
                first = credentials.get_frozen_credentials()

                local_now.return_value = self.expires_at
                second = credentials.get_frozen_credentials()

        self.assertEqual(first.access_key, 'foo')
        self.assertEqual(first.secret_key, 'bar')
        self.assertEqual(first.token, 'baz')
        self.assertEqual(second.access_key, 'foo')
        self.assertEqual(second.secret_key, 'bar')
        self.assertEqual(second.token, 'baz')

    def test_required_config_not_set(self):
        del self.config['sso_start_url']
        # If any required configuration is missing we should get an error
        with self.assertRaises(botocore.exceptions.InvalidConfigError):
            self.provider.load()

    def test_load_sso_credentials_with_account_id(self):
        self._add_get_role_credentials_response()
        with self.stubber:
            credentials = self.provider.load()
            self.assertEqual(credentials.access_key, 'foo')
            self.assertEqual(credentials.secret_key, 'bar')
            self.assertEqual(credentials.token, 'baz')
            self.assertEqual(credentials.account_id, '1234567890')


@pytest.mark.parametrize(
    "account_id, expected", [("123456789012", "123456789012"), (None, None)]
)
def test_get_deferred_property_account_id(account_id, expected):
    creds = Credentials(
        access_key='foo', secret_key='bar', token='baz', account_id=account_id
    )
    deferred_account_id = creds.get_deferred_property('account_id')
    assert callable(deferred_account_id)
    assert deferred_account_id() == expected


@pytest.fixture
def mock_base_assume_role_credential_fetcher():
    return BaseAssumeRoleCredentialFetcher(
        client_creator=mock.Mock(),
        role_arn='arn:aws:iam::123456789012:role/RoleA',
    )


def test_add_account_id_to_response_with_valid_arn(
    mock_base_assume_role_credential_fetcher,
):
    response = {
        'Credentials': {},
        'AssumedRoleUser': {
            'AssumedRoleId': 'myroleid',
            'Arn': 'arn:aws:iam::123456789012:role/RoleA',
        },
    }
    mock_base_assume_role_credential_fetcher._add_account_id_to_response(
        response
    )
    assert 'AccountId' in response['Credentials']
    assert response['Credentials']['AccountId'] == '123456789012'


def test_add_account_id_to_response_with_invalid_arn(
    mock_base_assume_role_credential_fetcher, caplog
):
    response = {
        'Credentials': {},
        'AssumedRoleUser': {
            'AssumedRoleId': 'myroleid',
            'Arn': 'invalid-arn',
        },
    }
    with caplog.at_level(logging.DEBUG):
        mock_base_assume_role_credential_fetcher._add_account_id_to_response(
            response
        )
    assert 'AccountId' not in response['Credentials']
    assert 'Unable to extract account ID from Arn' in caplog.text


def load_login_test_cases():
    test_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'login',
        'login-provider-test-cases.json',
    )
    with open(test_dir) as f:
        data = json.load(f)
    return data


class TestLoginProvider:
    FROZEN_TIME = datetime(2025, 11, 19, 0, 0, 0, tzinfo=tzutc())

    @pytest.mark.parametrize(
        "test_case", load_login_test_cases(), ids=lambda x: x["documentation"]
    )
    def test_login_credentials(self, test_case):
        tempdir = tempfile.mkdtemp()
        config_file = os.path.join(tempdir, 'config')
        cache_dir = os.path.join(tempdir, 'cache')
        os.makedirs(cache_dir)

        config_contents = test_case.get('configContents')
        with open(config_file, 'w') as f:
            f.write(config_contents)

        cache_contents = test_case.get('cacheContents', {})
        for filename, cache_data in cache_contents.items():
            cache_file_path = os.path.join(cache_dir, filename)
            with open(cache_file_path, 'w') as f:
                json.dump(cache_data, f)

        original_config_file = os.environ.get('AWS_CONFIG_FILE')
        original_cache_dir = os.environ.get('AWS_LOGIN_CACHE_DIRECTORY')

        os.environ['AWS_CONFIG_FILE'] = config_file
        os.environ['AWS_LOGIN_CACHE_DIRECTORY'] = cache_dir

        try:
            session = botocore.session.Session(profile='signin')
            token_cache = credentials.JSONFileCache(cache_dir)

            def load_config():
                profile_config = session.get_scoped_config()
                return {'profiles': {'signin': profile_config}}

            mock_client = mock.Mock()
            mock_client.exceptions.AccessDeniedException = (
                botocore.exceptions.ClientError
            )

            for api_call in test_case.get('mockApiCalls', []):
                if (
                    'responseCode' in api_call
                    and api_call['responseCode'] >= 400
                ):
                    mock_client.create_o_auth2_token.side_effect = ClientError(
                        {}, 'CreateOAuth2Token'
                    )
                else:
                    mock_client.create_o_auth2_token.return_value = api_call[
                        'response'
                    ]

            with mock.patch(
                'botocore.credentials._local_now',
                return_value=self.FROZEN_TIME,
            ):
                provider = credentials.LoginProvider(
                    token_cache=token_cache,
                    load_config=load_config,
                    profile_name='signin',
                    client_creator=lambda service_name, **kwargs: mock_client,
                )

                try:
                    # Get frozen credentials to trigger the refresh if needed
                    refreshable_creds = provider.load()
                    frozen_creds = refreshable_creds.get_frozen_credentials()

                    outcomes = test_case.get('outcomes', [])
                    for outcome in outcomes:
                        if outcome.get('result') == 'credentials':
                            self._validate_creds(frozen_creds, outcome)

                        elif outcome.get('result') == 'cacheContents':
                            for (
                                cache_filename,
                                expected_cache_data,
                            ) in outcome.items():
                                if cache_filename == 'result':
                                    continue

                                self._validate_cached_token_contents(
                                    cache_dir,
                                    cache_filename,
                                    expected_cache_data,
                                )

                    self._validate_refresh_calls(
                        mock_client, test_case.get('mockApiCalls', [])
                    )

                except LoginError as e:
                    if any(
                        outcome.get('result') == 'error'
                        for outcome in test_case.get('outcomes')
                    ):
                        pass  # verify that an error was raised as expected
                    else:
                        raise e

        finally:
            if original_config_file is not None:
                os.environ['AWS_CONFIG_FILE'] = original_config_file
            elif 'AWS_CONFIG_FILE' in os.environ:
                del os.environ['AWS_CONFIG_FILE']

            if original_cache_dir is not None:
                os.environ['AWS_LOGIN_CACHE_DIRECTORY'] = original_cache_dir
            elif 'AWS_LOGIN_CACHE_DIRECTORY' in os.environ:
                del os.environ['AWS_LOGIN_CACHE_DIRECTORY']

            shutil.rmtree(tempdir)

    @staticmethod
    def _validate_refresh_calls(mock_client, mock_api_calls):
        if not mock_api_calls:
            mock_client.create_o_auth2_token.assert_not_called()
            return

        call_args_list = mock_client.create_o_auth2_token.call_args_list

        for i, expected_api_call in enumerate(mock_api_calls):
            actual_call = call_args_list[i]
            actual_kwargs = actual_call.kwargs if actual_call.kwargs else {}
            expected_request = expected_api_call['request']

            assert 'tokenInput' in actual_kwargs
            assert (
                expected_request['tokenInput'] == actual_kwargs['tokenInput']
            )

    @staticmethod
    def _validate_cached_token_contents(
        cache_dir, cache_filename, expected_cache_data
    ):
        cache_file_path = os.path.join(cache_dir, cache_filename)
        assert os.path.exists(cache_file_path)

        with open(cache_file_path) as f:
            actual_cache_data = json.load(f)

        assert actual_cache_data == expected_cache_data

    @staticmethod
    def _validate_creds(resolved_credentials, expected_output):
        assert resolved_credentials is not None

        if 'accessKeyId' in expected_output:
            assert (
                resolved_credentials.access_key
                == expected_output['accessKeyId']
            )

        if 'secretAccessKey' in expected_output:
            assert (
                resolved_credentials.secret_key
                == expected_output['secretAccessKey']
            )

        if 'sessionToken' in expected_output:
            assert (
                resolved_credentials.token == expected_output['sessionToken']
            )

        if 'accountId' in expected_output:
            assert (
                resolved_credentials.account_id == expected_output['accountId']
            )

    def test_refresh_failure_returns_cached_credentials(self):
        profile_name = 'test-profile'
        mock_token_cache = mock.Mock()
        mock_client_creator = mock.Mock()
        mock_load_config = mock.Mock()
        now = datetime.now(tzutc())
        expiry_time = now + timedelta(hours=1)

        mock_load_config.return_value = {
            'profiles': {
                profile_name: {
                    'login_session': 'my-session',
                    'region': 'us-east-1',
                }
            }
        }

        with (
            mock.patch('botocore.credentials.LoginCredentialsLoader'),
            mock.patch(
                'botocore.credentials.LoginCredentialFetcher'
            ) as mock_fetcher_class,
        ):
            mock_fetcher = mock.Mock()
            expected_creds = {
                'access_key': 'test-access-key',
                'secret_key': 'test-secret-key',
                'token': 'test-token',
                'expiry_time': expiry_time.isoformat(),
                'account_id': '123456789012',
            }
            mock_fetcher.load_cached_credentials.return_value = expected_creds
            mock_fetcher.refresh_credentials.side_effect = Exception(
                "login down"
            )
            mock_fetcher_class.return_value = mock_fetcher

            local_now = mock.Mock(return_value=now)
            with mock.patch('botocore.credentials._local_now', local_now):
                provider = LoginProvider(
                    load_config=mock_load_config,
                    client_creator=mock_client_creator,
                    profile_name=profile_name,
                    token_cache=mock_token_cache,
                )
                credentials = provider.load()

                local_now.return_value = expiry_time
                frozen = credentials.get_frozen_credentials()

            assert frozen.access_key == expected_creds['access_key']
            assert frozen.secret_key == expected_creds['secret_key']
            assert frozen.token == expected_creds['token']
            mock_fetcher.load_cached_credentials.assert_called_once()
            mock_fetcher.refresh_credentials.assert_called_once()


def test_login_provider_feature_ids_in_context(client_context):
    profile_name = 'test-profile'
    mock_token_cache = mock.Mock()
    mock_client_creator = mock.Mock()
    mock_load_config = mock.Mock()

    mock_load_config.return_value = {
        'profiles': {
            profile_name: {
                'login_session': 'my-session',
                'region': 'us-east-1',
            }
        }
    }

    with (
        mock.patch('botocore.credentials.LoginCredentialsLoader'),
        mock.patch(
            'botocore.credentials.LoginCredentialFetcher'
        ) as mock_fetcher_class,
    ):
        mock_fetcher = mock.Mock()
        date_in_future = datetime.utcnow() + timedelta(hours=1)
        expiry_time = date_in_future.isoformat() + 'Z'
        expected_creds = {
            'access_key': 'test-access-key',
            'secret_key': 'test-secret-key',
            'token': 'test-token',
            'expiry_time': expiry_time,
            'account_id': '123456789012',
        }
        mock_fetcher.load_cached_credentials.return_value = expected_creds
        mock_fetcher_class.return_value = mock_fetcher

        provider = LoginProvider(
            token_cache=mock_token_cache,
            load_config=mock_load_config,
            profile_name=profile_name,
            client_creator=mock_client_creator,
        )

        result = provider.load()

        assert result is not None
        assert result.access_key == expected_creds['access_key']
        assert result.secret_key == expected_creds['secret_key']

        mock_fetcher.load_cached_credentials.assert_called_once()

        assert 'AC' in client_context.features
        assert 'AD' in client_context.features


@pytest.mark.parametrize(
    'error_type,expected_exception',
    [
        ('TOKEN_EXPIRED', botocore.exceptions.LoginRefreshTokenExpired),
        (
            'USER_CREDENTIALS_CHANGED',
            botocore.exceptions.LoginRefreshPasswordChanged,
        ),
        (
            'INSUFFICIENT_PERMISSIONS',
            botocore.exceptions.LoginInsufficientPermissions,
        ),
        ('UNKNOWN_ERROR', botocore.exceptions.LoginError),
    ],
)
def test_login_credential_fetcher_access_denied_errors(
    error_type, expected_exception
):
    token_loader = mock.Mock()
    client_creator = mock.Mock()

    base_token = {
        'clientId': 'test-client',
        'refreshToken': 'test-refresh-token',
        'dpopKey': SAMPLE_SIGN_IN_DPOP_PEM,
        'accessToken': {'expiresAt': '2020-01-01T00:00:00Z'},
    }
    token_loader.load_token.return_value = base_token

    client = mock.Mock()
    client.exceptions.AccessDeniedException = ClientError
    client.create_o_auth2_token.side_effect = ClientError(
        {'Error': {'Code': 'AccessDeniedException'}, 'error': error_type},
        'CreateOAuth2Token',
    )
    client_creator.return_value = client

    fetcher = credentials.LoginCredentialFetcher(
        session_name='test-session',
        token_loader=token_loader,
        client_creator=client_creator,
    )

    with pytest.raises(expected_exception):
        fetcher.refresh_credentials()


def _login_refresh_client():
    client = mock.Mock()
    client.exceptions.AccessDeniedException = ClientError
    client.create_o_auth2_token.return_value = {
        'tokenOutput': {
            'accessToken': {
                'accessKeyId': 'new-akid',
                'secretAccessKey': 'new-secret',
                'sessionToken': 'new-session-token',
            },
            'refreshToken': 'new-refresh-token',
            'expiresIn': 900,
        }
    }
    return client


def _expired_login_token(**extra):
    token = {
        'clientId': 'test-client',
        'refreshToken': 'test-refresh-token',
        'dpopKey': SAMPLE_SIGN_IN_DPOP_PEM,
        'accessToken': {
            'accessKeyId': 'old-akid',
            'secretAccessKey': 'old-secret',
            'sessionToken': 'old-session-token',
            'accountId': '123456789012',
            'expiresAt': '2020-01-01T00:00:00Z',
        },
    }
    token.update(extra)
    return token


def test_login_refresh_uses_sign_in_region():
    token_loader = mock.Mock()
    token_loader.load_token.return_value = _expired_login_token(
        signInRegion='eu-west-2'
    )
    client_creator = mock.Mock(return_value=_login_refresh_client())

    fetcher = credentials.LoginCredentialFetcher(
        session_name='test-session',
        token_loader=token_loader,
        client_creator=client_creator,
    )
    creds = fetcher.refresh_credentials()

    assert creds['access_key'] == 'new-akid'
    client_creator.assert_called_once_with(
        'signin', config=mock.ANY, region_name='eu-west-2'
    )
    # The region is preserved for the next refresh, not rewritten.
    saved_token = token_loader.save_token.call_args[0][1]
    assert saved_token['signInRegion'] == 'eu-west-2'


@pytest.mark.parametrize(
    'extra', [{}, {'signInRegion': ''}], ids=['missing', 'empty']
)
def test_login_refresh_without_sign_in_region(extra):
    token_loader = mock.Mock()
    token_loader.load_token.return_value = _expired_login_token(**extra)
    client_creator = mock.Mock(return_value=_login_refresh_client())

    fetcher = credentials.LoginCredentialFetcher(
        session_name='test-session',
        token_loader=token_loader,
        client_creator=client_creator,
    )
    fetcher.refresh_credentials()

    client_creator.assert_called_once_with('signin', config=mock.ANY)
    assert 'region_name' not in client_creator.call_args.kwargs


def _login_token(access_key):
    return {
        'clientId': 'test-client',
        'refreshToken': 'test-refresh-token',
        'dpopKey': SAMPLE_SIGN_IN_DPOP_PEM,
        'accessToken': {
            'accessKeyId': access_key,
            'secretAccessKey': 'test-secret-key',
            'sessionToken': 'test-session-token',
            'accountId': '123456789012',
            'expiresAt': '2099-01-01T00:00:00Z',
        },
    }


def test_login_credential_fetcher_refreshes_invalidated_token():
    token_loader = mock.Mock()
    token_loader.load_token.return_value = _login_token('OLD-ACCESS')
    client = mock.Mock()
    client.create_o_auth2_token.return_value = {
        'tokenOutput': {
            'accessToken': {
                'accessKeyId': 'NEW-ACCESS',
                'secretAccessKey': 'new-secret-key',
                'sessionToken': 'new-session-token',
            },
            'refreshToken': 'new-refresh-token',
            'expiresIn': 900,
        }
    }
    fetcher = credentials.LoginCredentialFetcher(
        session_name='test-session',
        token_loader=token_loader,
        client_creator=mock.Mock(return_value=client),
    )

    fetcher._invalidate('OLD-ACCESS')
    refreshed = fetcher.refresh_credentials()

    assert refreshed['access_key'] == 'NEW-ACCESS'
    client.create_o_auth2_token.assert_called_once()


def test_login_credential_fetcher_reuses_token_with_other_credentials():
    token_loader = mock.Mock()
    # Another process already refreshed the cached token.
    token_loader.load_token.return_value = _login_token('NEWER-ACCESS')
    client_creator = mock.Mock()
    fetcher = credentials.LoginCredentialFetcher(
        session_name='test-session',
        token_loader=token_loader,
        client_creator=client_creator,
    )

    fetcher._invalidate('OLD-ACCESS')
    refreshed = fetcher.refresh_credentials()

    assert refreshed['access_key'] == 'NEWER-ACCESS'
    client_creator.assert_not_called()


class FakeNonRecoverableRefreshError(Exception, RefreshNonRecoverableError):
    pass


@pytest.fixture
def mock_time():
    return mock.Mock(return_value=datetime(2021, 12, 10, tzinfo=timezone.utc))


@pytest.fixture
def refresher():
    return mock.Mock()


@pytest.fixture
def resilient_creds(mock_time, refresher):
    return _create_resilient_credentials(
        mock_time,
        refresher=refresher,
        expires_in=timedelta(minutes=-30),
    )


def _valid_metadata(
    mock_time, access_key='NEW-ACCESS', expires_in=timedelta(hours=1)
):
    return {
        'access_key': access_key,
        'secret_key': 'NEW-SECRET',
        'token': 'NEW-TOKEN',
        'expiry_time': (mock_time() + expires_in).isoformat(),
    }


def _create_resilient_credentials(
    mock_time,
    refresher=None,
    access_key='ORIGINAL-ACCESS',
    expires_in=timedelta(hours=1),
    method='iam-role',
    invalidate_provider_cache=None,
):
    if refresher is None:
        refresher = mock.Mock(return_value=_valid_metadata(mock_time))
    return credentials._ResilientRefreshableCredentials(
        access_key,
        'ORIGINAL-SECRET',
        'ORIGINAL-TOKEN',
        mock_time() + expires_in,
        refresher,
        method,
        time_fetcher=mock_time,
        invalidate_provider_cache=invalidate_provider_cache,
    )


def _create_deferred_resilient_credentials(
    mock_time, refresher, method='assume-role'
):
    return credentials._DeferredResilientRefreshableCredentials(
        refresher, method, time_fetcher=mock_time
    )


def _assert_refresh_boundary(
    creds, mock_time, issued_at, expires_in, refresh_window
):
    expiry_time = issued_at + expires_in

    mock_time.return_value = expiry_time - timedelta(
        seconds=refresh_window + 1
    )
    assert creds.refresh_needed() is False

    mock_time.return_value = expiry_time - timedelta(
        seconds=refresh_window - 1
    )
    assert creds.refresh_needed() is True


class TestRefreshWindows:
    def test_15_minute_credentials_do_not_refresh_immediately(self, mock_time):
        creds = _create_resilient_credentials(
            mock_time, expires_in=timedelta(minutes=15)
        )

        assert creds.refresh_needed() is False

    @pytest.mark.parametrize(
        'expires_in, expected_window',
        [
            (timedelta(minutes=20), 5 * 60),
            (timedelta(minutes=20, seconds=1), 15 * 60),
            (timedelta(minutes=89, seconds=59), 15 * 60),
            (timedelta(minutes=90), 60 * 60),
        ],
    )
    def test_advisory_window_tier_boundaries(
        self, mock_time, expires_in, expected_window
    ):
        issued_at = mock_time()
        creds = _create_resilient_credentials(mock_time, expires_in=expires_in)

        _assert_refresh_boundary(
            creds, mock_time, issued_at, expires_in, expected_window
        )

    def test_advisory_window_uses_lifetime_at_creation(self, mock_time):
        issued_at = mock_time()
        creds = _create_resilient_credentials(
            mock_time, expires_in=timedelta(hours=2)
        )

        mock_time.return_value = issued_at + timedelta(minutes=70)

        assert creds.refresh_needed() is True

    def test_advisory_window_recomputed_after_successful_refresh(
        self, mock_time
    ):
        issued_at = mock_time()
        refresher = mock.Mock(
            return_value=_valid_metadata(
                mock_time, expires_in=timedelta(hours=6)
            )
        )
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(seconds=30),
        )

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'NEW-ACCESS'
        _assert_refresh_boundary(
            creds, mock_time, issued_at, timedelta(hours=6), 60 * 60
        )

    def test_advisory_window_not_recomputed_on_refresh_failure(
        self, mock_time
    ):
        issued_at = mock_time()
        refresher = mock.Mock(side_effect=Exception("source down"))
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(minutes=30),
        )

        mock_time.return_value = issued_at + timedelta(minutes=16)
        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert creds.refresh_needed() is True


class TestRefreshBackoff:
    @pytest.mark.parametrize(
        'remaining_lifetime, expected_upper',
        [
            (timedelta(minutes=30), 600),
            (timedelta(minutes=20), 600),
            (timedelta(minutes=10), 300),
            (timedelta(minutes=5), 150),
            (timedelta(minutes=3), 90),
            (timedelta(minutes=1), 90),
            (timedelta(seconds=0), 90),
            (timedelta(minutes=-30), 90),
        ],
    )
    def test_refresh_backoff_scales_with_remaining_lifetime(
        self, mock_time, refresher, remaining_lifetime, expected_upper
    ):
        issued_at = mock_time()
        refresher.side_effect = Exception("source down")
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(hours=2),
        )
        mock_time.return_value = (
            issued_at + timedelta(hours=2) - remaining_lifetime
        )

        with mock.patch(
            'botocore.credentials.random.uniform', return_value=75
        ) as uniform:
            frozen = creds.get_frozen_credentials()

        uniform.assert_called_once_with(60, expected_upper)
        assert frozen.access_key == 'ORIGINAL-ACCESS'
        refresher.assert_called_once_with()

    def test_in_refresh_backoff_does_not_reread_blocked_until(self, mock_time):
        creds = _create_resilient_credentials(
            mock_time, expires_in=timedelta(hours=1)
        )
        creds._refresh_blocked_until = mock_time() + timedelta(minutes=5)

        def clear_backoff_during_read():
            creds._refresh_blocked_until = None
            return mock_time()

        creds._time_fetcher = clear_backoff_during_read

        assert creds._in_refresh_backoff() is True
        assert creds._refresh_blocked_until is None

    def test_failed_refresh_returns_cached_credentials(
        self, resilient_creds, refresher
    ):
        refresher.side_effect = Exception("source down")

        frozen = resilient_creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert frozen.secret_key == 'ORIGINAL-SECRET'
        assert frozen.token == 'ORIGINAL-TOKEN'
        assert refresher.call_count == 1

    def test_failed_refresh_is_not_retried_immediately(
        self, resilient_creds, refresher
    ):
        refresher.side_effect = Exception("source down")

        resilient_creds.get_frozen_credentials()
        assert refresher.call_count == 1

        frozen = resilient_creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

    def test_failed_refresh_is_retried_after_backoff(
        self, mock_time, refresher
    ):
        issued_at = mock_time()
        refresher.side_effect = [
            Exception("source down"),
            _valid_metadata(mock_time),
        ]
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(minutes=-30),
        )

        with mock.patch(
            'botocore.credentials.random.uniform', return_value=75
        ):
            frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

        mock_time.return_value = issued_at + timedelta(seconds=74)
        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

        mock_time.return_value = issued_at + timedelta(seconds=75)
        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'NEW-ACCESS'
        assert refresher.call_count == 2


class TestRefreshResponseValidation:
    def test_incomplete_refresh_response_returns_cached_credentials(
        self, mock_time
    ):
        refresher = mock.Mock(return_value={})
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(minutes=-30),
        )

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

    def test_expired_refresh_response_returns_cached_credentials(
        self, mock_time
    ):
        refresher = mock.Mock(
            return_value=_valid_metadata(
                mock_time, expires_in=timedelta(seconds=0)
            )
        )
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(minutes=-30),
        )

        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'ORIGINAL-ACCESS'

        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

    def test_malformed_expiry_returns_cached_credentials(self, mock_time):
        refresher = mock.Mock(
            return_value={
                'access_key': 'NEW-ACCESS',
                'secret_key': 'NEW-SECRET',
                'token': 'NEW-TOKEN',
                'expiry_time': 'not-a-datetime',
            }
        )
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(minutes=-30),
        )

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1


class TestDeferredResilientRefreshableCredentials:
    def test_refresh_needed_until_first_fetch(self, mock_time):
        refresher = mock.Mock(return_value=_valid_metadata(mock_time))
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        assert creds.refresh_needed() is True

        creds.get_frozen_credentials()

        assert creds.refresh_needed() is False

    def test_first_access_calls_refresher(self, mock_time):
        refresher = mock.Mock(return_value=_valid_metadata(mock_time))
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        refresher.assert_not_called()
        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'NEW-ACCESS'
        assert refresher.call_count == 1

    def test_expired_first_fetch_is_used_and_refreshes_on_next_access(
        self, mock_time
    ):
        refresher = mock.Mock(
            side_effect=[
                _valid_metadata(
                    mock_time,
                    access_key='FIRST-ACCESS',
                    expires_in=timedelta(seconds=-1),
                ),
                _valid_metadata(mock_time),
            ]
        )
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'FIRST-ACCESS'
        assert creds.refresh_needed() is True

        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'NEW-ACCESS'
        assert refresher.call_count == 2

    def test_first_fetch_failure_raises(self, mock_time):
        refresher = mock.Mock(side_effect=Exception("source down"))
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        with pytest.raises(Exception, match='source down'):
            creds.get_frozen_credentials()

    def test_incomplete_first_fetch_response_raises(self, mock_time):
        refresher = mock.Mock(return_value={})
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        with pytest.raises(
            botocore.exceptions.CredentialRetrievalError,
            match='Response did not contain',
        ):
            creds.get_frozen_credentials()

    @pytest.mark.parametrize(
        'expiry_time', ['not-a-datetime', '2021-12-10T01:00:00']
    )
    def test_malformed_first_fetch_expiry_raises(self, mock_time, expiry_time):
        refresher = mock.Mock(
            return_value={
                'access_key': 'NEW-ACCESS',
                'secret_key': 'NEW-SECRET',
                'token': 'NEW-TOKEN',
                'expiry_time': expiry_time,
            }
        )
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        # The cache is empty and the initial response has an invalid expiry.
        with pytest.raises(
            botocore.exceptions.CredentialRetrievalError,
            match='invalid expiry_time',
        ):
            creds.get_frozen_credentials()

        # No credentials were accepted, so the next access must retry the source.
        with pytest.raises(
            botocore.exceptions.CredentialRetrievalError,
            match='invalid expiry_time',
        ):
            creds.get_frozen_credentials()
        assert refresher.call_count == 2

    def test_after_first_fetch_failure_keeps_cached_credentials(
        self, mock_time
    ):
        issued_at = mock_time()
        refresher = mock.Mock(
            side_effect=[
                _valid_metadata(mock_time, access_key='FIRST-ACCESS'),
                Exception("source down"),
            ]
        )
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'FIRST-ACCESS'

        mock_time.return_value = issued_at + timedelta(hours=1)
        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'FIRST-ACCESS'
        assert refresher.call_count == 2

    def test_refresh_failure_after_initial_fetch_is_not_retried_immediately(
        self, mock_time
    ):
        issued_at = mock_time()
        refresher = mock.Mock(
            side_effect=[
                _valid_metadata(mock_time, access_key='FIRST-ACCESS'),
                Exception("source down"),
            ]
        )
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'FIRST-ACCESS'

        mock_time.return_value = issued_at + timedelta(hours=1)
        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'FIRST-ACCESS'
        assert refresher.call_count == 2

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'FIRST-ACCESS'
        assert refresher.call_count == 2

    def test_first_fetch_uses_computed_advisory_window(self, mock_time):
        issued_at = mock_time()
        refresher = mock.Mock(
            return_value=_valid_metadata(
                mock_time, expires_in=timedelta(hours=6)
            )
        )
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'NEW-ACCESS'
        assert refresher.call_count == 1
        _assert_refresh_boundary(
            creds, mock_time, issued_at, timedelta(hours=6), 60 * 60
        )


class TestNonRecoverableRefresh:
    @pytest.fixture
    def patched_jitter(self):
        with mock.patch('botocore.credentials.random.uniform', return_value=5):
            yield

    def _assert_reauth_raised(self, creds):
        with pytest.raises(
            FakeNonRecoverableRefreshError, match='reauth required'
        ):
            creds.get_frozen_credentials()

    def test_advisory_nonrecoverable_error_is_not_retried_within_ttl(
        self, mock_time, patched_jitter
    ):
        refresher = mock.Mock(
            side_effect=FakeNonRecoverableRefreshError("reauth required")
        )
        creds = _create_resilient_credentials(
            mock_time, refresher=refresher, expires_in=timedelta(seconds=90)
        )

        self._assert_reauth_raised(creds)
        assert refresher.call_count == 1

        self._assert_reauth_raised(creds)
        assert refresher.call_count == 1

    def test_mandatory_nonrecoverable_error_is_not_retried_within_ttl(
        self, mock_time, patched_jitter
    ):
        refresher = mock.Mock(
            side_effect=FakeNonRecoverableRefreshError("reauth required")
        )
        creds = _create_resilient_credentials(
            mock_time, refresher=refresher, expires_in=timedelta(seconds=30)
        )

        self._assert_reauth_raised(creds)
        assert refresher.call_count == 1

        self._assert_reauth_raised(creds)
        assert refresher.call_count == 1

    def test_advisory_nonrecoverable_error_is_retried_after_ttl_expires(
        self, mock_time, patched_jitter
    ):
        issued_at = mock_time()
        refresher = mock.Mock(
            side_effect=[
                FakeNonRecoverableRefreshError("reauth required"),
                _valid_metadata(mock_time),
            ]
        )
        creds = _create_resilient_credentials(
            mock_time, refresher=refresher, expires_in=timedelta(seconds=90)
        )

        self._assert_reauth_raised(creds)

        mock_time.return_value = issued_at + timedelta(seconds=6)
        frozen = creds.get_frozen_credentials()

        assert refresher.call_count == 2
        assert frozen.access_key == 'NEW-ACCESS'

    def test_deferred_nonrecoverable_error_is_not_retried_within_ttl(
        self, mock_time, patched_jitter
    ):
        refresher = mock.Mock(
            side_effect=FakeNonRecoverableRefreshError("reauth required")
        )
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        self._assert_reauth_raised(creds)
        assert refresher.call_count == 1

        self._assert_reauth_raised(creds)
        assert refresher.call_count == 1

    def test_deferred_nonrecoverable_error_retries_after_ttl_expires(
        self, mock_time, patched_jitter
    ):
        issued_at = mock_time()
        refresher = mock.Mock(
            side_effect=[
                FakeNonRecoverableRefreshError("reauth required"),
                _valid_metadata(mock_time),
            ]
        )
        creds = _create_deferred_resilient_credentials(mock_time, refresher)

        self._assert_reauth_raised(creds)
        self._assert_reauth_raised(creds)
        assert refresher.call_count == 1

        mock_time.return_value = issued_at + timedelta(seconds=6)
        frozen = creds.get_frozen_credentials()

        assert refresher.call_count == 2
        assert frozen.access_key == 'NEW-ACCESS'

    @pytest.mark.parametrize(
        'method',
        ['assume-role', 'assume-role-with-web-identity'],
    )
    def test_sts_nonrecoverable_error_is_not_retried_within_ttl(
        self, mock_time, patched_jitter, method
    ):
        refresher = mock.Mock(
            side_effect=ClientError(
                {
                    'Error': {
                        'Code': 'InvalidIdentityToken',
                        'Message': 'bad token',
                    }
                },
                'AssumeRole',
            )
        )
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(seconds=30),
            method=method,
        )

        with pytest.raises(ClientError, match='InvalidIdentityToken'):
            creds.get_frozen_credentials()

        with pytest.raises(ClientError, match='InvalidIdentityToken'):
            creds.get_frozen_credentials()

        assert refresher.call_count == 1

    def test_sts_nonrecoverable_codes_do_not_apply_to_non_sts_providers(
        self, mock_time
    ):
        refresher = mock.Mock(
            side_effect=ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
                'GetRoleCredentials',
            )
        )
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(seconds=30),
            method='sso',
        )

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

    def test_sso_expired_token_refresh_failure_is_nonrecoverable(
        self, mock_time, patched_jitter
    ):
        # The SSO token provider raises this when the cached token has expired
        # and CreateToken did not produce a new one. Only a new login fixes
        # that, so it must reach the caller rather than being absorbed by
        # static stability.
        refresher = mock.Mock(
            side_effect=TokenRetrievalError(
                provider='sso',
                error_msg='Token has expired and refresh failed',
            )
        )
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(seconds=30),
            method='sso',
        )

        with pytest.raises(TokenRetrievalError):
            creds.get_frozen_credentials()

        with pytest.raises(TokenRetrievalError):
            creds.get_frozen_credentials()

        assert refresher.call_count == 1

    def test_login_validation_error_raises_original_exception(self, mock_time):
        error = ClientError(
            {
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'The provided authorization grant is invalid.',
                }
            },
            'CreateOAuth2Token',
        )
        refresher = mock.Mock(side_effect=error)
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(seconds=30),
            method='login',
        )

        with pytest.raises(ClientError) as exc_info:
            creds.get_frozen_credentials()
        assert exc_info.value is error

    @pytest.mark.parametrize(
        'method, error_code',
        [
            ('assume-role', 'ValidationException'),
            ('login', 'TooManyRequestsError'),
        ],
    )
    def test_other_service_errors_use_refresh_backoff(
        self, mock_time, method, error_code
    ):
        refresher = mock.Mock(
            side_effect=ClientError(
                {'Error': {'Code': error_code, 'Message': 'service error'}},
                'RefreshCredentials',
            )
        )
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(seconds=30),
            method=method,
        )

        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'ORIGINAL-ACCESS'

        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1


class TestNonRecoverableProviderErrors:
    def test_sso_unauthorized_service_error_raises_nonrecoverable_error(
        self, mock_time
    ):
        token_loader = mock.Mock(
            return_value={
                'accessToken': 'some.sso.token',
                'expiresAt': '2099-10-18T22:26:40Z',
            }
        )
        client = mock.Mock()
        client.exceptions.UnauthorizedException = ClientError
        client.get_role_credentials.side_effect = ClientError(
            {'Error': {'Code': 'UnauthorizedException'}},
            'GetRoleCredentials',
        )
        fetcher = credentials.SSOCredentialFetcher(
            start_url='https://d-92671207e4.awsapps.com/start',
            sso_region='us-east-1',
            role_name='test-role',
            account_id='1234567890',
            client_creator=mock.Mock(return_value=client),
            token_loader=token_loader,
            cache={},
            time_fetcher=mock_time,
        )

        with pytest.raises(UnauthorizedSSOTokenError):
            fetcher.fetch_credentials()

    def test_sso_expired_cached_token_raises_nonrecoverable_error(
        self, mock_time
    ):
        token_loader = mock.Mock(
            return_value={
                'accessToken': 'some.sso.token',
                'expiresAt': '2018-10-18T22:26:40Z',
            }
        )
        client = mock.Mock()
        fetcher = credentials.SSOCredentialFetcher(
            start_url='https://d-92671207e4.awsapps.com/start',
            sso_region='us-east-1',
            role_name='test-role',
            account_id='1234567890',
            client_creator=mock.Mock(return_value=client),
            token_loader=token_loader,
            cache={},
            time_fetcher=mock_time,
        )

        with pytest.raises(UnauthorizedSSOTokenError):
            fetcher.fetch_credentials()
        client.get_role_credentials.assert_not_called()

    def test_sso_missing_cached_token_raises_nonrecoverable_error(self):
        loader = SSOTokenLoader(cache={})

        with pytest.raises(SSOTokenLoadError):
            loader('https://d-92671207e4.awsapps.com/start')

    @pytest.mark.parametrize(
        'token,error_msg',
        [
            (
                None,
                'Unable to load a existing login session for session test-session.',
            ),
            (
                {'accessToken': {}, 'refreshToken': 'refresh'},
                'missing one or more required fields',
            ),
        ],
    )
    def test_login_refresh_invalid_cached_token_raises_nonrecoverable_error(
        self, token, error_msg
    ):
        token_loader = mock.Mock()
        token_loader.load_token.return_value = token
        fetcher = credentials.LoginCredentialFetcher(
            session_name='test-session',
            token_loader=token_loader,
            client_creator=mock.Mock(),
        )

        with pytest.raises(
            LoginInvalidCachedTokenError,
            match=error_msg,
        ):
            fetcher.refresh_credentials()


class TestInvalidate:
    def test_matching_access_key_forces_refresh(self, mock_time):
        refresher = mock.Mock(return_value=_valid_metadata(mock_time))
        creds = _create_resilient_credentials(
            mock_time, refresher=refresher, expires_in=timedelta(hours=1)
        )

        creds._invalidate('ORIGINAL-ACCESS')
        frozen = creds.get_frozen_credentials()

        assert refresher.call_count == 1
        assert frozen.access_key == 'NEW-ACCESS'

    def test_mismatched_access_key_is_noop(self, mock_time):
        refresher = mock.Mock(return_value=_valid_metadata(mock_time))
        creds = _create_resilient_credentials(
            mock_time, refresher=refresher, expires_in=timedelta(hours=1)
        )

        creds._invalidate('DIFFERENT-ACCESS')
        frozen = creds.get_frozen_credentials()

        assert refresher.call_count == 0
        assert frozen.access_key == 'ORIGINAL-ACCESS'

    def test_provider_cache_invalidation_failure_still_refreshes(
        self, mock_time
    ):
        refresher = mock.Mock(return_value=_valid_metadata(mock_time))
        invalidate_provider_cache = mock.Mock(
            side_effect=RuntimeError("error")
        )
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(hours=1),
            invalidate_provider_cache=invalidate_provider_cache,
        )

        creds._invalidate('ORIGINAL-ACCESS')
        frozen = creds.get_frozen_credentials()

        invalidate_provider_cache.assert_called_once_with('ORIGINAL-ACCESS')
        assert refresher.call_count == 1
        assert frozen.access_key == 'NEW-ACCESS'

    def test_does_not_bypass_refresh_backoff(self, mock_time):
        issued_at = mock_time()
        refresher = mock.Mock(
            side_effect=[
                Exception("source down"),
                _valid_metadata(mock_time),
            ]
        )
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(minutes=-30),
        )

        frozen = creds.get_frozen_credentials()
        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

        creds._invalidate('ORIGINAL-ACCESS')
        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 1

        mock_time.return_value = issued_at + timedelta(minutes=11)
        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'NEW-ACCESS'
        assert refresher.call_count == 2

    def test_refresh_lock_held_skips_invalidation(self, mock_time):
        refresher = mock.Mock(return_value=_valid_metadata(mock_time))
        invalidate_provider_cache = mock.Mock()
        creds = _create_resilient_credentials(
            mock_time,
            refresher=refresher,
            expires_in=timedelta(hours=1),
            invalidate_provider_cache=invalidate_provider_cache,
        )

        assert creds._refresh_lock.acquire(False)
        try:
            creds._invalidate('ORIGINAL-ACCESS')
        finally:
            creds._refresh_lock.release()

        frozen = creds.get_frozen_credentials()

        assert frozen.access_key == 'ORIGINAL-ACCESS'
        assert refresher.call_count == 0
        invalidate_provider_cache.assert_not_called()


class TestProviderCacheInvalidation:
    @pytest.fixture
    def assume_role_load_config(self):
        return mock.Mock(
            return_value={
                'profiles': {
                    'development': {
                        'role_arn': 'arn:aws:iam::123456789012:role/test-role',
                        'source_profile': 'source',
                    },
                    'source': {
                        'aws_access_key_id': 'SOURCE-ACCESS',
                        'aws_secret_access_key': 'SOURCE-SECRET',
                        'aws_session_token': 'SOURCE-TOKEN',
                    },
                }
            }
        )

    @pytest.fixture
    def web_identity_load_config(self):
        return mock.Mock(
            return_value={
                'profiles': {
                    'development': {
                        'role_arn': 'arn:aws:iam::123456789012:role/test-role',
                        'web_identity_token_file': '/tmp/token',
                    }
                }
            }
        )

    @pytest.fixture
    def web_identity_token_loader_cls(self):
        token_loader = mock.Mock(return_value='OIDC-TOKEN')
        return mock.Mock(return_value=token_loader)

    @pytest.fixture
    def sso_start_url(self):
        return 'https://test.awsapps.com/start'

    @pytest.fixture
    def sso_load_config(self, sso_start_url):
        return mock.Mock(
            return_value={
                'profiles': {
                    'sso-profile': {
                        'sso_start_url': sso_start_url,
                        'sso_region': 'us-east-1',
                        'sso_role_name': 'Administrator',
                        'sso_account_id': '1234567890',
                    }
                }
            }
        )

    @pytest.fixture
    def future_expiration(self):
        return datetime(2099, 1, 1, tzinfo=timezone.utc)

    @pytest.fixture
    def sso_token_cache(self, sso_start_url, future_expiration):
        token_cache = {}
        SSOTokenLoader(cache=token_cache).save_token(
            sso_start_url,
            {
                'accessToken': 'ACCESS-TOKEN',
                'expiresAt': future_expiration.strftime(
                    '%Y-%m-%dT%H:%M:%SUTC'
                ),
            },
        )
        return token_cache

    def test_assume_role_refreshes_source_credentials(
        self, assume_role_load_config, future_expiration
    ):
        expiration = future_expiration
        client = mock.Mock()
        client.assume_role.side_effect = [
            {
                'Credentials': {
                    'AccessKeyId': 'OLD-ACCESS',
                    'SecretAccessKey': 'OLD-ACCESS-SECRET',
                    'SessionToken': 'OLD-ACCESS-TOKEN',
                    'Expiration': expiration,
                }
            },
            {
                'Credentials': {
                    'AccessKeyId': 'NEW-ACCESS',
                    'SecretAccessKey': 'NEW-ACCESS-SECRET',
                    'SessionToken': 'NEW-ACCESS-TOKEN',
                    'Expiration': expiration,
                }
            },
        ]
        client_creator = mock.Mock(return_value=client)
        provider = credentials.AssumeRoleProvider(
            assume_role_load_config,
            client_creator,
            cache={},
            profile_name='development',
        )

        creds = provider.load()
        first = creds.get_frozen_credentials()
        creds._invalidate('OLD-ACCESS')
        second = creds.get_frozen_credentials()

        assert first.access_key == 'OLD-ACCESS'
        assert second.access_key == 'NEW-ACCESS'
        assert client.assume_role.call_count == 2

    def test_web_identity_refreshes_source_credentials(
        self,
        web_identity_load_config,
        web_identity_token_loader_cls,
        future_expiration,
    ):
        expiration = future_expiration
        client = mock.Mock()
        client.assume_role_with_web_identity.side_effect = [
            {
                'Credentials': {
                    'AccessKeyId': 'OLD-ACCESS',
                    'SecretAccessKey': 'OLD-ACCESS-SECRET',
                    'SessionToken': 'OLD-ACCESS-TOKEN',
                    'Expiration': expiration,
                }
            },
            {
                'Credentials': {
                    'AccessKeyId': 'NEW-ACCESS',
                    'SecretAccessKey': 'NEW-ACCESS-SECRET',
                    'SessionToken': 'NEW-ACCESS-TOKEN',
                    'Expiration': expiration,
                }
            },
        ]
        client_creator = mock.Mock(return_value=client)
        provider = credentials.AssumeRoleWithWebIdentityProvider(
            load_config=web_identity_load_config,
            client_creator=client_creator,
            profile_name='development',
            cache={},
            token_loader_cls=web_identity_token_loader_cls,
        )

        creds = provider.load()
        first = creds.get_frozen_credentials()
        creds._invalidate('OLD-ACCESS')
        second = creds.get_frozen_credentials()

        assert first.access_key == 'OLD-ACCESS'
        assert second.access_key == 'NEW-ACCESS'
        assert client.assume_role_with_web_identity.call_count == 2
        web_identity_token_loader_cls.assert_called_once_with('/tmp/token')

    def test_sso_refreshes_source_credentials(
        self, sso_load_config, sso_token_cache, future_expiration
    ):
        expiration = future_expiration
        client = mock.Mock()
        client.get_role_credentials.side_effect = [
            {
                'roleCredentials': {
                    'accessKeyId': 'OLD-ACCESS',
                    'secretAccessKey': 'OLD-ACCESS-SECRET',
                    'sessionToken': 'OLD-ACCESS-TOKEN',
                    'expiration': int(expiration.timestamp() * 1000),
                }
            },
            {
                'roleCredentials': {
                    'accessKeyId': 'NEW-ACCESS',
                    'secretAccessKey': 'NEW-ACCESS-SECRET',
                    'sessionToken': 'NEW-ACCESS-TOKEN',
                    'expiration': int(expiration.timestamp() * 1000),
                }
            },
        ]
        client_creator = mock.Mock(return_value=client)
        provider = credentials.SSOProvider(
            load_config=sso_load_config,
            client_creator=client_creator,
            profile_name='sso-profile',
            cache={},
            token_cache=sso_token_cache,
        )

        creds = provider.load()
        first = creds.get_frozen_credentials()
        creds._invalidate('OLD-ACCESS')
        second = creds.get_frozen_credentials()

        assert first.access_key == 'OLD-ACCESS'
        assert second.access_key == 'NEW-ACCESS'
        assert client.get_role_credentials.call_count == 2

    def test_assume_role_refresh_fetches_new_credentials_from_source(
        self, assume_role_load_config
    ):
        now = datetime(2021, 12, 10, tzinfo=timezone.utc)
        local_now = mock.Mock(return_value=now)
        expiration = now + timedelta(hours=2)
        client = mock.Mock()
        client.assume_role.side_effect = [
            {
                'Credentials': {
                    'AccessKeyId': 'OLD-ACCESS',
                    'SecretAccessKey': 'OLD-ACCESS-SECRET',
                    'SessionToken': 'OLD-ACCESS-TOKEN',
                    'Expiration': expiration,
                }
            },
            {
                'Credentials': {
                    'AccessKeyId': 'NEW-ACCESS',
                    'SecretAccessKey': 'NEW-ACCESS-SECRET',
                    'SessionToken': 'NEW-ACCESS-TOKEN',
                    'Expiration': expiration + timedelta(minutes=61),
                }
            },
        ]
        client_creator = mock.Mock(return_value=client)

        with mock.patch('botocore.credentials._local_now', local_now):
            provider = credentials.AssumeRoleProvider(
                assume_role_load_config,
                client_creator,
                cache={},
                profile_name='development',
            )
            creds = provider.load()
            first = creds.get_frozen_credentials()
            # Inside the 60-minute advisory window, but outside the
            # provider cache's 15-minute expiry window.
            local_now.return_value = now + timedelta(minutes=61)
            second = creds.get_frozen_credentials()

        assert first.access_key == 'OLD-ACCESS'
        assert second.access_key == 'NEW-ACCESS'
        assert client.assume_role.call_count == 2

    def test_assume_role_refresh_reuses_newer_provider_cached_credentials(
        self, assume_role_load_config
    ):
        now = datetime(2021, 12, 10, tzinfo=timezone.utc)
        local_now = mock.Mock(return_value=now)
        client = mock.Mock()
        client.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'OLD-ACCESS',
                'SecretAccessKey': 'OLD-ACCESS-SECRET',
                'SessionToken': 'OLD-ACCESS-TOKEN',
                'Expiration': now + timedelta(hours=2),
            }
        }
        client_creator = mock.Mock(return_value=client)
        cache = {}

        with mock.patch('botocore.credentials._local_now', local_now):
            provider = credentials.AssumeRoleProvider(
                assume_role_load_config,
                client_creator,
                cache=cache,
                profile_name='development',
            )
            creds = provider.load()
            creds.get_frozen_credentials()
            # Another process refreshed the shared cache in the meantime.
            cache_key = next(iter(cache))
            cache[cache_key] = {
                'Credentials': {
                    'AccessKeyId': 'NEWER-ACCESS',
                    'SecretAccessKey': 'NEWER-ACCESS-SECRET',
                    'SessionToken': 'NEWER-ACCESS-TOKEN',
                    'Expiration': now + timedelta(hours=3),
                }
            }
            local_now.return_value = now + timedelta(minutes=61)
            refreshed = creds.get_frozen_credentials()

        assert refreshed.access_key == 'NEWER-ACCESS'
        assert client.assume_role.call_count == 1

    def test_failed_assume_role_refresh_keeps_shared_cache_usable(
        self, assume_role_load_config
    ):
        now = datetime(2021, 12, 10, tzinfo=timezone.utc)
        local_now = mock.Mock(return_value=now)
        client = mock.Mock()
        client.assume_role.side_effect = [
            {
                'Credentials': {
                    'AccessKeyId': 'OLD-ACCESS',
                    'SecretAccessKey': 'OLD-ACCESS-SECRET',
                    'SessionToken': 'OLD-ACCESS-TOKEN',
                    'Expiration': now + timedelta(hours=2),
                }
            },
            EndpointConnectionError(endpoint_url='https://sts'),
        ]
        client_creator = mock.Mock(return_value=client)
        cache = {}

        with mock.patch('botocore.credentials._local_now', local_now):
            first = credentials.AssumeRoleProvider(
                assume_role_load_config,
                client_creator,
                cache=cache,
                profile_name='development',
            ).load()
            first.get_frozen_credentials()
            local_now.return_value = now + timedelta(minutes=61)
            # The refresh fails, so the first consumer keeps its credentials.
            assert first.get_frozen_credentials().access_key == 'OLD-ACCESS'
            second = credentials.AssumeRoleProvider(
                assume_role_load_config,
                client_creator,
                cache=cache,
                profile_name='development',
            ).load()
            # A second consumer can still use the still-valid cached ones.
            assert second.get_frozen_credentials().access_key == 'OLD-ACCESS'

        assert client.assume_role.call_count == 2


class CredentialRefreshClock:
    def __init__(self):
        self._now = datetime(2021, 12, 10, tzinfo=timezone.utc)

    def __call__(self):
        return self._now

    def advance(self, seconds):
        self._now += timedelta(seconds=seconds)


class CredentialRefreshLifecycleHarness:
    def __init__(self, test_case):
        self._test_case = test_case
        self._clock = CredentialRefreshClock()
        self._next_refresh_response = None
        self._next_lifetime_seconds = 3600
        self._refresh_count = 0
        self._refresh_backoff_seconds = test_case['given'].get(
            'refreshBackoffSeconds', 75
        )
        self._creds = self._create_credentials()

    def uniform_random(self, low, high):
        if low == 60 and 90 <= high <= 600:
            assert low <= self._refresh_backoff_seconds <= high
            return self._refresh_backoff_seconds
        if (low, high) == (1, 5):
            return 5
        raise AssertionError(
            f"Unexpected random.uniform call with bounds {(low, high)}"
        )

    def run_step(self, step):
        step_type = step['type']
        if step_type == 'advanceTime':
            self._clock.advance(step['seconds'])
            return None
        if step_type == 'invalidate':
            self._creds._invalidate(step['rejectedAccessKeyId'])
            return None
        if step_type != 'getCredentials':
            raise AssertionError(f"Unknown step type: {step_type}")

        self._next_lifetime_seconds = step.get('lifetimeSeconds', 3600)
        response = step.get('response')
        if response is None:
            self._next_refresh_response = None
        else:
            self._next_refresh_response = self._build_refresh_response(step)

        rate_limited = self._creds._in_refresh_backoff()
        had_cached_credentials = self._creds._frozen_credentials is not None
        previous_access_key = self._current_access_key()
        refresh_count = self._refresh_count
        try:
            frozen = self._creds.get_frozen_credentials()
        except Exception as error:
            source_contacted = self._refresh_count != refresh_count
            if self._next_refresh_response is not None and source_contacted:
                self._next_refresh_response = None
            return {
                'result': self._result_from_error(
                    error, had_cached_credentials
                ),
                'sourceContacted': source_contacted,
                'rateLimited': rate_limited,
            }

        source_contacted = self._refresh_count != refresh_count
        if self._next_refresh_response is not None and source_contacted:
            self._next_refresh_response = None
        result = 'cachedCredentials'
        if previous_access_key != frozen.access_key:
            result = 'newCredentials'
        actual = {
            'result': result,
            'sourceContacted': source_contacted,
            'rateLimited': rate_limited,
        }
        if result == 'newCredentials':
            actual['advisoryWindowSeconds'] = (
                self._creds._advisory_refresh_timeout
            )
        return actual

    def _create_credentials(self):
        given = self._test_case['given']
        state = given['cachedCredentials']
        if state == 'none':
            return credentials._DeferredResilientRefreshableCredentials(
                self._refresh_using,
                'iam-role',
                time_fetcher=self._clock,
            )

        return _create_resilient_credentials(
            self._clock,
            refresher=self._refresh_using,
            access_key=given.get('accessKeyId', 'ORIGINAL-ACCESS'),
            expires_in=self._seed_expiry_delta(state),
        )

    def _seed_expiry_delta(self, state):
        if state == 'valid':
            return timedelta(minutes=20)
        if state == 'advisory':
            return timedelta(minutes=4)
        if state == 'mandatory':
            return timedelta(seconds=30)
        if state == 'expired':
            return timedelta(seconds=-30)
        raise AssertionError(f"Unknown cached credential state: {state}")

    def _refresh_using(self):
        if self._next_refresh_response is None:
            raise AssertionError(
                "Credential source was contacted unexpectedly"
            )
        self._refresh_count += 1
        return self._next_refresh_response()

    def _build_refresh_response(self, step):
        response_type = step['response']
        if response_type == 'freshCredentials':
            return self._fresh_credentials_response
        if response_type == 'staleCredentials':
            return self._stale_credentials_response
        if response_type == 'error':
            return self._recoverable_error_response
        if response_type == 'nonRecoverableError':
            return self._nonrecoverable_error_response
        raise AssertionError(f"Unknown refresh response: {response_type}")

    def _fresh_credentials_response(self):
        access_key = f'NEW-ACCESS-{self._refresh_count}'
        expiry_time = self._clock() + timedelta(
            seconds=self._next_lifetime_seconds
        )
        return {
            'access_key': access_key,
            'secret_key': 'NEW-SECRET',
            'token': 'NEW-TOKEN',
            'expiry_time': expiry_time.isoformat(),
        }

    def _stale_credentials_response(self):
        return {
            'access_key': f'STALE-ACCESS-{self._refresh_count}',
            'secret_key': 'STALE-SECRET',
            'token': 'STALE-TOKEN',
            'expiry_time': self._clock().isoformat(),
        }

    def _recoverable_error_response(self):
        raise Exception("source down")

    def _nonrecoverable_error_response(self):
        raise FakeNonRecoverableRefreshError("reauth required")

    def _current_access_key(self):
        if self._creds._frozen_credentials is None:
            return None
        return self._creds._frozen_credentials.access_key

    def _result_from_error(self, error, had_cached_credentials):
        if isinstance(error, RefreshNonRecoverableError):
            return 'nonRecoverableError'
        if not had_cached_credentials:
            return 'noCredentialsError'
        raise AssertionError(
            f"Unexpected exception for modeled lifecycle case: {error!r}"
        )


def _get_credential_refresh_test_id():
    return os.environ.get('BOTOCORE_TEST_ID')


def _load_credential_refresh_lifecycle_cases():
    test_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'credential_refresh',
        'credential-refresh-tests.json',
    )
    with open(test_dir, encoding='utf-8') as f:
        test_cases = json.load(f)

    requested_case_id = _get_credential_refresh_test_id()
    loaded_cases = []
    for test_case in test_cases:
        if (
            requested_case_id is not None
            and test_case['id'] != requested_case_id
        ):
            continue
        loaded_cases.append(test_case)
    return loaded_cases


def _credential_refresh_case_id(test_case):
    return f"{test_case['id']}: {test_case['documentation']}"


class TestCredentialRefreshLifecycle:
    @pytest.mark.parametrize(
        'test_case',
        _load_credential_refresh_lifecycle_cases(),
        ids=_credential_refresh_case_id,
    )
    def test_credential_refresh_lifecycle(self, test_case):
        if 'configuredAdvisoryWindowSeconds' in test_case['given']:
            pytest.skip(
                "Botocore does not support customer configuration of refresh windows."
            )
        harness = CredentialRefreshLifecycleHarness(test_case)
        with mock.patch(
            'botocore.credentials.random.uniform',
            side_effect=harness.uniform_random,
        ):
            for step in test_case['steps']:
                actual = harness.run_step(step)
                if actual is None:
                    continue
                for key, expected in step['expected'].items():
                    assert actual[key] == expected


class PausingRefresher:
    def __init__(self, response):
        self._response = response
        self.started = threading.Event()
        self.resume = threading.Event()
        self.call_count = 0

    def __call__(self):
        self.call_count += 1
        self.started.set()
        if not self.resume.wait(timeout=1):
            raise AssertionError("Timed out waiting to resume refresh")
        return self._response


class CredentialFetchThread(threading.Thread):
    def __init__(self, creds):
        super().__init__()
        self._creds = creds
        self.frozen_credentials = None
        self.error = None

    def run(self):
        try:
            self.frozen_credentials = self._creds.get_frozen_credentials()
        except Exception as error:
            self.error = error


class TestCredentialRefreshConcurrency:
    def test_concurrent_reader_gets_refreshed_frozen_credentials(
        self, mock_time
    ):
        refresher = mock.Mock(return_value=_valid_metadata(mock_time))
        creds = PausingResilientRefreshableCredentials(
            'ORIGINAL-ACCESS',
            'ORIGINAL-SECRET',
            'ORIGINAL-TOKEN',
            mock_time() - timedelta(seconds=30),
            refresher,
            'iam-role',
            time_fetcher=mock_time,
        )
        creds.publish_started = threading.Event()
        creds.resume_publish = threading.Event()
        expected_credentials = credentials.ReadOnlyCredentials(
            'NEW-ACCESS', 'NEW-SECRET', 'NEW-TOKEN'
        )

        with ThreadPoolExecutor(max_workers=2) as executor:
            refresh = executor.submit(creds.get_frozen_credentials)
            try:
                assert creds.publish_started.wait(timeout=1)
                reader = executor.submit(creds.get_frozen_credentials)
                assert creds.refresh_needed()
            finally:
                creds.resume_publish.set()

            assert refresh.result(timeout=1) == expected_credentials
            assert reader.result(timeout=1) == expected_credentials

        refresher.assert_called_once_with()

    def test_advisory_refresh_concurrent_callers_reuse_cached_credentials(
        self, mock_time
    ):
        pausing_refresher = PausingRefresher(_valid_metadata(mock_time))
        refresher = mock.Mock(side_effect=pausing_refresher)
        creds = _create_resilient_credentials(
            mock_time, refresher, expires_in=timedelta(seconds=90)
        )
        refreshing_thread = CredentialFetchThread(creds)

        refreshing_thread.start()
        assert pausing_refresher.started.wait(timeout=1)

        cached = creds.get_frozen_credentials()

        assert cached.access_key == 'ORIGINAL-ACCESS'
        assert refreshing_thread.is_alive()

        pausing_refresher.resume.set()
        refreshing_thread.join(timeout=1)

        assert refreshing_thread.error is None
        assert refreshing_thread.frozen_credentials.access_key == 'NEW-ACCESS'
        assert refresher.call_count == 1

    @pytest.mark.parametrize(
        'expires_in',
        [timedelta(seconds=30), timedelta(seconds=-30)],
        ids=['mandatory', 'expired'],
    )
    def test_mandatory_refresh_concurrent_callers_wait_for_single_refresh(
        self, mock_time, expires_in
    ):
        pausing_refresher = PausingRefresher(_valid_metadata(mock_time))
        refresher = mock.Mock(side_effect=pausing_refresher)
        creds = _create_resilient_credentials(
            mock_time, refresher, expires_in=expires_in
        )
        refresh_owner_thread = CredentialFetchThread(creds)
        waiting_thread = CredentialFetchThread(creds)

        refresh_owner_thread.start()
        assert pausing_refresher.started.wait(timeout=1)

        waiting_thread.start()
        waiting_thread.join(timeout=0.05)
        assert waiting_thread.is_alive()

        pausing_refresher.resume.set()
        refresh_owner_thread.join(timeout=1)
        waiting_thread.join(timeout=1)

        assert refresh_owner_thread.error is None
        assert waiting_thread.error is None
        assert (
            refresh_owner_thread.frozen_credentials.access_key == 'NEW-ACCESS'
        )
        assert waiting_thread.frozen_credentials.access_key == 'NEW-ACCESS'
        assert refresher.call_count == 1
