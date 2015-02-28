#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest
import os


PASSWORD_DATA = ("GWDnuoj/7pbMQkg125E8oGMUVCI+r98sGbFFl8SX+dEYxMZzz+byYwwjvyg8i"
                 "SGKaLuLTIWatWopVu5cMWDKH65U4YFL2g3LqyajBrCFnuSE1piTeS/rPQpoSv"
                 "BN5FGj9HWqNrglWAJgh9OZNSGgpEojBenL/0rwSpDWL7f/f52M5doYA6q+v0y"
                 "gEoi1Wq6hcmrBfyA4seW1RlKgnUru5Y9oc1hFHi53E3b1EkjGqCsCemVUwumB"
                 "j8uwCLJRaMcqrCxK1smtAsiSqk0Jk9jpN2vcQgnMPypEdmEEXyWHwq55fjy6c"
                 "h+sqYcwumIL5QcFW2JQ5+XBEoFhC66gOsAXow==")


class TestGetPasswordData(BaseAWSCommandParamsTest):

    prefix = 'ec2 get-password-data'

    def setUp(self):
        super(TestGetPasswordData, self).setUp()
        self.parsed_response = {'InstanceId': 'i-12345678',
                                'Timestamp': '2013-07-27T18:29:23.000Z',
                                'PasswordData': PASSWORD_DATA}

    def test_no_priv_launch_key(self):
        args = ' --instance-id i-12345678'
        cmdline = self.prefix + args
        result = {'InstanceId': 'i-12345678'}
        output = self.assert_params_for_cmd(cmdline, result, expected_rc=0)[0]
        self.assertIn('"InstanceId": "i-12345678"', output)
        self.assertIn('"Timestamp": "2013-07-27T18:29:23.000Z"', output)
        self.assertIn('"PasswordData": "%s"' % PASSWORD_DATA, output)

    def test_nonexistent_priv_launch_key(self):
        args = ' --instance-id i-12345678 --priv-launch-key foo.pem'
        cmdline = self.prefix + args
        error_msg = self.assert_params_for_cmd(
            cmdline, expected_rc=255)[1]
        self.assertIn('priv-launch-key should be a path to '
                      'the local SSH private key file used '
                      'to launch the instance.\n', error_msg)

    def test_priv_launch_key(self):
        key_path = os.path.join(os.path.dirname(__file__),
                                'testcli.pem')
        args = ' --instance-id i-12345678 --priv-launch-key %s' % key_path
        cmdline = self.prefix + args
        result = {'InstanceId': 'i-12345678'}
        output = self.assert_params_for_cmd(cmdline, result, expected_rc=0)[0]
        self.assertIn('"InstanceId": "i-12345678"', output)
        self.assertIn('"Timestamp": "2013-07-27T18:29:23.000Z"', output)
        self.assertIn('"PasswordData": "=mG8.r$o-s"', output)
