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
import os
import mock
import tempfile
import shutil
import json
import time
from uuid import uuid4

from botocore.session import Session
from botocore.exceptions import ClientError
from tests import BaseEnvVar, temporary_file, random_chars


S3_READ_POLICY_ARN = 'arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'


class TestCredentialPrecedence(BaseEnvVar):

    def setUp(self):
        super(TestCredentialPrecedence, self).setUp()

        # Set the config file to something that doesn't exist so
        # that we don't accidentally load a config.
        os.environ['AWS_CONFIG_FILE'] = '~/.aws/config-missing'

    def create_session(self, *args, **kwargs):
        """
        Create a new session with the given arguments. Additionally,
        this method will set the credentials file to the test credentials
        used by the following test cases.
        """
        kwargs['session_vars'] = {
            'credentials_file': (
                None, None,
                os.path.join(os.path.dirname(__file__), 'test-credentials'),
                None)
        }

        return Session(*args, **kwargs)

    def test_access_secret_vs_profile_env(self):
        # If all three are given, then the access/secret keys should
        # take precedence.
        os.environ['AWS_ACCESS_KEY_ID'] = 'env'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'env-secret'
        os.environ['AWS_DEFAULT_PROFILE'] = 'test'

        s = self.create_session()
        credentials = s.get_credentials()

        self.assertEqual(credentials.access_key, 'env')
        self.assertEqual(credentials.secret_key, 'env-secret')

    @mock.patch('botocore.credentials.Credentials')
    def test_access_secret_vs_profile_code(self, credentials_cls):
        # If all three are given, then the access/secret keys should
        # take precedence.
        s = self.create_session(profile='test')

        client = s.create_client('s3', aws_access_key_id='code',
                                 aws_secret_access_key='code-secret')

        credentials_cls.assert_called_with(
            access_key='code', secret_key='code-secret', token=mock.ANY)

    def test_profile_env_vs_code(self):
        # If the profile is set both by the env var and by code,
        # then the one set by code should take precedence.
        os.environ['AWS_DEFAULT_PROFILE'] = 'test'
        s = self.create_session(profile='default')

        credentials = s.get_credentials()

        self.assertEqual(credentials.access_key, 'default')
        self.assertEqual(credentials.secret_key, 'default-secret')

    @mock.patch('botocore.credentials.Credentials')
    def test_access_secret_env_vs_code(self, credentials_cls):
        # If the access/secret keys are set both as env vars and via
        # code, then those set by code should take precedence.
        os.environ['AWS_ACCESS_KEY_ID'] = 'env'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'secret'
        s = self.create_session()

        client = s.create_client('s3', aws_access_key_id='code',
                                 aws_secret_access_key='code-secret')

        credentials_cls.assert_called_with(
            access_key='code', secret_key='code-secret', token=mock.ANY)

    def test_access_secret_env_vs_profile_code(self):
        # If access/secret keys are set in the environment, but then a
        # specific profile is passed via code, then the access/secret
        # keys defined in that profile should take precedence over
        # the environment variables. Example:
        #
        # ``aws --profile dev s3 ls``
        #
        os.environ['AWS_ACCESS_KEY_ID'] = 'env'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'env-secret'
        s = self.create_session(profile='test')

        credentials = s.get_credentials()

        self.assertEqual(credentials.access_key, 'test')
        self.assertEqual(credentials.secret_key, 'test-secret')

    def test_honors_aws_shared_credentials_file_env_var(self):
        with temporary_file('w') as f:
            f.write('[default]\n'
                    'aws_access_key_id=custom1\n'
                    'aws_secret_access_key=custom2\n')
            f.flush()
            os.environ['AWS_SHARED_CREDENTIALS_FILE'] = f.name
            s = Session()
            credentials = s.get_credentials()

            self.assertEqual(credentials.access_key, 'custom1')
            self.assertEqual(credentials.secret_key, 'custom2')


class TestAssumeRoleCredentials(BaseEnvVar):
    def setUp(self):
        self.env_original = os.environ.copy()
        self.environ_copy = os.environ.copy()
        super(TestAssumeRoleCredentials, self).setUp()
        os.environ = self.environ_copy
        # The tests rely on manipulating AWS_CONFIG_FILE,
        # but we also need to make sure we don't accidentally
        # pick up the ~/.aws/credentials file either.
        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = str(uuid4())
        self.parent_session = Session()
        self.iam = self.parent_session.create_client('iam')
        self.sts = self.parent_session.create_client('sts')
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, 'config')

        # A role trust policy that allows the current account to call assume
        # role on itself.
        account_id = self.sts.get_caller_identity()['Account']
        self.role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::%s:root" % account_id
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }

    def tearDown(self):
        super(TestAssumeRoleCredentials, self).tearDown()
        shutil.rmtree(self.tempdir)
        os.environ = self.env_original.copy()

    def random_name(self):
        return 'botocoretest-' + random_chars(10)

    def create_role(self, policy_document, policy_arn=None):
        name = self.random_name()
        response = self.iam.create_role(
            RoleName=name,
            AssumeRolePolicyDocument=json.dumps(policy_document)
        )
        self.addCleanup(self.iam.delete_role, RoleName=name)
        if policy_arn:
            self.iam.attach_role_policy(RoleName=name, PolicyArn=policy_arn)
            self.addCleanup(
                self.iam.detach_role_policy, RoleName=name,
                PolicyArn=policy_arn
            )
        return response['Role']

    def create_user(self, policy_arns):
        name = self.random_name()
        user = self.iam.create_user(UserName=name)['User']
        self.addCleanup(self.iam.delete_user, UserName=name)

        for arn in policy_arns:
            self.iam.attach_user_policy(
                UserName=name,
                PolicyArn=arn
            )
            self.addCleanup(
                self.iam.detach_user_policy,
                UserName=name, PolicyArn=arn
            )

        return user

    def create_creds(self, user_name):
        creds = self.iam.create_access_key(UserName=user_name)['AccessKey']
        self.addCleanup(
            self.iam.delete_access_key,
            UserName=user_name, AccessKeyId=creds['AccessKeyId']
        )
        return creds

    def wait_for_assume_role(self, role_arn, access_key, secret_key,
                             token=None, attempts=30, delay=10,
                             success_delay=1,
                             num_success=4):
        for _ in range(num_success):
            creds = self._wait_for_assume_role(
                role_arn, access_key, secret_key, token, attempts, delay)
            time.sleep(success_delay)
        return creds

    def _wait_for_assume_role(self, role_arn, access_key, secret_key,
                              token, attempts, delay):
        # "Why not use the policy simulator?" you might ask. The answer is
        # that the policy simulator will return success far before you can
        # actually make the calls.
        client = self.parent_session.create_client(
            'sts', aws_access_key_id=access_key,
            aws_secret_access_key=secret_key, aws_session_token=token
        )
        attempts_remaining = attempts
        role_session_name = random_chars(10)
        while attempts_remaining > 0:
            attempts_remaining -= 1
            try:
                result = client.assume_role(
                    RoleArn=role_arn, RoleSessionName=role_session_name)
                return result['Credentials']
            except ClientError as e:
                code = e.response.get('Error', {}).get('Code')
                if code in ["InvalidClientTokenId", "AccessDenied"]:
                    time.sleep(delay)
                else:
                    raise

        raise Exception("Unable to assume role %s" % role_arn)

    def create_assume_policy(self, role_arn):
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Resource": role_arn,
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        name = self.random_name()
        response = self.iam.create_policy(
            PolicyName=name,
            PolicyDocument=json.dumps(policy_document)
        )
        self.addCleanup(
            self.iam.delete_policy, PolicyArn=response['Policy']['Arn']
        )
        return response['Policy']['Arn']

    def assert_s3_read_only_session(self, session):
        # Calls to S3 should succeed
        s3 = session.create_client('s3')
        s3.list_buckets()

        # Calls to other services should not
        iam = session.create_client('iam')
        try:
            iam.list_groups()
            self.fail("Expected call to list_groups to fail, but it passed.")
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code')
            if code != 'AccessDenied':
                raise

    def test_recursive_assume_role(self):
        # Create the final role, the one that will actually have access to s3
        final_role = self.create_role(self.role_policy, S3_READ_POLICY_ARN)

        # Create the role that can assume the final role
        middle_policy_arn = self.create_assume_policy(final_role['Arn'])
        middle_role = self.create_role(self.role_policy, middle_policy_arn)

        # Create a user that can only assume the middle-man role, and then get
        # static credentials for it.
        user_policy_arn = self.create_assume_policy(middle_role['Arn'])
        user = self.create_user([user_policy_arn])
        user_creds = self.create_creds(user['UserName'])

        # Setup the config file with the profiles we'll be using. For
        # convenience static credentials are placed here instead of putting
        # them in the credentials file.
        config = (
            '[default]\n'
            'aws_access_key_id = %s\n'
            'aws_secret_access_key = %s\n'
            '[profile middle]\n'
            'source_profile = default\n'
            'role_arn = %s\n'
            '[profile final]\n'
            'source_profile = middle\n'
            'role_arn = %s\n'
        )
        config = config % (
            user_creds['AccessKeyId'], user_creds['SecretAccessKey'],
            middle_role['Arn'], final_role['Arn']
        )
        with open(self.config_file, 'w') as f:
            f.write(config)

        # Wait for IAM permissions to propagate
        middle_creds = self.wait_for_assume_role(
            role_arn=middle_role['Arn'],
            access_key=user_creds['AccessKeyId'],
            secret_key=user_creds['SecretAccessKey'],
        )
        self.wait_for_assume_role(
            role_arn=final_role['Arn'],
            access_key=middle_creds['AccessKeyId'],
            secret_key=middle_creds['SecretAccessKey'],
            token=middle_creds['SessionToken'],
        )

        # Configure our credentials file to be THE credentials file
        os.environ['AWS_CONFIG_FILE'] = self.config_file

        self.assert_s3_read_only_session(Session(profile='final'))

    def test_assume_role_with_credential_source(self):
        # Create a role with read access to S3
        role = self.create_role(self.role_policy, S3_READ_POLICY_ARN)

        # Create a user that can assume the role and get static credentials
        # for it.
        user_policy_arn = self.create_assume_policy(role['Arn'])
        user = self.create_user([user_policy_arn])
        user_creds = self.create_creds(user['UserName'])

        # Setup the config file with the profile we'll be using.
        config = (
            '[profile assume]\n'
            'role_arn = %s\n'
            'credential_source = Environment\n'
        )
        config = config % role['Arn']
        with open(self.config_file, 'w') as f:
            f.write(config)

        # Wait for IAM permissions to propagate
        self.wait_for_assume_role(
            role_arn=role['Arn'],
            access_key=user_creds['AccessKeyId'],
            secret_key=user_creds['SecretAccessKey'],
        )

        # Setup the environment so that our new config file is THE config
        # file and add the expected credentials since we're using the
        # environment as our credential source.
        os.environ['AWS_CONFIG_FILE'] = self.config_file
        os.environ['AWS_SECRET_ACCESS_KEY'] = user_creds['SecretAccessKey']
        os.environ['AWS_ACCESS_KEY_ID'] = user_creds['AccessKeyId']

        self.assert_s3_read_only_session(Session(profile='assume'))
