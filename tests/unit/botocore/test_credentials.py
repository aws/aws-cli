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
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from dateutil.tz import tzlocal, tzutc

import botocore.exceptions
import botocore.session
from botocore import credentials
from botocore.compat import json
from botocore.configprovider import ConfigValueStore
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
    LoginError,
    MissingDependencyException,
)
from botocore.session import Session
from botocore.stub import Stubber
from botocore.utils import (
    ContainerMetadataFetcher,
    FileWebIdentityTokenLoader,
    SSOTokenLoader,
    datetime2timestamp,
)
from tests import (
    BaseEnvVar,
    IntegerRefresher,
    mock,
    requires_crt,
    skip_if_crt,
    skip_if_windows,
    temporary_file,
    unittest,
)

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
        # say the current time is now(), then we should need
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
        date_in_future = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(seconds=1000)
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
        date_in_future = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(seconds=1000)
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
        refresher = credentials.AssumeRoleWithWebIdentityCredentialFetcher(
            client_creator, self.load_token, self.role_arn, cache=cache
        )
        expected_response = self.get_expected_creds_from_response(
            cache[cache_key]
        )
        response = refresher.fetch_credentials()

        self.assertEqual(response, expected_response)
        client_creator.assert_not_called()

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
        date_in_future = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(seconds=1000)
        utc_timestamp = date_in_future.isoformat() + 'Z'

        cache_key = 'c29461feeacfbed43017d20612606ff76abc073d'
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
        date_in_future = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(seconds=1000)
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
        date_in_future = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(seconds=1000)
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

    def test_can_delete_existing_values(self):
        key_path = Path(os.path.join(self.tempdir, 'deleteme.json'))
        self.cache['deleteme'] = {'foo': 'bar'}
        assert self.cache['deleteme'] == {'foo': 'bar'}
        assert key_path.exists()

        del self.cache['deleteme']
        # Validate key removed
        with pytest.raises(KeyError):
            self.cache['deleteme']
        # Validate file removed
        assert not key_path.exists()

        self.cache['deleteme'] = {'bar': 'baz'}
        assert self.cache['deleteme'] == {'bar': 'baz'}

    def test_can_delete_missing_values(self):
        key_path = Path(os.path.join(self.tempdir, 'deleteme.json'))
        assert not key_path.exists()

        with pytest.raises(KeyError):
            del self.cache['deleteme']

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
        provider = credentials.ContainerProvider(environ, fetcher)

        with self.assertRaises(exception):
            provider.load()

    def test_http_error_propagated_on_refresh(self):
        # We should ensure errors are still propagated even in the
        # case of a failed refresh.
        environ = {
            'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI': '/latest/credentials?id=foo'
        }
        fetcher = mock.Mock(spec=credentials.ContainerMetadataFetcher)
        timeobj = datetime.now(tzlocal())
        expired_timestamp = (timeobj - timedelta(hours=23)).isoformat()
        http_exception = botocore.exceptions.MetadataRetrievalError
        raised_exception = botocore.exceptions.CredentialRetrievalError
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
        # Second time with a refresh should propagate an error.
        with self.assertRaises(raised_exception):
            creds.get_frozen_credentials()

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
        with temporary_file('w') as f:
            f.write('Basic auth-token')
            f.flush()
            environ = {
                'AWS_CONTAINER_CREDENTIALS_FULL_URI': 'http://localhost/foo',
                'AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE': f.name,
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

    def test_reloads_auth_token_from_file(self):
        with temporary_file('w') as f:
            f.write('First auth token')
            f.flush()
            environ = {
                'AWS_CONTAINER_CREDENTIALS_FULL_URI': 'http://localhost/foo',
                'AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE': f.name,
            }
            fetcher = self.create_fetcher()
            timeobj = datetime.now(tzlocal())
            fetcher.retrieve_full_uri.side_effect = [
                {
                    "AccessKeyId": "first_key",
                    "SecretAccessKey": "first_secret",
                    "Token": "first_token",
                    "Expiration": (timeobj + timedelta(seconds=1)).isoformat(),
                },
                {
                    "AccessKeyId": "second_key",
                    "SecretAccessKey": "second_secret",
                    "Token": "second_token",
                    "Expiration": (timeobj + timedelta(minutes=5)).isoformat(),
                },
            ]
            provider = credentials.ContainerProvider(environ, fetcher)
            creds = provider.load()
            fetcher.retrieve_full_uri.assert_called_with(
                'http://localhost/foo',
                headers={'Authorization': 'First auth token'},
            )
            time.sleep(1.5)
            f.seek(0)
            f.truncate()
            f.write('Second auth token')
            f.flush()
            creds._refresh()
            fetcher.retrieve_full_uri.assert_called_with(
                'http://localhost/foo',
                headers={'Authorization': 'Second auth token'},
            )

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


def _load_login_test_cases():
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

    @requires_crt()
    @pytest.mark.parametrize(
        "test_case", _load_login_test_cases(), ids=lambda x: x["documentation"]
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
                    load_config=load_config,
                    client_creator=lambda service_name, **kwargs: mock_client,
                    profile_name='signin',
                    token_cache=token_cache,
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


@requires_crt()
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
        mock.patch('botocore.credentials.LoginTokenLoader'),
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
            load_config=mock_load_config,
            client_creator=mock_client_creator,
            profile_name=profile_name,
            token_cache=mock_token_cache,
        )

        result = provider.load()

        assert result is not None
        assert result.access_key == expected_creds['access_key']
        assert result.secret_key == expected_creds['secret_key']

        mock_fetcher.load_cached_credentials.assert_called_once()

        assert 'AC' in client_context.features
        assert 'AD' in client_context.features


@requires_crt()
@pytest.mark.parametrize(
    'error_type,expected_exception',
    [
        ('TOKEN_EXPIRED', botocore.exceptions.LoginRefreshRequired),
        (
            'USER_CREDENTIALS_CHANGED',
            botocore.exceptions.LoginRefreshRequired,
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


@skip_if_crt()
def test_login_throws_exception_with_no_crt():
    profile_name = 'test-profile'
    mock_load_config = mock.Mock()
    mock_load_config.return_value = {
        'profiles': {
            profile_name: {
                'login_session': 'my-session',
                'region': 'us-east-1',
            }
        }
    }

    provider = LoginProvider(
        load_config=mock_load_config,
        client_creator=mock.Mock(),
        profile_name=profile_name,
        token_cache=mock.Mock(),
    )

    with pytest.raises(MissingDependencyException):
        provider.load()


@skip_if_crt()
def test_build_dpop_header_raises_without_crt():
    from botocore.credentials import _build_dpop_header

    with pytest.raises(MissingDependencyException):
        _build_dpop_header(None, 'https://example.com/token')


@requires_crt()
def test_dpop_jwt_signature_validation():
    import base64
    import hashlib

    from awscrt.crypto import EC, ECRawSignature, ECType

    from botocore.credentials import _build_dpop_header

    private_key = EC.new_generate(ECType.P_256)

    result = _build_dpop_header(private_key, 'https://example.com/token')
    parts = result.split('.')

    original_signing_input = f"{parts[0]}.{parts[1]}"
    message_hash = hashlib.sha256(original_signing_input.encode()).digest()

    signature_bytes = base64.urlsafe_b64decode(parts[2] + '==')
    r_bytes = signature_bytes[:32]
    s_bytes = signature_bytes[32:]
    der_signature = EC.encode_raw_signature(ECRawSignature(r_bytes, s_bytes))

    assert private_key.verify(message_hash, der_signature)


@requires_crt()
def test_build_dpop_header_structure():
    import base64
    import json

    from awscrt.crypto import EC, ECType

    from botocore.credentials import _build_dpop_header

    private_key = EC.new_generate(ECType.P_256)
    uri = 'https://example.com/token'
    test_timestamp = 1234567890
    test_uid = 'test-uid-123'

    result = _build_dpop_header(
        private_key, uri, ts=test_timestamp, uid=test_uid
    )
    parts = result.split('.')

    assert len(parts) == 3

    payload_json = base64.urlsafe_b64decode(parts[1] + '==').decode()
    payload = json.loads(payload_json)

    assert payload['htm'] == 'POST'
    assert payload['htu'] == uri
    assert payload['iat'] == test_timestamp
    assert payload['jti'] == test_uid
