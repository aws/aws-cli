#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import awscli.customizations.ec2bundleinstance

import datetime
import base64

from six.moves import cStringIO
import mock

class TestBundleInstance(BaseAWSCommandParamsTest):

    prefix = 'ec2 bundle-instance'

    Base64Policy = ('eyJleHBpcmF0aW9uIjogIjIwMTMtMDgtMTBUMDA6MDA6MDAiL'
                    'CJjb25kaXRpb25zIjogW3siYnVja2V0IjogIm15YnVja2V0In'
                    '0seyJhY2wiOiAiZWMyLWJ1bmRsZS1yZWFkIn0sWyJzdGFydHM'
                    'td2l0aCIsICIka2V5IiwgImZvb2JhciJdXX0=')
    PolicySignature = '0Wr6cr2Je//jinxyiuL4qMs51Lk='
    
    def setUp(self):
        super(TestBundleInstance, self).setUp()
        # This mocks out datetime.datetime.utcnow() so that it always
        # returns the same datetime object.  This is because this value
        # is embedded into the policy file that is generated and we
        # don't what the policy or its signature to change each time
        # we run the test.
        self.datetime_patcher = mock.patch.object(
            awscli.customizations.ec2bundleinstance.datetime, 'datetime',  
            mock.Mock(wraps=datetime.datetime)
        )
        mocked_datetime = self.datetime_patcher.start()
        mocked_datetime.utcnow.return_value = datetime.datetime(2013, 8, 9)


    def tearDown(self):
        super(TestBundleInstance, self).tearDown()
        self.datetime_patcher.stop
        
    def test_no_policy_provided(self):
        args = ' --instance-id i-12345678 --owner-akid AKIAIOSFODNN7EXAMPLE'
        args += ' --owner-sak wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        args += ' --bucket mybucket --prefix foobar'
        args_list = (self.prefix + args).split()
        result =  {'InstanceId': 'i-12345678',
                   'Storage.S3.Bucket': 'mybucket',
                   'Storage.S3.Prefix': 'foobar',
                   'Storage.S3.AWSAccessKeyId': 'AKIAIOSFODNN7EXAMPLE',
                   'Storage.S3.UploadPolicy': self.Base64Policy,
                   'Storage.S3.UploadPolicySignature': self.PolicySignature}
        self.assert_params_for_cmd(args_list, result)

    def test_policy_provided(self):
        policy = '{"notarealpolicy":true}'
        base64policy = base64.encodestring(policy).strip()
        policy_signature = 'a5SmoLOxoM0MHpOdC25nE7KIafg='
        args = ' --instance-id i-12345678 --owner-akid AKIAIOSFODNN7EXAMPLE'
        args += ' --owner-sak wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        args += ' --bucket mybucket --prefix foobar --policy %s' % policy
        args_list = (self.prefix + args).split()
        result =  {'InstanceId': 'i-12345678',
                   'Storage.S3.Bucket': 'mybucket',
                   'Storage.S3.Prefix': 'foobar',
                   'Storage.S3.AWSAccessKeyId': 'AKIAIOSFODNN7EXAMPLE',
                   'Storage.S3.UploadPolicy': base64policy,
                   'Storage.S3.UploadPolicySignature': policy_signature}
        self.assert_params_for_cmd(args_list, result)

    def test_both(self):
        captured = cStringIO()
        json = """{"S3":{"Bucket":"foobar","Prefix":"fiebaz"}}"""
        args = ' --instance-id i-12345678 --owner-aki blah --owner-sak blah --storage %s' % json
        args_list = (self.prefix + args).split()
        with mock.patch('sys.stderr', captured):
            self.assert_params_for_cmd(args_list, {}, expected_rc=255)

        
if __name__ == "__main__":
    unittest.main()
