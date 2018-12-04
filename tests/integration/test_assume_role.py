# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import shutil
import tempfile
import json
import time

from botocore.session import Session
from botocore.exceptions import ClientError

from awscli.testutils import unittest, aws, random_chars

S3_READ_POLICY_ARN = 'arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'


class TestAssumeRoleCredentials(unittest.TestCase):
    def setUp(self):
        super(TestAssumeRoleCredentials, self).setUp()
        self.environ = os.environ.copy()
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

    def random_name(self):
        return 'clitest-' + random_chars(10)

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
                             token=None, attempts=30, delay=10):
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

    def assert_s3_read_only_profile(self, profile_name):
        # Calls to S3 should succeed
        command = 's3api list-buckets --profile %s' % profile_name
        result = aws(command, env_vars=self.environ)
        self.assertEqual(result.rc, 0, result.stderr)

        # Calls to other services should not
        command = 'iam list-groups --profile %s' % profile_name
        result = aws(command, env_vars=self.environ)
        self.assertNotEqual(result.rc, 0, result.stdout)
        self.assertIn('AccessDenied', result.stderr)

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
        self.environ['AWS_CONFIG_FILE'] = self.config_file

        self.assert_s3_read_only_profile(profile_name='final')

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
        self.environ['AWS_CONFIG_FILE'] = self.config_file
        self.environ['AWS_SECRET_ACCESS_KEY'] = user_creds['SecretAccessKey']
        self.environ['AWS_ACCESS_KEY_ID'] = user_creds['AccessKeyId']

        self.assert_s3_read_only_profile(profile_name='assume')
