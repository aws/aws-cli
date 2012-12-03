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
import botocore.credentials
import botocore.exceptions

metadata = {'instance-type': 't1.micro',
            'instance-id': 'i-c4bb5fba',
            'iam': {'info':
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
                                              u'Type': u'AWS-HMAC'}}},
            'local-hostname': 'domU-12-31-39-09-FA-87.compute-1.internal',
            'network': {'interfaces':
                        {'macs': {'12:31:39:09:fa:87':
                                  {'local-hostname': 'domU-12-31-39-09-FA-87.compute-1.internal',
                                   'public-hostname': 'ec2-107-22-36-64.compute-1.amazonaws.com',
                                   'public-ipv4s': '107.22.36.64',
                                   'mac': '12:31:39:09:fa:87',
                                   'owner-id': '419278470775',
                                   'local-ipv4s': '10.210.253.113',
                                   'device-number': '0'}}}},
            'hostname': 'domU-12-31-39-09-FA-87.compute-1.internal',
            'ami-id': 'ami-1b814f72',
            'kernel-id': 'aki-825ea7eb',
            'instance-action': 'none',
            'profile': 'default-paravirtual',
            'reservation-id': 'r-dd7d7fa4',
            'security-groups': 'foobar',
            'metrics': {'vhostmd': '<?xml version="1.0" encoding="UTF-8"?>'},
            'mac': '12:31:39:09:FA:87',
            'public-ipv4': '107.22.36.64',
            'ami-manifest-path': '(unknown)',
            'local-ipv4': '10.210.253.113',
            'placement': {'availability-zone': 'us-east-1d'},
            'ami-launch-index': '0',
            'public-hostname': 'ec2-107-22-36-64.compute-1.amazonaws.com',
            'public-keys': {'foobar': ['ssh-rsa FOOBAR']},
            'block-device-mapping': {'ami': '/dev/sda1', 'root': '/dev/sda1'}}


class EnvVarTest(unittest.TestCase):

    def test_envvar(self):
        if 'AWS_CONFIG_FILE' in os.environ:
            del os.environ['AWS_CONFIG_FILE']
        os.environ['BOTO_CONFIG'] = ''
        os.environ['AWS_ACCESS_KEY_ID'] = 'foo'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'bar'
        credentials = botocore.credentials.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'env'

    def test_config(self):
        if 'AWS_ACCESS_KEY_ID' in os.environ:
            del os.environ['AWS_ACCESS_KEY_ID']
        if 'AWS_SECRET_ACCESS_KEY' in os.environ:
            del os.environ['AWS_SECRET_ACCESS_KEY']
        os.environ['BOTO_CONFIG'] = ''
        os.environ['AWS_CONFIG_FILE'] = 'aws_config'
        credentials = botocore.credentials.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'config'
        assert credentials.profiles == ['default', 'personal']
        credentials = botocore.credentials.get_credentials('personal')
        assert credentials.access_key == 'fie'
        assert credentials.secret_key == 'baz'
        assert credentials.method == 'config'
        assert credentials.profiles == ['default', 'personal']

    def test_boto_config(self):
        if 'AWS_ACCESS_KEY_ID' in os.environ:
            del os.environ['AWS_ACCESS_KEY_ID']
        if 'AWS_SECRET_ACCESS_KEY' in os.environ:
            del os.environ['AWS_SECRET_ACCESS_KEY']
        if 'AWS_CONFIG_FILE' in os.environ:
            del os.environ['AWS_CONFIG_FILE']
        os.environ['BOTO_CONFIG'] = 'boto_config'
        credentials = botocore.credentials.get_credentials()
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'boto'

    def test_iam_role(self):
        if 'AWS_ACCESS_KEY_ID' in os.environ:
            del os.environ['AWS_ACCESS_KEY_ID']
        if 'AWS_SECRET_ACCESS_KEY' in os.environ:
            del os.environ['AWS_SECRET_ACCESS_KEY']
        if 'AWS_CONFIG_FILE' in os.environ:
            del os.environ['AWS_CONFIG_FILE']
        os.environ['BOTO_CONFIG'] = ''
        credentials = botocore.credentials.get_credentials(metadata=metadata)
        assert credentials.access_key == 'foo'
        assert credentials.secret_key == 'bar'
        assert credentials.method == 'iam-role'


if __name__ == "__main__":
    unittest.main()
