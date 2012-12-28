#!/usr/bin/env
# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
            {u'InstanceProfileArn': u'arn:aws:iam::444444444444:instance-profile/foobar',
             u'InstanceProfileId': u'FOOBAR',
             u'Code': u'Success',
             u'LastUpdated': u'2012-12-03T14:36:50Z'},
            'security-credentials': {'foobar':
                                     {u'Code': u'Success',
                                      u'LastUpdated': u'2012-12-03T14:38:21Z',
                                      u'AccessKeyId': u'foo',
                                      u'SecretAccessKey': u'bar',
                                      u'Token': u'foobar',
                                      u'Expiration': u'2012-12-03T20:48:03Z',
                                      u'Type': u'AWS-HMAC'}}}


class EnvVarTest(unittest.TestCase):

    def test_envvar(self):
        config_path = os.path.join(os.path.dirname(__file__),
                                   'aws_config_nocreds')
        os.environ['AWS_CONFIG_FILE'] = config_path
        os.environ['BOTO_CONFIG'] = ''
        os.environ['AWS_ACCESS_KEY_ID'] = 'foo'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'bar'
        session = botocore.session.get_session()
        credentials = session.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'env'


class ConfigTest(unittest.TestCase):

    def test_config(self):
        if 'AWS_ACCESS_KEY_ID' in os.environ:
            del os.environ['AWS_ACCESS_KEY_ID']
        if 'AWS_SECRET_ACCESS_KEY' in os.environ:
            del os.environ['AWS_SECRET_ACCESS_KEY']
        os.environ['BOTO_CONFIG'] = ''
        config_path = os.path.join(os.path.dirname(__file__), 'aws_config')
        os.environ['AWS_CONFIG_FILE'] = config_path
        session = botocore.session.get_session()
        credentials = session.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'config'
        assert session.available_profiles == ['default', 'personal']
        session.profile = 'personal'
        credentials = session.get_credentials()
        assert credentials.access_key == 'fie'
        assert credentials.secret_key == 'baz'
        assert credentials.method == 'config'
        assert session.available_profiles == ['default', 'personal']


class BotoConfigTest(unittest.TestCase):

    def test_boto_config(self):
        if 'AWS_ACCESS_KEY_ID' in os.environ:
            del os.environ['AWS_ACCESS_KEY_ID']
        if 'AWS_SECRET_ACCESS_KEY' in os.environ:
            del os.environ['AWS_SECRET_ACCESS_KEY']
        if 'AWS_CONFIG_FILE' in os.environ:
            del os.environ['AWS_CONFIG_FILE']
        config_path = os.path.join(os.path.dirname(__file__), 'boto_config')
        os.environ['BOTO_CONFIG'] = config_path
        session = botocore.session.get_session()
        credentials = session.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'boto'


class IamRoleTest(unittest.TestCase):

    def test_iam_role(self):
        if 'AWS_ACCESS_KEY_ID' in os.environ:
            del os.environ['AWS_ACCESS_KEY_ID']
        if 'AWS_SECRET_ACCESS_KEY' in os.environ:
            del os.environ['AWS_SECRET_ACCESS_KEY']
        if 'AWS_CONFIG_FILE' in os.environ:
            del os.environ['AWS_CONFIG_FILE']
        os.environ['BOTO_CONFIG'] = ''
        session = botocore.session.get_session()
        credentials = session.get_credentials(metadata=metadata)
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'iam-role'


if __name__ == "__main__":
    unittest.main()
