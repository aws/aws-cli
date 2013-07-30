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
from tests.unit import BaseAWSCommandParamsTest
import os
import sys
import re
from six.moves import cStringIO
import httpretty

GET_PASSWORD_DATA_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<GetPasswordDataResponse xmlns="http://ec2.amazonaws.com/doc/2013-02-01/">
    <requestId>000000000000</requestId>
    <instanceId>i-12345678</instanceId>
    <timestamp>2013-07-27T18:29:23.000Z</timestamp>
    <passwordData>&#xd;
GWDnuoj/7pbMQkg125E8oGMUVCI+r98sGbFFl8SX+dEYxMZzz+byYwwjvyg8iSGKaLuLTIWatWopVu5cMWDKH65U4YFL2g3LqyajBrCFnuSE1piTeS/rPQpoSvBN5FGj9HWqNrglWAJgh9OZNSGgpEojBenL/0rwSpDWL7f/f52M5doYA6q+v0ygEoi1Wq6hcmrBfyA4seW1RlKgnUru5Y9oc1hFHi53E3b1EkjGqCsCemVUwumBj8uwCLJRaMcqrCxK1smtAsiSqk0Jk9jpN2vcQgnMPypEdmEEXyWHwq55fjy6ch+sqYcwumIL5QcFW2JQ5+XBEoFhC66gOsAXow==&#xd;
</passwordData>
</GetPasswordDataResponse>"""

GET_PASSWORD_OUTPUT_NO_DECRYPT = """{
    "InstanceId": "i-12345678", 
    "Timestamp": "2013-07-27T18:29:23.000Z", 
    "PasswordData": "GWDnuoj/7pbMQkg125E8oGMUVCI+r98sGbFFl8SX+dEYxMZzz+byYwwjvyg8iSGKaLuLTIWatWopVu5cMWDKH65U4YFL2g3LqyajBrCFnuSE1piTeS/rPQpoSvBN5FGj9HWqNrglWAJgh9OZNSGgpEojBenL/0rwSpDWL7f/f52M5doYA6q+v0ygEoi1Wq6hcmrBfyA4seW1RlKgnUru5Y9oc1hFHi53E3b1EkjGqCsCemVUwumBj8uwCLJRaMcqrCxK1smtAsiSqk0Jk9jpN2vcQgnMPypEdmEEXyWHwq55fjy6ch+sqYcwumIL5QcFW2JQ5+XBEoFhC66gOsAXow=="
}
"""

GET_PASSWORD_OUTPUT = """{
    "InstanceId": "i-12345678", 
    "Timestamp": "2013-07-27T18:29:23.000Z", 
    "PasswordData": "=mG8.r$o-s"
}
"""


class TestGetPasswordData(BaseAWSCommandParamsTest):

    prefix = 'ec2 get-password-data'

    def register_uri(self):
        httpretty.register_uri(httpretty.POST, re.compile('.*'),
                               body=GET_PASSWORD_DATA_RESPONSE)

    def test_no_priv_launch_key(self):
        save = sys.stdout
        sys.stdout = cStringIO()
        args = ' --instance-id i-12345678'
        cmdline = self.prefix + args
        result = {'InstanceId': 'i-12345678'}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        self.assertEqual(sys.stdout.getvalue(), GET_PASSWORD_OUTPUT_NO_DECRYPT)
        sys.stdout = save

    def test_nonexistent_priv_launch_key(self):
        args = ' --instance-id i-12345678 --priv-launch-key foo.pem'
        cmdline = self.prefix + args
        result = {}
        self.assert_params_for_cmd(cmdline, result, expected_rc=255)

    def test_priv_launch_key(self):
        save = sys.stdout
        sys.stdout = cStringIO()
        key_path = os.path.join(os.path.dirname(__file__),
                                'testcli.pem')
        args = ' --instance-id i-12345678 --priv-launch-key %s' % key_path
        cmdline = self.prefix + args
        result = {'InstanceId': 'i-12345678'}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        self.assertEqual(sys.stdout.getvalue(), GET_PASSWORD_OUTPUT)
        sys.stdout = save
