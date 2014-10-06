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


CHANGEBATCH_JSON = ('{"Comment":"string","Changes":['
                    '{"Action":"CREATE","ResourceRecordSet":{'
                    '"Name":"test-foo.bar.com",'
                    '"Type":"CNAME",'
                    '"TTL":300,'
                    '"ResourceRecords":['
                    '{"Value":"foo-bar-com.us-west-1.elb.amazonaws.com"}'
                    ']}}]}')


class TestGetHostedZone(BaseAWSCommandParamsTest):

    prefix = 'route53 get-hosted-zone'

    def setUp(self):
        super(TestGetHostedZone, self).setUp()

    def test_full_resource_id(self):
        args = ' --id /hostedzone/ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        expected_id = 'ZD3IYMVP1KDDM'
        self.assert_params_for_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.last_kwargs['Id'], expected_id)

    def test_short_resource_id(self):
        args = ' --id ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        expected_id = 'ZD3IYMVP1KDDM'
        self.assert_params_for_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.last_kwargs['Id'], expected_id)


class TestChangeResourceRecord(BaseAWSCommandParamsTest):

    prefix = 'route53 change-resource-record-sets'

    def setUp(self):
        super(TestChangeResourceRecord, self).setUp()

    def test_full_resource_id(self):
        args = ' --hosted-zone-id /change/ZD3IYMVP1KDDM'
        args += ' --change-batch %s' % CHANGEBATCH_JSON
        cmdline = self.prefix + args
        expected_hosted_zone = 'ZD3IYMVP1KDDM'
        self.assert_params_for_cmd2(cmdline, expected_rc=0)
        # Verify that we used the correct value for HostedZoneId.
        self.assertEqual(self.last_kwargs['HostedZoneId'],
                         expected_hosted_zone)


class TestGetChange(BaseAWSCommandParamsTest):

    prefix = 'route53 get-change'

    def setUp(self):
        super(TestGetChange, self).setUp()

    def test_full_resource_id(self):
        args = ' --id /change/ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        expected_id = 'ZD3IYMVP1KDDM'
        self.assert_params_for_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.last_kwargs['Id'], expected_id)

    def test_short_resource_id(self):
        args = ' --id ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        expected_id = 'ZD3IYMVP1KDDM'
        self.assert_params_for_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.last_kwargs['Id'], expected_id)


class TestMaxItems(BaseAWSCommandParamsTest):

    prefix = 'route53 list-resource-record-sets'

    def test_full_resource_id(self):
        args = ' --hosted-zone-id /hostedzone/ABCD --max-items 1'
        cmdline = self.prefix + args
        expected_hosted_zone = 'ABCD'
        self.assert_params_for_cmd2(cmdline, expected_rc=0)
        # Verify that we used the correct value for HostedZoneId.
        self.assertEqual(self.last_kwargs['HostedZoneId'],
                         expected_hosted_zone)
