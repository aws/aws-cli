#!/usr/bin/env
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import unittest
import os
import botocore.session
import botocore.exceptions

metadata = {'info':
            {'InstanceProfileArn': 'arn:aws:iam::444444444444:instance-profile/foobar',
             'InstanceProfileId': 'FOOBAR',
             'Code': 'Success',
             'LastUpdated': '2012-12-03T14:36:50Z'},
            'security-credentials': {'foobar':
                                     {'Code': 'Success',
                                      'LastUpdated': '2012-12-03T14:38:21Z',
                                      'AccessKeyId': 'foo',
                                      'SecretAccessKey': 'bar',
                                      'Token': 'foobar',
                                      'Expiration': '2012-12-03T20:48:03Z',
                                      'Type': 'AWS-HMAC'}}}


class EnvVarTest(unittest.TestCase):

    def setUp(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)
        config_path = os.path.join(os.path.dirname(__file__),
                                   'aws_config_nocreds')
        os.environ['AWS_CONFIG_FILE'] = config_path
        os.environ['BOTO_CONFIG'] = ''
        os.environ['AWS_ACCESS_KEY_ID'] = 'foo'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'bar'
        self.session = botocore.session.get_session()

    def test_envvar(self):
        credentials = self.session.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'env'

    def tearDown(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)


class CredentialsFileTest(unittest.TestCase):

    def setUp(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)
        config_path = os.path.join(os.path.dirname(__file__),
                                   'aws_credentials')
        self.bad_config_path = os.path.join(os.path.dirname(__file__),
                                            'no_aws_credentials')
        os.environ['AWS_CREDENTIAL_FILE'] = config_path
        os.environ['BOTO_CONFIG'] = ''
        self.session = botocore.session.get_session()

    def test_credentials_file(self):
        credentials = self.session.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'credentials-file'

    def test_bad_file(self):
        os.environ['AWS_CREDENTIAL_FILE'] = self.bad_config_path
        credentials = self.session.get_credentials()
        assert credentials == None

    def tearDown(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)


class ConfigTest(unittest.TestCase):

    def setUp(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)
        config_path = os.path.join(os.path.dirname(__file__), 'aws_config')
        os.environ['AWS_CONFIG_FILE'] = config_path
        os.environ['BOTO_CONFIG'] = ''
        self.session = botocore.session.get_session()

    def test_config(self):
        credentials = self.session.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'config'
        assert len(self.session.available_profiles) == 2
        assert 'default' in self.session.available_profiles
        assert 'personal' in self.session.available_profiles
        os.environ['BOTO_DEFAULT_PROFILE'] = 'personal'
        session = botocore.session.get_session()
        credentials = session.get_credentials()
        assert credentials.access_key == 'fie'
        assert credentials.secret_key == 'baz'
        assert credentials.method == 'config'
        assert len(session.available_profiles) == 2
        assert 'default' in session.available_profiles
        assert 'personal' in session.available_profiles

    def tearDown(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)


class BotoConfigTest(unittest.TestCase):

    def setUp(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)
        config_path = os.path.join(os.path.dirname(__file__), 'boto_config')
        os.environ['BOTO_CONFIG'] = config_path
        self.session = botocore.session.get_session()

    def test_boto_config(self):
        credentials = self.session.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'boto'

    def tearDown(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)


class IamRoleTest(unittest.TestCase):

    def setUp(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)
        os.environ['BOTO_CONFIG'] = ''
        self.session = botocore.session.get_session()

    def test_iam_role(self):
        credentials = self.session.get_credentials(metadata=metadata)
        assert credentials.method == 'iam-role'
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'

    def tearDown(self):
        for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'BOTO_CONFIG', 'AWS_CONFIG_FILE',
                    'AWS_CREDENTIAL_FILE'):
            os.environ.pop(var, None)


if __name__ == "__main__":
    unittest.main()
