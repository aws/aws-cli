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
                    '{"Value":"foo-bar-com"}'
                    ']}}]}')


class TestGetHostedZone(BaseAWSCommandParamsTest):

    prefix = 'route53 get-hosted-zone'

    def setUp(self):
        super(TestGetHostedZone, self).setUp()

    def test_full_resource_id(self):
        args = ' --id /hostedzone/ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        self.assert_params_for_cmd(
            cmdline, {'Id': 'ZD3IYMVP1KDDM'}, expected_rc=0)

    def test_short_resource_id(self):
        args = ' --id ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        self.assert_params_for_cmd(
            cmdline, {'Id': 'ZD3IYMVP1KDDM'},
            expected_rc=0)


class TestChangeResourceRecord(BaseAWSCommandParamsTest):

    prefix = 'route53 change-resource-record-sets'

    def setUp(self):
        super(TestChangeResourceRecord, self).setUp()

    def test_full_resource_id(self):
        args = ' --hosted-zone-id /change/ZD3IYMVP1KDDM'
        args += ' --change-batch %s' % CHANGEBATCH_JSON
        cmdline = self.prefix + args
        expected = {
            "HostedZoneId": "ZD3IYMVP1KDDM",
            "ChangeBatch": {
                "Comment": "string",
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": "test-foo.bar.com",
                            "Type": "CNAME",
                            "TTL": 300,
                            "ResourceRecords": [
                                {
                                    "Value": "foo-bar-com"
                                }
                            ]
                        }
                    }
                ]
            }
        }
        self.assert_params_for_cmd(cmdline, expected, expected_rc=0)


class TestGetChange(BaseAWSCommandParamsTest):

    prefix = 'route53 get-change'

    def setUp(self):
        super(TestGetChange, self).setUp()

    def test_full_resource_id(self):
        args = ' --id /change/ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        expected = {'Id': 'ZD3IYMVP1KDDM'}
        self.assert_params_for_cmd(cmdline, expected, expected_rc=0)

    def test_short_resource_id(self):
        args = ' --id ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        expected = {'Id': 'ZD3IYMVP1KDDM'}
        self.assert_params_for_cmd(cmdline, expected, expected_rc=0)


class TestReusableDelegationSet(BaseAWSCommandParamsTest):

    prefix = 'route53 get-reusable-delegation-set'

    def setUp(self):
        super(TestReusableDelegationSet, self).setUp()

    def test_full_resource_id(self):
        args = ' --id /delegationset/N9INWVYQ6Q0FN'
        cmdline = self.prefix + args
        self.assert_params_for_cmd(cmdline, {'Id': 'N9INWVYQ6Q0FN'},
                                    expected_rc=0)

    def test_short_resource_id(self):
        args = ' --id N9INWVYQ6Q0FN'
        cmdline = self.prefix + args
        self.assert_params_for_cmd(cmdline, {'Id': 'N9INWVYQ6Q0FN'},
                                    expected_rc=0)


class TestMaxItems(BaseAWSCommandParamsTest):

    prefix = 'route53 list-resource-record-sets'

    def test_full_resource_id(self):
        args = ' --hosted-zone-id /hostedzone/ABCD --max-items 1'
        cmdline = self.prefix + args
        expected = {'HostedZoneId': 'ABCD'}
        self.assert_params_for_cmd(cmdline, expected, expected_rc=0)
