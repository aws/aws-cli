# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json
import math
import os
import shutil
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from dateutil.tz import tzlocal

from botocore import UNSIGNED
from botocore.config import Config
from botocore.credentials import (
    AssumeRoleProvider,
    BotoProvider,
    CanonicalNameCredentialSourcer,
    ContainerProvider,
    CredentialResolver,
    Credentials,
    DeferredRefreshableCredentials,
    EnvProvider,
    InstanceMetadataProvider,
    JSONFileCache,
    ProcessProvider,
    ProfileProviderBuilder,
    ReadOnlyCredentials,
    SSOProvider,
    create_credential_resolver,
)
from botocore.exceptions import (
    CredentialRetrievalError,
    InfiniteLoopConfigError,
    InvalidConfigError,
)
from botocore.session import Session
from botocore.stub import Stubber
from botocore.tokens import SSOTokenProvider
from botocore.utils import (
    ContainerMetadataFetcher,
    InstanceMetadataFetcher,
    datetime2timestamp,
)
from tests import (
    BaseEnvVar,
    ClientHTTPStubber,
    IntegerRefresher,
    SessionHTTPStubber,
    StubbedSession,
    mock,
    random_chars,
    temporary_file,
    unittest,
)
from tests.functional.test_useragent import (
    get_captured_ua_strings,
    parse_registered_feature_ids,
)

TIME_IN_ONE_HOUR = datetime.now(tz=timezone.utc) + timedelta(hours=1)
TIME_IN_SIX_MONTHS = datetime.now(tz=timezone.utc) + timedelta(hours=4320)


class TestCredentialRefreshRaces(unittest.TestCase):
    def assert_consistent_credentials_seen(self, creds, func):
        collected = []
        self._run_threads(20, func, collected)
        for creds in collected:
            # During testing, the refresher uses it's current
            # refresh count as the values for the access, secret, and
            # token value.  This means that at any given point in time,
            # the credentials should be something like:
            #
            # ReadOnlyCredentials('1', '1', '1')
            # ReadOnlyCredentials('2', '2', '2')
            # ...
            # ReadOnlyCredentials('30', '30', '30')
            #
            # This makes it really easy to verify we see a consistent
            # set of credentials from the same time period.  We just
            # check if all the credential values are the same.  If
            # we ever see something like:
            #
            # ReadOnlyCredentials('1', '2', '1')
            #
            # We fail.  This is because we're using the access_key
            # from the first refresh ('1'), the secret key from
            # the second refresh ('2'), and the token from the
            # first refresh ('1').
            self.assertTrue(creds[0] == creds[1] == creds[2], creds)

    def assert_non_none_retrieved_credentials(self, func):
        collected = []
        self._run_threads(50, func, collected)
        for cred in collected:
            self.assertIsNotNone(cred)

    def _run_threads(self, num_threads, func, collected):
        threads = []
        for _ in range(num_threads):
            threads.append(threading.Thread(target=func, args=(collected,)))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def test_has_no_race_conditions(self):
        creds = IntegerRefresher(
            creds_last_for=2, advisory_refresh=1, mandatory_refresh=0
        )

        def _run_in_thread(collected):
            for _ in range(4000):
                frozen = creds.get_frozen_credentials()
                collected.append(
                    (frozen.access_key, frozen.secret_key, frozen.token)
                )

        start = time.time()
        self.assert_consistent_credentials_seen(creds, _run_in_thread)
        end = time.time()
        # creds_last_for = 2 seconds (from above)
        # So, for example, if execution time took 6.1 seconds, then
        # we should see a maximum number of refreshes being (6 / 2.0) + 1 = 4
        max_calls_allowed = math.ceil((end - start) / 2.0) + 1
        self.assertTrue(
            creds.refresh_counter <= max_calls_allowed,
            f"Too many cred refreshes, max: {max_calls_allowed}, actual: "
            f"{creds.refresh_counter}, time_delta: {end - start:.4f}",
        )

    def test_no_race_for_immediate_advisory_expiration(self):
        creds = IntegerRefresher(
            creds_last_for=1, advisory_refresh=1, mandatory_refresh=0
        )

        def _run_in_thread(collected):
            for _ in range(100):
                frozen = creds.get_frozen_credentials()
                collected.append(
                    (frozen.access_key, frozen.secret_key, frozen.token)
                )

        self.assert_consistent_credentials_seen(creds, _run_in_thread)

    def test_no_race_for_initial_refresh_of_deferred_refreshable(self):
        def get_credentials():
            expiry_time = (
                datetime.now(tzlocal()) + timedelta(hours=24)
            ).isoformat()
            return {
                'access_key': 'my-access-key',
                'secret_key': 'my-secret-key',
                'token': 'my-token',
                'expiry_time': expiry_time,
            }

        deferred_creds = DeferredRefreshableCredentials(
            get_credentials, 'fixed'
        )

        def _run_in_thread(collected):
            frozen = deferred_creds.get_frozen_credentials()
            collected.append(frozen)

        self.assert_non_none_retrieved_credentials(_run_in_thread)


class BaseAssumeRoleTest(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, 'config')
        self.environ['AWS_CONFIG_FILE'] = self.config_file
        self.environ['AWS_SHARED_CREDENTIALS_FILE'] = str(uuid.uuid4())

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        super().tearDown()

    def some_future_time(self):
        timeobj = datetime.now(tzlocal())
        return timeobj + timedelta(hours=24)

    def create_assume_role_response(self, credentials, expiration=None):
        if expiration is None:
            expiration = self.some_future_time()

        response = {
            'Credentials': {
                'AccessKeyId': credentials.access_key,
                'SecretAccessKey': credentials.secret_key,
                'SessionToken': credentials.token,
                'Expiration': expiration,
            },
            'AssumedRoleUser': {
                'AssumedRoleId': 'myroleid',
                'Arn': 'arn:aws:iam::1234567890:user/myuser',
            },
        }

        return response

    def create_random_credentials(self):
        return Credentials(
            f'fake-{random_chars(15)}',
            f'fake-{random_chars(35)}',
            f'fake-{random_chars(45)}',
            # The account_id gets resolved from the
            # Arn in create_assume_role_response().
            account_id='1234567890',
        )

    def assert_creds_equal(self, c1, c2):
        c1_frozen = c1
        if not isinstance(c1_frozen, ReadOnlyCredentials):
            c1_frozen = c1.get_frozen_credentials()
        c2_frozen = c2
        if not isinstance(c2_frozen, ReadOnlyCredentials):
            c2_frozen = c2.get_frozen_credentials()
        self.assertEqual(c1_frozen, c2_frozen)

    def write_config(self, config):
        with open(self.config_file, 'w') as f:
            f.write(config)


class TestAssumeRole(BaseAssumeRoleTest):
    def setUp(self):
        super().setUp()
        self.environ['AWS_ACCESS_KEY_ID'] = 'access_key'
        self.environ['AWS_SECRET_ACCESS_KEY'] = 'secret_key'

        self.metadata_provider = self.mock_provider(InstanceMetadataProvider)
        self.env_provider = self.mock_provider(EnvProvider)
        self.container_provider = self.mock_provider(ContainerProvider)
        self.mock_client_creator = mock.Mock(spec=Session.create_client)
        self.actual_client_region = None

        current_dir = os.path.dirname(os.path.abspath(__file__))
        credential_process = os.path.join(
            current_dir, 'utils', 'credentialprocess.py'
        )
        self.credential_process = f'{sys.executable} {credential_process}'

    def mock_provider(self, provider_cls):
        mock_instance = mock.Mock(spec=provider_cls)
        mock_instance.load.return_value = None
        mock_instance.METHOD = provider_cls.METHOD
        mock_instance.CANONICAL_NAME = provider_cls.CANONICAL_NAME
        return mock_instance

    def create_session(self, profile=None, sso_token_cache=None):
        session = StubbedSession(profile=profile)
        if not sso_token_cache:
            sso_token_cache = JSONFileCache(self.tempdir)
        # We have to set bogus credentials here or otherwise we'll trigger
        # an early credential chain resolution.
        sts = session.create_client(
            'sts',
            aws_access_key_id='spam',
            aws_secret_access_key='eggs',
        )
        self.mock_client_creator.return_value = sts
        assume_role_provider = AssumeRoleProvider(
            load_config=lambda: session.full_config,
            client_creator=self.mock_client_creator,
            cache={},
            profile_name=profile,
            credential_sourcer=CanonicalNameCredentialSourcer(
                [
                    self.env_provider,
                    self.container_provider,
                    self.metadata_provider,
                ]
            ),
            profile_provider_builder=ProfileProviderBuilder(
                session,
                sso_token_cache=sso_token_cache,
            ),
        )
        stubber = session.stub('sts')
        stubber.activate()

        component_name = 'credential_provider'
        resolver = session.get_component(component_name)
        available_methods = [p.METHOD for p in resolver.providers]
        replacements = {
            'env': self.env_provider,
            'iam-role': self.metadata_provider,
            'container-role': self.container_provider,
            'assume-role': assume_role_provider,
        }
        for name, provider in replacements.items():
            try:
                index = available_methods.index(name)
            except ValueError:
                # The provider isn't in the session
                continue

            resolver.providers[index] = provider

        session.register_component('credential_provider', resolver)
        return session, stubber

    def test_assume_role(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n\n'
            '[profile B]\n'
            'aws_access_key_id = abc123\n'
            'aws_secret_access_key = def456\n'
        )
        self.write_config(config)

        expected_creds = self.create_random_credentials()
        response = self.create_assume_role_response(expected_creds)
        session, stubber = self.create_session(profile='A')
        stubber.add_response('assume_role', response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)
        stubber.assert_no_pending_responses()

    def test_environment_credential_source(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'credential_source = Environment\n'
        )
        self.write_config(config)

        environment_creds = self.create_random_credentials()
        self.env_provider.load.return_value = environment_creds

        expected_creds = self.create_random_credentials()
        response = self.create_assume_role_response(expected_creds)
        session, stubber = self.create_session(profile='A')
        stubber.add_response('assume_role', response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)

        stubber.assert_no_pending_responses()
        self.assertEqual(self.env_provider.load.call_count, 1)

    def test_instance_metadata_credential_source(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'credential_source = Ec2InstanceMetadata\n'
        )
        self.write_config(config)

        metadata_creds = self.create_random_credentials()
        self.metadata_provider.load.return_value = metadata_creds

        expected_creds = self.create_random_credentials()
        response = self.create_assume_role_response(expected_creds)
        session, stubber = self.create_session(profile='A')
        stubber.add_response('assume_role', response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)

        stubber.assert_no_pending_responses()
        self.assertEqual(self.metadata_provider.load.call_count, 1)

    def test_container_credential_source(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'credential_source = EcsContainer\n'
        )
        self.write_config(config)

        container_creds = self.create_random_credentials()
        self.container_provider.load.return_value = container_creds

        expected_creds = self.create_random_credentials()
        response = self.create_assume_role_response(expected_creds)
        session, stubber = self.create_session(profile='A')
        stubber.add_response('assume_role', response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)

        stubber.assert_no_pending_responses()
        self.assertEqual(self.container_provider.load.call_count, 1)

    def test_invalid_credential_source(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'credential_source = CustomInvalidProvider\n'
        )
        self.write_config(config)

        with self.assertRaises(InvalidConfigError):
            session, _ = self.create_session(profile='A')
            session.get_credentials()

    def test_misconfigured_source_profile(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n'
            '[profile B]\n'
            'region = us-west-2\n'
        )
        self.write_config(config)

        with self.assertRaises(InvalidConfigError):
            session, _ = self.create_session(profile='A')
            session.get_credentials().get_frozen_credentials()

    def test_recursive_assume_role(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n\n'
            '[profile B]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleB\n'
            'source_profile = C\n\n'
            '[profile C]\n'
            'aws_access_key_id = abc123\n'
            'aws_secret_access_key = def456\n'
        )
        self.write_config(config)

        profile_b_creds = self.create_random_credentials()
        profile_b_response = self.create_assume_role_response(profile_b_creds)
        profile_a_creds = self.create_random_credentials()
        profile_a_response = self.create_assume_role_response(profile_a_creds)

        session, stubber = self.create_session(profile='A')
        stubber.add_response('assume_role', profile_b_response)
        stubber.add_response('assume_role', profile_a_response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, profile_a_creds)
        stubber.assert_no_pending_responses()

    def test_recursive_assume_role_stops_at_static_creds(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n\n'
            '[profile B]\n'
            'aws_access_key_id = abc123\n'
            'aws_secret_access_key = def456\n'
            'role_arn = arn:aws:iam::123456789:role/RoleB\n'
            'source_profile = C\n\n'
            '[profile C]\n'
            'aws_access_key_id = abc123\n'
            'aws_secret_access_key = def456\n'
        )
        self.write_config(config)

        profile_a_creds = self.create_random_credentials()
        profile_a_response = self.create_assume_role_response(profile_a_creds)
        session, stubber = self.create_session(profile='A')
        stubber.add_response('assume_role', profile_a_response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, profile_a_creds)
        stubber.assert_no_pending_responses()

    def test_infinitely_recursive_assume_role(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = A\n'
        )
        self.write_config(config)

        with self.assertRaises(InfiniteLoopConfigError):
            session, _ = self.create_session(profile='A')
            session.get_credentials()

    def test_process_source_profile(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n'
            '[profile B]\n'
            f'credential_process = {self.credential_process}\n'
        )
        self.write_config(config)

        expected_creds = self.create_random_credentials()
        response = self.create_assume_role_response(expected_creds)
        session, stubber = self.create_session(profile='A')
        stubber.add_response('assume_role', response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)
        stubber.assert_no_pending_responses()
        # Assert that the client was created with the credentials from the
        # credential process.
        self.assertEqual(self.mock_client_creator.call_count, 1)
        _, kwargs = self.mock_client_creator.call_args_list[0]
        expected_kwargs = {
            'aws_access_key_id': 'spam',
            'aws_secret_access_key': 'eggs',
            'aws_session_token': None,
        }
        self.assertEqual(kwargs, expected_kwargs)

    def test_web_identity_source_profile(self):
        token_path = os.path.join(self.tempdir, 'token')
        with open(token_path, 'w') as token_file:
            token_file.write('a.token')
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n'
            '[profile B]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleB\n'
            f'web_identity_token_file = {token_path}\n'
        )
        self.write_config(config)

        session, stubber = self.create_session(profile='A')

        identity_creds = self.create_random_credentials()
        identity_response = self.create_assume_role_response(identity_creds)
        stubber.add_response(
            'assume_role_with_web_identity',
            identity_response,
        )

        expected_creds = self.create_random_credentials()
        assume_role_response = self.create_assume_role_response(expected_creds)
        stubber.add_response('assume_role', assume_role_response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)
        stubber.assert_no_pending_responses()
        # Assert that the client was created with the credentials from the
        # assume role with web identity call.
        self.assertEqual(self.mock_client_creator.call_count, 1)
        _, kwargs = self.mock_client_creator.call_args_list[0]
        expected_kwargs = {
            'aws_access_key_id': identity_creds.access_key,
            'aws_secret_access_key': identity_creds.secret_key,
            'aws_session_token': identity_creds.token,
        }
        self.assertEqual(kwargs, expected_kwargs)

    def test_web_identity_source_profile_ignores_env_vars(self):
        token_path = os.path.join(self.tempdir, 'token')
        with open(token_path, 'w') as token_file:
            token_file.write('a.token')
        self.environ['AWS_ROLE_ARN'] = 'arn:aws:iam::123456789:role/RoleB'
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n'
            '[profile B]\n'
            f'web_identity_token_file = {token_path}\n'
        )
        self.write_config(config)

        session, _ = self.create_session(profile='A')
        # The config is split between the profile and the env, we
        # should only be looking at the profile so this should raise
        # a configuration error.
        with self.assertRaises(InvalidConfigError):
            session.get_credentials()

    def test_sso_source_profile_legacy(self):
        token_cache_key = 'f395038c92f1828cbb3991d2d6152d326b895606'
        cached_token = {
            'accessToken': 'a.token',
            'expiresAt': self.some_future_time().strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }
        temp_cache = JSONFileCache(self.tempdir)
        temp_cache[token_cache_key] = cached_token

        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n'
            '[profile B]\n'
            'sso_region = us-east-1\n'
            'sso_start_url = https://test.url/start\n'
            'sso_role_name = SSORole\n'
            'sso_account_id = 1234567890\n'
        )
        self.write_config(config)

        session, sts_stubber = self.create_session(profile='A')
        client_config = Config(
            region_name='us-east-1',
            signature_version=UNSIGNED,
        )
        sso_stubber = session.stub('sso', config=client_config)
        sso_stubber.activate()
        # The expiration needs to be in milliseconds
        expiration = datetime2timestamp(self.some_future_time()) * 1000
        sso_role_creds = self.create_random_credentials()
        sso_role_response = {
            'roleCredentials': {
                'accessKeyId': sso_role_creds.access_key,
                'secretAccessKey': sso_role_creds.secret_key,
                'sessionToken': sso_role_creds.token,
                'expiration': int(expiration),
            }
        }
        sso_stubber.add_response('get_role_credentials', sso_role_response)

        expected_creds = self.create_random_credentials()
        assume_role_response = self.create_assume_role_response(expected_creds)
        sts_stubber.add_response('assume_role', assume_role_response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)
        sts_stubber.assert_no_pending_responses()
        # Assert that the client was created with the credentials from the
        # SSO get role credentials response
        self.assertEqual(self.mock_client_creator.call_count, 1)
        _, kwargs = self.mock_client_creator.call_args_list[0]
        expected_kwargs = {
            'aws_access_key_id': sso_role_creds.access_key,
            'aws_secret_access_key': sso_role_creds.secret_key,
            'aws_session_token': sso_role_creds.token,
        }
        self.assertEqual(kwargs, expected_kwargs)

    def test_sso_source_profile(self):
        token_cache_key = '32096c2e0eff33d844ee6d675407ace18289357d'
        cached_token = {
            'accessToken': 'C',
            'expiresAt': TIME_IN_ONE_HOUR.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        temp_cache = JSONFileCache(self.tempdir)
        temp_cache[token_cache_key] = cached_token
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n'
            '[profile B]\n'
            'sso_session = C\n'
            'sso_role_name = SSORole\n'
            'sso_account_id = 1234567890\n'
            '[sso-session C]\n'
            'sso_region = us-east-1\n'
            'sso_start_url = https://test.url/start\n'
        )
        self.write_config(config)

        session, sts_stubber = self.create_session(
            profile='A', sso_token_cache=temp_cache
        )
        client_config = Config(
            region_name='us-east-1',
            signature_version=UNSIGNED,
        )
        sso_stubber = session.stub('sso', config=client_config)
        sso_stubber.activate()
        # The expiration needs to be in milliseconds
        expiration = datetime2timestamp(self.some_future_time()) * 1000
        sso_role_creds = self.create_random_credentials()
        sso_role_response = {
            'roleCredentials': {
                'accessKeyId': sso_role_creds.access_key,
                'secretAccessKey': sso_role_creds.secret_key,
                'sessionToken': sso_role_creds.token,
                'expiration': int(expiration),
            }
        }
        sso_stubber.add_response('get_role_credentials', sso_role_response)

        expected_creds = self.create_random_credentials()
        assume_role_response = self.create_assume_role_response(expected_creds)
        sts_stubber.add_response('assume_role', assume_role_response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)
        sts_stubber.assert_no_pending_responses()
        # Assert that the client was created with the credentials from the
        # SSO get role credentials response
        self.assertEqual(self.mock_client_creator.call_count, 1)
        _, kwargs = self.mock_client_creator.call_args_list[0]
        expected_kwargs = {
            'aws_access_key_id': sso_role_creds.access_key,
            'aws_secret_access_key': sso_role_creds.secret_key,
            'aws_session_token': sso_role_creds.token,
        }
        self.assertEqual(kwargs, expected_kwargs)

    def test_web_identity_credential_source_ignores_env_vars(self):
        token_path = os.path.join(self.tempdir, 'token')
        with open(token_path, 'w') as token_file:
            token_file.write('a.token')
        self.environ['AWS_ROLE_ARN'] = 'arn:aws:iam::123456789:role/RoleB'
        self.environ['AWS_WEB_IDENTITY_TOKEN_FILE'] = token_path
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'credential_source = Environment\n'
        )
        self.write_config(config)

        session, _ = self.create_session(profile='A')
        # We should not get credentials from web-identity configured in the
        # environment when the Environment credential_source is set.
        # There are no Environment credentials, so this should raise a
        # retrieval error.
        with self.assertRaises(CredentialRetrievalError):
            session.get_credentials()

    def test_self_referential_profile(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = A\n'
            'aws_access_key_id = abc123\n'
            'aws_secret_access_key = def456\n'
        )
        self.write_config(config)

        expected_creds = self.create_random_credentials()
        response = self.create_assume_role_response(expected_creds)
        session, stubber = self.create_session(profile='A')
        stubber.add_response('assume_role', response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)
        stubber.assert_no_pending_responses()

    def create_stubbed_sts_client(self, session):
        expected_creds = self.create_random_credentials()
        _original_create_client = session.create_client

        def create_client_sts_stub(service, *args, **kwargs):
            client = _original_create_client(service, *args, **kwargs)
            stub = Stubber(client)
            response = self.create_assume_role_response(expected_creds)
            self.actual_client_region = client.meta.region_name
            stub.add_response('assume_role', response)
            stub.activate()
            return client

        return create_client_sts_stub, expected_creds

    def test_assume_role_uses_correct_region(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n\n'
            '[profile B]\n'
            'aws_access_key_id = abc123\n'
            'aws_secret_access_key = def456\n'
        )
        self.write_config(config)
        session = Session(profile='A')
        # Verify that when we configure the session with a specific region
        # that we use that region when creating the sts client.
        session.set_config_variable('region', 'cn-north-1')

        create_client, expected_creds = self.create_stubbed_sts_client(session)
        session.create_client = create_client

        resolver = create_credential_resolver(session)
        provider = resolver.get_provider('assume-role')
        creds = provider.load()
        self.assert_creds_equal(creds, expected_creds)
        self.assertEqual(self.actual_client_region, 'cn-north-1')

    def test_assume_role_resolves_account_id(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::1234567890:role/RoleA\n'
            'source_profile = B\n\n'
            '[profile B]\n'
            'aws_access_key_id = foo\n'
            'aws_secret_access_key = bar\n'
        )
        self.write_config(config)
        expected_creds = self.create_random_credentials()
        response = self.create_assume_role_response(expected_creds)

        session, stubber = self.create_session(profile='A')
        stubber.add_response('assume_role', response)

        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)
        self.assertEqual(actual_creds.account_id, '1234567890')


class TestAssumeRoleWithWebIdentity(BaseAssumeRoleTest):
    def setUp(self):
        super().setUp()
        self.token_file = os.path.join(self.tempdir, 'token.jwt')
        self.write_token('totally.a.token')

    def write_token(self, token, path=None):
        if path is None:
            path = self.token_file
        with open(path, 'w') as f:
            f.write(token)

    def assert_session_credentials(self, expected_params, **kwargs):
        expected_creds = self.create_random_credentials()
        response = self.create_assume_role_response(expected_creds)
        session = StubbedSession(**kwargs)
        stubber = session.stub('sts')
        stubber.add_response(
            'assume_role_with_web_identity', response, expected_params
        )
        stubber.activate()
        actual_creds = session.get_credentials()
        self.assert_creds_equal(actual_creds, expected_creds)
        stubber.assert_no_pending_responses()

    def test_assume_role(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'role_session_name = sname\n'
            f'web_identity_token_file = {self.token_file}\n'
        )
        self.write_config(config)
        expected_params = {
            'RoleArn': 'arn:aws:iam::123456789:role/RoleA',
            'RoleSessionName': 'sname',
            'WebIdentityToken': 'totally.a.token',
        }
        self.assert_session_credentials(expected_params, profile='A')

    def test_assume_role_env_vars(self):
        config = '[profile B]\nregion = us-west-2\n'
        self.write_config(config)
        self.environ['AWS_ROLE_ARN'] = 'arn:aws:iam::123456789:role/RoleB'
        self.environ['AWS_WEB_IDENTITY_TOKEN_FILE'] = self.token_file
        self.environ['AWS_ROLE_SESSION_NAME'] = 'bname'

        expected_params = {
            'RoleArn': 'arn:aws:iam::123456789:role/RoleB',
            'RoleSessionName': 'bname',
            'WebIdentityToken': 'totally.a.token',
        }
        self.assert_session_credentials(expected_params)

    def test_assume_role_env_vars_do_not_take_precedence(self):
        config = (
            '[profile A]\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'role_session_name = aname\n'
            f'web_identity_token_file = {self.token_file}\n'
        )
        self.write_config(config)

        different_token = os.path.join(self.tempdir, str(uuid.uuid4()))
        self.write_token('totally.different.token', path=different_token)
        self.environ['AWS_ROLE_ARN'] = 'arn:aws:iam::123456789:role/RoleC'
        self.environ['AWS_WEB_IDENTITY_TOKEN_FILE'] = different_token
        self.environ['AWS_ROLE_SESSION_NAME'] = 'cname'

        expected_params = {
            'RoleArn': 'arn:aws:iam::123456789:role/RoleA',
            'RoleSessionName': 'aname',
            'WebIdentityToken': 'totally.a.token',
        }
        self.assert_session_credentials(expected_params, profile='A')


class TestProcessProvider(unittest.TestCase):
    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        credential_process = os.path.join(
            current_dir, 'utils', 'credentialprocess.py'
        )
        self.credential_process = f'{sys.executable} {credential_process}'
        self.environ = os.environ.copy()
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()

    def tearDown(self):
        self.environ_patch.stop()

    def test_credential_process(self):
        config = '[profile processcreds]\ncredential_process = %s\n'
        config = config % self.credential_process
        with temporary_file('w') as f:
            f.write(config)
            f.flush()
            self.environ['AWS_CONFIG_FILE'] = f.name

            credentials = Session(profile='processcreds').get_credentials()
            self.assertEqual(credentials.access_key, 'spam')
            self.assertEqual(credentials.secret_key, 'eggs')

    def test_credential_process_returns_error(self):
        config = (
            '[profile processcreds]\ncredential_process = %s --raise-error\n'
        )
        config = config % self.credential_process
        with temporary_file('w') as f:
            f.write(config)
            f.flush()
            self.environ['AWS_CONFIG_FILE'] = f.name

            session = Session(profile='processcreds')

            # This regex validates that there is no substring: b'
            # The reason why we want to validate that is that we want to
            # make sure that stderr is actually decoded so that in
            # exceptional cases the error is properly formatted.
            # As for how the regex works:
            # `(?!b').` is a negative lookahead, meaning that it will only
            # match if it is not followed by the pattern `b'`. Since it is
            # followed by a `.` it will match any character not followed by
            # that pattern. `((?!hede).)*` does that zero or more times. The
            # final pattern adds `^` and `$` to anchor the beginning and end
            # of the string so we can know the whole string is consumed.
            # Finally `(?s)` at the beginning makes dots match newlines so
            # we can handle a multi-line string.
            reg = r"(?s)^((?!b').)*$"
            with self.assertRaisesRegex(CredentialRetrievalError, reg):
                session.get_credentials()


class TestSTSRegional(BaseAssumeRoleTest):
    def add_assume_role_http_response(self, stubber):
        stubber.add_response(body=self._get_assume_role_body('AssumeRole'))

    def add_assume_role_with_web_identity_http_response(self, stubber):
        stubber.add_response(
            body=self._get_assume_role_body('AssumeRoleWithWebIdentity')
        )

    def _get_assume_role_body(self, method_name):
        expiration = self.some_future_time()
        body = (
            f'<{method_name}Response>'
            f'  <{method_name}Result>'
            '    <AssumedRoleUser>'
            '      <Arn>arn:aws:sts::0123456:user</Arn>'
            '      <AssumedRoleId>AKID:mysession-1567020004</AssumedRoleId>'
            '    </AssumedRoleUser>'
            '    <Credentials>'
            '      <AccessKeyId>AccessKey</AccessKeyId>'
            '      <SecretAccessKey>SecretKey</SecretAccessKey>'
            '      <SessionToken>SessionToken</SessionToken>'
            f'      <Expiration>{expiration}</Expiration>'
            '    </Credentials>'
            f'  </{method_name}Result>'
            f'</{method_name}Response>'
        )
        return body.encode('utf-8')

    def make_stubbed_client_call_to_region(self, session, stubber, region):
        ec2 = session.create_client('ec2', region_name=region)
        stubber.add_response(body=b'<DescribeRegionsResponse/>')
        ec2.describe_regions()

    def test_assume_role_uses_same_region_as_client(self):
        config = (
            '[profile A]\n'
            'sts_regional_endpoints = regional\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            'source_profile = B\n\n'
            '[profile B]\n'
            'aws_access_key_id = abc123\n'
            'aws_secret_access_key = def456\n'
        )
        self.write_config(config)

        session = Session(profile='A')
        with SessionHTTPStubber(session) as stubber:
            self.add_assume_role_http_response(stubber)
            # Make an arbitrary client and API call as we are really only
            # looking to make sure the STS assume role call uses the correct
            # endpoint.
            self.make_stubbed_client_call_to_region(
                session, stubber, 'us-west-2'
            )
            self.assertEqual(
                stubber.requests[0].url, 'https://sts.us-west-2.amazonaws.com/'
            )

    def test_assume_role_web_identity_uses_same_region_as_client(self):
        token_file = os.path.join(self.tempdir, 'token.jwt')
        with open(token_file, 'w') as f:
            f.write('some-token')
        config = (
            '[profile A]\n'
            'sts_regional_endpoints = regional\n'
            'role_arn = arn:aws:iam::123456789:role/RoleA\n'
            f'web_identity_token_file = {token_file}\n'
            'source_profile = B\n\n'
            '[profile B]\n'
            'aws_access_key_id = abc123\n'
            'aws_secret_access_key = def456\n'
        )
        self.write_config(config)
        # Make an arbitrary client and API call as we are really only
        # looking to make sure the STS assume role call uses the correct
        # endpoint.
        session = Session(profile='A')
        with SessionHTTPStubber(session) as stubber:
            self.add_assume_role_with_web_identity_http_response(stubber)
            # Make an arbitrary client and API call as we are really only
            # looking to make sure the STS assume role call uses the correct
            # endpoint.
            self.make_stubbed_client_call_to_region(
                session, stubber, 'us-west-2'
            )
            self.assertEqual(
                stubber.requests[0].url, 'https://sts.us-west-2.amazonaws.com/'
            )


class MockCache:
    """Mock for JSONFileCache to avoid touching files on disk"""

    def __init__(self, working_dir=None, dumps_func=None):
        self.working_dir = working_dir
        self.dumps_func = dumps_func

    def __contains__(self, cache_key):
        return True

    def __getitem__(self, cache_key):
        return {
            "startUrl": "https://test.awsapps.com/start",
            "region": "us-east-1",
            "accessToken": "access-token",
            "expiresAt": TIME_IN_ONE_HOUR.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "expiresIn": 3600,
            "clientId": "client-12345",
            "clientSecret": "client-secret",
            "registrationExpiresAt": TIME_IN_SIX_MONTHS.strftime(
                '%Y-%m-%dT%H:%M:%SZ'
            ),
            "refreshToken": "refresh-here",
        }

    def __delitem__(self, cache_key):
        pass


class SSOSessionTest(BaseEnvVar):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, 'config')
        self.environ['AWS_CONFIG_FILE'] = self.config_file
        self.access_key_id = 'ASIA123456ABCDEFG'
        self.secret_access_key = 'secret-key'
        self.session_token = 'session-token'

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        super().tearDown()

    def write_config(self, config):
        with open(self.config_file, 'w') as f:
            f.write(config)

    def test_token_chosen_from_provider(self):
        profile = (
            '[profile sso-test]\n'
            'region = us-east-1\n'
            'sso_session = sso-test-session\n'
            'sso_account_id = 12345678901234\n'
            'sso_role_name = ViewOnlyAccess\n'
            '\n'
            '[sso-session sso-test-session]\n'
            'sso_region = us-east-1\n'
            'sso_start_url = https://test.awsapps.com/start\n'
            'sso_registration_scopes = sso:account:access\n'
        )
        self.write_config(profile)

        session = Session(profile='sso-test')
        with SessionHTTPStubber(session) as stubber:
            self.add_credential_response(stubber)
            stubber.add_response()
            with mock.patch.object(
                SSOTokenProvider, 'DEFAULT_CACHE_CLS', MockCache
            ):
                c = session.create_client('s3')
                c.list_buckets()

        self.assert_valid_sso_call(
            stubber.requests[0],
            (
                'https://portal.sso.us-east-1.amazonaws.com/federation/credentials'
                '?role_name=ViewOnlyAccess&account_id=12345678901234'
            ),
            b'access-token',
        )
        self.assert_credentials_used(
            stubber.requests[1],
            self.access_key_id.encode('utf-8'),
            self.session_token.encode('utf-8'),
        )

    def test_mismatched_session_values(self):
        profile = (
            '[profile sso-test]\n'
            'region = us-east-1\n'
            'sso_session = sso-test-session\n'
            'sso_start_url = https://test2.awsapps.com/start\n'
            'sso_account_id = 12345678901234\n'
            'sso_role_name = ViewOnlyAccess\n'
            '\n'
            '[sso-session sso-test-session]\n'
            'sso_region = us-east-1\n'
            'sso_start_url = https://test.awsapps.com/start\n'
            'sso_registration_scopes = sso:account:access\n'
        )
        self.write_config(profile)

        session = Session(profile='sso-test')
        with pytest.raises(InvalidConfigError):
            c = session.create_client('s3')
            c.list_buckets()

    def test_missing_sso_session(self):
        profile = (
            '[profile sso-test]\n'
            'region = us-east-1\n'
            'sso_session = sso-test-session\n'
            'sso_start_url = https://test2.awsapps.com/start\n'
            'sso_account_id = 12345678901234\n'
            'sso_role_name = ViewOnlyAccess\n'
            '\n'
        )
        self.write_config(profile)

        session = Session(profile='sso-test')
        with pytest.raises(InvalidConfigError):
            c = session.create_client('s3')
            c.list_buckets()

    def assert_valid_sso_call(self, request, url, access_token):
        assert request.url == url
        assert 'x-amz-sso_bearer_token' in request.headers
        assert request.headers['x-amz-sso_bearer_token'] == access_token

    def assert_credentials_used(self, request, access_key, session_token):
        assert access_key in request.headers.get('Authorization')
        assert request.headers.get('X-Amz-Security-Token') == session_token

    def add_credential_response(self, stubber):
        response = {
            'roleCredentials': {
                'accessKeyId': self.access_key_id,
                'secretAccessKey': self.secret_access_key,
                'sessionToken': self.session_token,
                'expiration': TIME_IN_ONE_HOUR.timestamp() * 1000,
            }
        }
        stubber.add_response(body=json.dumps(response).encode('utf-8'))


class TestContextCredentials(unittest.TestCase):
    ACCESS_KEY = "access-key"
    SECRET_KEY = "secret-key"

    def _add_fake_creds(self, request, **kwargs):
        request.context.setdefault('signing', {})
        request.context['signing']['request_credentials'] = Credentials(
            self.ACCESS_KEY, self.SECRET_KEY
        )

    def test_credential_context_override(self):
        session = StubbedSession()
        with SessionHTTPStubber(session) as stubber:
            s3 = session.create_client('s3')
            s3.meta.events.register('before-sign', self._add_fake_creds)
            stubber.add_response()
            s3.list_buckets()
            request = stubber.requests[0]
            assert self.ACCESS_KEY in str(request.headers.get('Authorization'))


@pytest.mark.parametrize(
    "creds_env_var,creds_file_content,patches,expected_feature_id",
    [
        (
            'AWS_SHARED_CREDENTIALS_FILE',
            '[default]\naws_access_key_id = FAKEACCESSKEY\naws_secret_access_key = FAKESECRET',
            [
                patch(
                    "botocore.credentials.AssumeRoleProvider.load",
                    return_value=None,
                ),
                patch(
                    "botocore.credentials.EnvProvider.load", return_value=None
                ),
            ],
            'n',
        ),
        (
            'AWS_CONFIG_FILE',
            '[default]\naws_access_key_id = FAKEACCESSKEY\naws_secret_access_key = FAKESECRET',
            [
                patch(
                    "botocore.credentials.AssumeRoleProvider.load",
                    return_value=None,
                ),
                patch(
                    "botocore.credentials.EnvProvider.load", return_value=None
                ),
                patch(
                    "botocore.credentials.SharedCredentialProvider.load",
                    return_value=None,
                ),
            ],
            'n',
        ),
    ],
)
def test_user_agent_has_file_based_feature_ids(
    creds_env_var,
    creds_file_content,
    patches,
    expected_feature_id,
    tmp_path,
    monkeypatch,
):
    credentials_file = tmp_path / "creds"
    credentials_file.write_text(creds_file_content)
    monkeypatch.setenv(creds_env_var, str(credentials_file))

    for patch_obj in patches:
        patch_obj.start()

    try:
        session = Session()
        client = session.create_client("s3", region_name="us-east-1")
        _assert_feature_ids_in_ua(client, expected_feature_id)
    finally:
        for patch_obj in patches:
            patch_obj.stop()


def _assert_feature_ids_in_ua(client, expected_feature_ids):
    """Helper to test feature IDs appear in user agent for multiple calls."""
    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response()
        http_stubber.add_response()
        client.list_buckets()
        client.list_buckets()

    ua_strings = get_captured_ua_strings(http_stubber)
    for ua_string in ua_strings:
        feature_list = parse_registered_feature_ids(ua_string)
        for expected_id in expected_feature_ids:
            assert expected_id in feature_list


@pytest.mark.parametrize(
    "config_content,env_vars,expected_source_features,expected_provider_feature",
    [
        # Test Case 1: Assume Role with source profile
        (
            '''[profile assume-role-test]
role_arn = arn:aws:iam::123456789012:role/test-role
source_profile = base

[profile base]
aws_access_key_id = FAKEACCESSKEY
aws_secret_access_key = FAKESECRET''',
            {},
            [
                'n',  # CREDENTIALS_PROFILE
                'o',  # CREDENTIALS_PROFILE_SOURCE_PROFILE
            ],
            'i',  # CREDENTIALS_STS_ASSUME_ROLE
        ),
        # Test Case 2: Assume Role with named provider
        (
            '''[profile assume-role-test]
role_arn = arn:aws:iam::123456789012:role/test-role
credential_source = Environment''',
            {
                'AWS_ACCESS_KEY_ID': 'FAKEACCESSKEY',
                'AWS_SECRET_ACCESS_KEY': 'FAKESECRET',
            },
            [
                'g',  # CREDENTIALS_ENV_VARS
                'p',  # CREDENTIALS_PROFILE_NAMED_PROVIDER
            ],
            'i',  # CREDENTIALS_STS_ASSUME_ROLE
        ),
    ],
)
def test_user_agent_has_assume_role_feature_ids(
    config_content,
    env_vars,
    expected_source_features,
    expected_provider_feature,
    tmp_path,
):
    session = _create_assume_role_session(config_content, tmp_path)

    # Set env vars if needed
    with patch.dict(os.environ, env_vars, clear=True):
        with SessionHTTPStubber(session) as stubber:
            s3 = session.create_client('s3', region_name='us-east-1')
            _add_assume_role_http_response(stubber, with_web_identity=False)
            stubber.add_response()
            stubber.add_response()
            s3.list_buckets()
            s3.list_buckets()

    ua_strings = get_captured_ua_strings(stubber)
    _assert_deferred_credential_feature_ids(
        ua_strings, expected_source_features, expected_provider_feature
    )


@pytest.mark.parametrize(
    "config_content,env_vars,expected_source_features,expected_provider_feature",
    [
        # Test Case 1: Assume Role with Web Identity through config profile
        (
            '''[profile assume-role-test]
role_arn = arn:aws:iam::123456789012:role/test-role
web_identity_token_file = {token_file}''',
            {},
            ['q'],  # CREDENTIALS_PROFILE_STS_WEB_ID_TOKEN
            'k',  # CREDENTIALS_STS_ASSUME_ROLE_WEB_ID
        ),
        # Test Case 2: Assume Role with Web Identity through env vars
        (
            '',
            {
                'AWS_ROLE_ARN': 'arn:aws:iam::123456789012:role/test-role',
                'AWS_WEB_IDENTITY_TOKEN_FILE': '{token_file}',
                'AWS_ROLE_SESSION_NAME': 'test-session',
            },
            ['h'],  # CREDENTIALS_ENV_VARS_STS_WEB_ID_TOKEN
            'k',  # CREDENTIALS_STS_ASSUME_ROLE_WEB_ID
        ),
    ],
)
def test_user_agent_has_assume_role_with_web_identity_feature_ids(
    config_content,
    env_vars,
    expected_source_features,
    expected_provider_feature,
    tmp_path,
):
    token_file = tmp_path / 'token.jwt'
    token_file.write_text('fake-jwt-token')
    if 'AWS_WEB_IDENTITY_TOKEN_FILE' in env_vars:
        env_vars['AWS_WEB_IDENTITY_TOKEN_FILE'] = str(token_file)
    elif config_content and 'web_identity_token_file' in config_content:
        config_content = config_content.replace(
            '{token_file}', str(token_file)
        )

    session = _create_assume_role_session(config_content, tmp_path)

    # Set env vars if needed
    with patch.dict(os.environ, env_vars, clear=True):
        with SessionHTTPStubber(session) as stubber:
            s3 = session.create_client('s3', region_name='us-east-1')
            _add_assume_role_http_response(stubber, with_web_identity=True)
            stubber.add_response()
            stubber.add_response()
            s3.list_buckets()
            s3.list_buckets()

    ua_strings = get_captured_ua_strings(stubber)
    _assert_deferred_credential_feature_ids(
        ua_strings, expected_source_features, expected_provider_feature
    )


def _create_assume_role_session(config_content, tmp_path):
    if config_content:
        config_file = tmp_path / 'config'
        config_file.write_text(config_content)
        session = Session(profile='assume-role-test')
        session.set_config_variable('config_file', str(config_file))
    else:
        session = Session()
    return session


def _add_assume_role_http_response(stubber, with_web_identity):
    """Add HTTP response for AssumeRole or AssumeRoleWithWebIdentity call with proper credentials"""
    expiration = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
        '%Y-%m-%dT%H:%M:%SZ'
    )
    method_name = (
        'AssumeRoleWithWebIdentity' if with_web_identity else 'AssumeRole'
    )
    body = (
        f'<{method_name}Response>'
        f'  <{method_name}Result>'
        '    <AssumedRoleUser>'
        '      <Arn>arn:aws:sts::123456789012:user</Arn>'
        '      <AssumedRoleId>AKID:test-session-123</AssumedRoleId>'
        '    </AssumedRoleUser>'
        '    <Credentials>'
        f'      <AccessKeyId>FAKEASSUMEROLEKEY</AccessKeyId>'
        f'      <SecretAccessKey>FAKEASSUMEROLSECRET</SecretAccessKey>'
        '      <SessionToken>FAKETOKEN</SessionToken>'
        f'      <Expiration>{expiration}</Expiration>'
        '    </Credentials>'
        f'  </{method_name}Result>'
        f'</{method_name}Response>'
    )
    stubber.add_response(body=body.encode('utf-8'))


def _assert_deferred_credential_feature_ids(
    ua_strings,
    expected_source_features,
    expected_provider_feature,
):
    """Helper to assert feature IDs for deferred credential provider tests"""
    assert len(ua_strings) == 3

    # Request to fetch credentials should only register feature ids for the credential source
    credential_source_feature_list = parse_registered_feature_ids(
        ua_strings[0]
    )
    for feature in expected_source_features:
        assert feature in credential_source_feature_list
    assert expected_provider_feature not in credential_source_feature_list

    # Original operation request should register feature ids for both the credential source and the provider
    for i in [1, 2]:
        operation_feature_list = parse_registered_feature_ids(ua_strings[i])
        for feature in expected_source_features:
            assert feature in operation_feature_list
        assert expected_provider_feature in operation_feature_list


class TestFeatureIdRegistered:
    def test_user_agent_has_env_vars_credentials_feature_id(
        self,
        monkeypatch,
        patched_session,
    ):
        env_vars = {
            'AWS_ACCESS_KEY_ID': 'FAKEACCESSKEY',
            'AWS_SECRET_ACCESS_KEY': 'FAKESECRET',
            'AWS_SESSION_TOKEN': 'FAKETOKEN',
        }
        for var, value in env_vars.items():
            monkeypatch.setenv(var, value)

        client = patched_session.create_client("s3", region_name="us-east-1")
        _assert_feature_ids_in_ua(client, ['g'])

    def test_user_agent_has_code_credentials_feature_id(self, patched_session):
        client = patched_session.create_client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id='FAKEACCESSKEY',
            aws_secret_access_key='FAKESECRET',
            aws_session_token='FAKETOKEN',
        )
        _assert_feature_ids_in_ua(client, ['e'])

    @patch("botocore.credentials.create_credential_resolver")
    @patch(
        "botocore.utils.InstanceMetadataFetcher.retrieve_iam_role_credentials"
    )
    def test_user_agent_has_imds_credentials_feature_id(
        self,
        mock_iam_fetcher,
        mock_get_credentials,
        patched_session,
    ):
        iam_role_fetcher = InstanceMetadataFetcher()
        imds_provider = InstanceMetadataProvider(iam_role_fetcher)
        credential_resolver = CredentialResolver([imds_provider])

        fake_credentials = {
            "role_name": "FAKEROLE",
            "access_key": "FAKEACCESSKEY",
            "secret_key": "FAKESECRET",
            "token": "FAKETOKEN",
            "expiry_time": "2099-01-01T00:00:00Z",
        }
        mock_iam_fetcher.return_value = fake_credentials
        mock_get_credentials.return_value = credential_resolver

        client = patched_session.create_client("s3", region_name="us-east-1")
        _assert_feature_ids_in_ua(client, ['0'])

    @patch("botocore.credentials.create_credential_resolver")
    @patch("botocore.credentials.ContainerMetadataFetcher.retrieve_full_uri")
    def test_user_agent_has_container_credentials_feature_id(
        self,
        mock_container_metadata_fetcher,
        mock_get_credentials,
        monkeypatch,
        patched_session,
    ):
        env_vars = {
            'AWS_CONTAINER_CREDENTIALS_FULL_URI': 'http://localhost/foo',
            'AWS_CONTAINER_AUTHORIZATION_TOKEN': 'Basic auth-token',
        }
        for var, value in env_vars.items():
            monkeypatch.setenv(var, value)

        container_metadata_fetcher = ContainerMetadataFetcher()
        container_provider = ContainerProvider(
            fetcher=container_metadata_fetcher
        )
        credential_resolver = CredentialResolver([container_provider])

        fake_credentials = {
            "AccessKeyId": "FAKEACCESSKEY",
            "SecretAccessKey": "FAKESECRET",
            "Token": "FAKETOKEN",
            "Expiration": "2099-01-01T00:00:00Z",
            "AccountId": "01234567890",
        }

        mock_container_metadata_fetcher.return_value = fake_credentials
        mock_get_credentials.return_value = credential_resolver

        client = patched_session.create_client("s3", region_name="us-east-1")
        _assert_feature_ids_in_ua(client, ['z'])

    @patch("botocore.credentials.create_credential_resolver")
    @patch("botocore.configloader.raw_config_parse")
    def test_user_agent_has_boto2_config_credentials_feature_id(
        self,
        mock_boto2_config,
        mock_get_credentials,
        patched_session,
    ):
        boto_provider = BotoProvider()
        credentials_resolver = CredentialResolver([boto_provider])

        fake_credentials = {
            "Credentials": {
                "aws_access_key_id": "FAKEACCESSKEY",
                "aws_secret_access_key": "FAKESECRETKEY",
            }
        }
        mock_boto2_config.return_value = fake_credentials
        mock_get_credentials.return_value = credentials_resolver

        client = patched_session.create_client("s3", region_name="us-east-1")
        _assert_feature_ids_in_ua(client, ['x'])

    @patch("botocore.credentials.create_credential_resolver")
    @patch("botocore.credentials.ProcessProvider._retrieve_credentials_using")
    @patch(
        "botocore.credentials.ProcessProvider._credential_process",
        return_value="Mock_credential_process",
    )
    def test_user_agent_has_process_provider_credentials_feature_id(
        self,
        _unused_mock_credentials_process,
        mock_process_config,
        mock_get_credentials,
        patched_session,
    ):
        process_provider = ProcessProvider(None, None)
        credentials_resolver = CredentialResolver([process_provider])

        fake_credentials = {
            'access_key': "FAKEACCESSKEY",
            'secret_key': "FAKESECRETKEY",
            'token': "FAKETOKEN",
        }
        mock_process_config.return_value = fake_credentials
        mock_get_credentials.return_value = credentials_resolver

        client = patched_session.create_client("s3", region_name="us-east-1")
        _assert_feature_ids_in_ua(client, ['v', 'w'])

    @patch("botocore.credentials.create_credential_resolver")
    @patch("botocore.credentials.CachedCredentialFetcher._load_from_cache")
    @patch("botocore.credentials.SSOProvider._load_sso_config")
    def test_user_agent_has_sso_legacy_credentials_feature_id(
        self,
        mock_load_sso_config,
        mock_cached_credential_fetcher,
        mock_get_credentials,
        patched_session,
    ):
        sso_provider = SSOProvider(None, None, None)
        credentials_resolver = CredentialResolver([sso_provider])
        mock_get_credentials.return_value = credentials_resolver

        fake_fetcher_kwargs = {
            'sso_start_url': "https://test.awsapps.com/start",
            'sso_region': "us-east-1",
            'sso_role_name': "Administrator",
            'sso_account_id': "1234567890",
        }

        fake_response = {
            "ProviderType": "sso",
            "Credentials": {
                "role_name": "FAKEROLE",
                "AccessKeyId": "FAKEACCESSKEY",
                "SecretAccessKey": "FAKESECRET",
                "SessionToken": "FAKETOKEN",
                "Expiration": "2099-01-01T00:00:00Z",
            },
        }
        mock_cached_credential_fetcher.return_value = fake_response
        mock_load_sso_config.return_value = fake_fetcher_kwargs

        client = patched_session.create_client("s3", region_name="us-east-1")
        _assert_feature_ids_in_ua(client, ['t', 'u'])

    @patch("botocore.credentials.create_credential_resolver")
    @patch("botocore.credentials.CachedCredentialFetcher._load_from_cache")
    @patch("botocore.credentials.SSOProvider._load_sso_config")
    def test_user_agent_has_sso_credentials_feature_id(
        self,
        mock_load_sso_config,
        mock_cached_credential_fetcher,
        mock_get_credentials,
        patched_session,
    ):
        sso_provider = SSOProvider(None, None, None)
        credentials_resolver = CredentialResolver([sso_provider])
        mock_get_credentials.return_value = credentials_resolver

        fake_fetcher_kwargs = {
            'sso_session': 'sample_test',  # Key difference from legacy SSO
            'sso_start_url': "https://test.awsapps.com/start",
            'sso_region': "us-east-1",
            'sso_role_name': "Administrator",
            'sso_account_id': "1234567890",
        }

        fake_response = {
            "ProviderType": "sso",
            "Credentials": {
                "role_name": "FAKEROLE",
                "AccessKeyId": "FAKEACCESSKEY",
                "SecretAccessKey": "FAKESECRET",
                "SessionToken": "FAKETOKEN",
                "Expiration": "2099-01-01T00:00:00Z",
            },
        }
        mock_cached_credential_fetcher.return_value = fake_response
        mock_load_sso_config.return_value = fake_fetcher_kwargs

        client = patched_session.create_client("s3", region_name="us-east-1")
        _assert_feature_ids_in_ua(client, ['r', 's'])
