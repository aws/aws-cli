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
import uuid
import threading
import os
import math
import time
import mock
import tempfile
import shutil
from datetime import datetime, timedelta
import sys

from dateutil.tz import tzlocal
from botocore.exceptions import CredentialRetrievalError

from tests import (
    unittest, IntegerRefresher, BaseEnvVar, BaseSessionTest, random_chars
)
from tests import temporary_file, StubbedSession, SessionHTTPStubber
from botocore import UNSIGNED
from botocore.credentials import EnvProvider, ContainerProvider
from botocore.credentials import InstanceMetadataProvider
from botocore.credentials import Credentials, ReadOnlyCredentials
from botocore.credentials import AssumeRoleProvider, ProfileProviderBuilder
from botocore.credentials import CanonicalNameCredentialSourcer
from botocore.credentials import DeferredRefreshableCredentials
from botocore.credentials import create_credential_resolver
from botocore.credentials import JSONFileCache
from botocore.credentials import SSOProvider
from botocore.config import Config
from botocore.session import Session
from botocore.exceptions import InvalidConfigError, InfiniteLoopConfigError
from botocore.stub import Stubber
from botocore.utils import datetime2timestamp


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
            creds_last_for=2,
            advisory_refresh=1,
            mandatory_refresh=0
        )
        def _run_in_thread(collected):
            for _ in range(4000):
                frozen = creds.get_frozen_credentials()
                collected.append((frozen.access_key,
                                  frozen.secret_key,
                                  frozen.token))
        start = time.time()
        self.assert_consistent_credentials_seen(creds, _run_in_thread)
        end = time.time()
        # creds_last_for = 2 seconds (from above)
        # So, for example, if execution time took 6.1 seconds, then
        # we should see a maximum number of refreshes being (6 / 2.0) + 1 = 4
        max_calls_allowed = math.ceil((end - start) / 2.0) + 1
        self.assertTrue(creds.refresh_counter <= max_calls_allowed,
                        "Too many cred refreshes, max: %s, actual: %s, "
                        "time_delta: %.4f" % (max_calls_allowed,
                                              creds.refresh_counter,
                                              (end - start)))

    def test_no_race_for_immediate_advisory_expiration(self):
        creds = IntegerRefresher(
            creds_last_for=1,
            advisory_refresh=1,
            mandatory_refresh=0
        )
        def _run_in_thread(collected):
            for _ in range(100):
                frozen = creds.get_frozen_credentials()
                collected.append((frozen.access_key,
                                  frozen.secret_key,
                                  frozen.token))
        self.assert_consistent_credentials_seen(creds, _run_in_thread)

    def test_no_race_for_initial_refresh_of_deferred_refreshable(self):
        def get_credentials():
            expiry_time = (
                datetime.now(tzlocal()) + timedelta(hours=24)).isoformat()
            return {
                'access_key': 'my-access-key',
                'secret_key': 'my-secret-key',
                'token': 'my-token',
                'expiry_time': expiry_time
            }

        deferred_creds = DeferredRefreshableCredentials(
            get_credentials, 'fixed')

        def _run_in_thread(collected):
            frozen = deferred_creds.get_frozen_credentials()
            collected.append(frozen)

        self.assert_non_none_retrieved_credentials(_run_in_thread)


class BaseAssumeRoleTest(BaseEnvVar):
    def setUp(self):
        super(BaseAssumeRoleTest, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, 'config')
        self.environ['AWS_CONFIG_FILE'] = self.config_file
        self.environ['AWS_SHARED_CREDENTIALS_FILE'] = str(uuid.uuid4())

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        super(BaseAssumeRoleTest, self).tearDown()

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
                'Expiration': expiration
            },
            'AssumedRoleUser': {
                'AssumedRoleId': 'myroleid',
                'Arn': 'arn:aws:iam::1234567890:user/myuser'
            }
        }

        return response

    def create_random_credentials(self):
        return Credentials(
            'fake-%s' % random_chars(15),
            'fake-%s' % random_chars(35),
            'fake-%s' % random_chars(45)
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
        super(TestAssumeRole, self).setUp()
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
        self.credential_process = '%s %s' % (
            sys.executable, credential_process
        )

    def mock_provider(self, provider_cls):
        mock_instance = mock.Mock(spec=provider_cls)
        mock_instance.load.return_value = None
        mock_instance.METHOD = provider_cls.METHOD
        mock_instance.CANONICAL_NAME = provider_cls.CANONICAL_NAME
        return mock_instance

    def create_session(self, profile=None):
        session = StubbedSession(profile=profile)

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
            credential_sourcer=CanonicalNameCredentialSourcer([
                self.env_provider, self.container_provider,
                self.metadata_provider
            ]),
            profile_provider_builder=ProfileProviderBuilder(
                session,
                sso_token_cache=JSONFileCache(self.tempdir),
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
            'assume-role': assume_role_provider
        }
        for name, provider in replacements.items():
            try:
                index = available_methods.index(name)
            except ValueError:
                # The provider isn't in the session
                continue

            resolver.providers[index] = provider

        session.register_component(
            'credential_provider', resolver
        )
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
            'credential_process = %s\n' % self.credential_process
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
            'web_identity_token_file = %s\n' % token_path
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
            'web_identity_token_file = %s\n' % token_path
        )
        self.write_config(config)

        session, _ = self.create_session(profile='A')
        # The config is split between the profile and the env, we
        # should only be looking at the profile so this should raise
        # a configuration error.
        with self.assertRaises(InvalidConfigError):
            session.get_credentials()

    def test_sso_source_profile(self):
        token_cache_key = 'f395038c92f1828cbb3991d2d6152d326b895606'
        cached_token = {
            'accessToken': 'a.token',
            'expiresAt': self.some_future_time(),
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


class TestAssumeRoleWithWebIdentity(BaseAssumeRoleTest):
    def setUp(self):
        super(TestAssumeRoleWithWebIdentity, self).setUp()
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
            'assume_role_with_web_identity',
            response,
            expected_params
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
            'web_identity_token_file = %s\n'
        ) % self.token_file
        self.write_config(config)
        expected_params = {
            'RoleArn': 'arn:aws:iam::123456789:role/RoleA',
            'RoleSessionName': 'sname',
            'WebIdentityToken': 'totally.a.token',
        }
        self.assert_session_credentials(expected_params, profile='A')

    def test_assume_role_env_vars(self):
        config = (
            '[profile B]\n'
            'region = us-west-2\n'
        )
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
            'web_identity_token_file = %s\n'
        ) % self.token_file
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
        self.credential_process = '%s %s' % (
            sys.executable, credential_process
        )
        self.environ = os.environ.copy()
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()

    def tearDown(self):
        self.environ_patch.stop()

    def test_credential_process(self):
        config = (
            '[profile processcreds]\n'
            'credential_process = %s\n'
        )
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
            '[profile processcreds]\n'
            'credential_process = %s --raise-error\n'
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


class TestInstanceMetadataFetcher(BaseSessionTest):

    @mock.patch('botocore.httpsession.URLLib3Session.send')
    def test_imds_use_truncated_user_agent(self, send):
        self.session.user_agent_version = '24.0'
        resolver = create_credential_resolver(self.session)
        provider = resolver.get_provider('iam-role')
        provider.load()
        args, _ = send.call_args
        self.assertEqual(args[0].headers['User-Agent'], 'Botocore/24.0')
