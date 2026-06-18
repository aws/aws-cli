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
import botocore.session
from botocore.exceptions import ProfileNotFound
from tests import mock, temporary_file, unittest


class TestSession(unittest.TestCase):
    def setUp(self):
        self.environ = {}
        self.env_patch = mock.patch('os.environ', self.environ)
        self.env_patch.start()
        self.session = botocore.session.get_session()

    def tearDown(self):
        self.env_patch.stop()

    def test_profile_precedence(self):
        self.environ['AWS_PROFILE'] = 'from_env_var'
        self.session.set_config_variable('profile', 'from_session_instance')
        self.assertEqual(self.session.profile, 'from_session_instance')

    def test_credentials_with_profile_precedence(self):
        self.environ['AWS_PROFILE'] = 'from_env_var'
        self.session.set_config_variable('profile', 'from_session_instance')
        try:
            self.session.get_credentials()
        except ProfileNotFound as e:
            self.assertNotIn('from_env_var', str(e))
            self.assertIn('from_session_instance', str(e))

    def test_session_profile_overrides_env_vars(self):
        # If the ".profile" attribute is set then the associated
        # creds for that profile take precedence over the environment
        # variables.
        with temporary_file('w') as f:
            # We test this by creating creds in two places,
            # env vars and a fake shared creds file.  We ensure
            # that if an explicit profile is set we pull creds
            # from the shared creds file.
            self.environ['AWS_ACCESS_KEY_ID'] = 'env_var_akid'
            self.environ['AWS_SECRET_ACCESS_KEY'] = 'env_var_sak'
            self.environ['AWS_SHARED_CREDENTIALS_FILE'] = f.name
            f.write(
                '[from_session_instance]\n'
                'aws_access_key_id=shared_creds_akid\n'
                'aws_secret_access_key=shared_creds_sak\n'
            )
            f.flush()
            self.session.set_config_variable(
                'profile', 'from_session_instance'
            )
            creds = self.session.get_credentials()
            self.assertEqual(creds.access_key, 'shared_creds_akid')
            self.assertEqual(creds.secret_key, 'shared_creds_sak')

    def test_profile_does_not_win_if_all_from_env_vars(self):
        # Creds should be pulled from the env vars because
        # if access_key/secret_key/profile are all specified on
        # the same "level", then the explicit creds take
        # precedence.
        with temporary_file('w') as f:
            self.environ['AWS_SHARED_CREDENTIALS_FILE'] = f.name
            self.environ['AWS_PROFILE'] = 'myprofile'
            # Even though we don't use the profile for credentials,
            # if you have a profile configured in any way
            # (env vars, set when creating a session, etc.) that profile
            # must exist.  So we need to create an empty profile
            # matching the value from AWS_PROFILE.
            f.write('[myprofile]\n')
            f.flush()
            self.environ['AWS_ACCESS_KEY_ID'] = 'env_var_akid'
            self.environ['AWS_SECRET_ACCESS_KEY'] = 'env_var_sak'

            creds = self.session.get_credentials()

            self.assertEqual(creds.access_key, 'env_var_akid')
            self.assertEqual(creds.secret_key, 'env_var_sak')

    def test_provides_available_regions_for_same_endpoint_prefix(self):
        regions = self.session.get_available_regions('s3')
        self.assertTrue(regions)

    def test_provides_available_regions_for_different_endpoint_prefix(self):
        regions = self.session.get_available_regions('elb')
        self.assertTrue(regions)

    def test_does_not_provide_regions_for_mismatch_service_name(self):
        # elb's endpoint prefix is elasticloadbalancing, but users should
        # still be using the service name when getting regions
        regions = self.session.get_available_regions('elasticloadbalancing')
        self.assertEqual(regions, [])
