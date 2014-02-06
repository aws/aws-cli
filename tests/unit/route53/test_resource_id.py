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


CHANGEBATCH_JSON = ('{"Comment":"string","Changes":['
                    '{"Action":"CREATE","ResourceRecordSet":{'
                    '"Name":"test-foo.bar.com",'
                    '"Type":"CNAME",'
                    '"TTL":300,'
                    '"ResourceRecords":['
                    '{"Value":"foo-bar-com.us-west-1.elb.amazonaws.com"}'
                    ']}}]}')

CHANGEBATCH_XML = ('<ChangeResourceRecordSetsRequest '
                   'xmlns="https://route53.amazonaws.com/doc/2013-04-01/">'
                   '<ChangeBatch><Comment>string</Comment>'
                   '<Changes><Change><Action>CREATE</Action>'
                   '<ResourceRecordSet>'
                   '<Name>test-foo.bar.com</Name>'
                   '<Type>CNAME</Type><TTL>300</TTL>'
                   '<ResourceRecords><ResourceRecord>'
                   '<Value>foo-bar-com.us-west-1.elb.amazonaws.com</Value>'
                   '</ResourceRecord></ResourceRecords>'
                   '</ResourceRecordSet></Change></Changes>'
                   '</ChangeBatch></ChangeResourceRecordSetsRequest>')

class TestGetHostedZone(BaseAWSCommandParamsTest):

    prefix = 'route53 get-hosted-zone'

    def setUp(self):
        super(TestGetHostedZone, self).setUp()

    def test_full_resource_id(self):
        args = ' --id /hostedzone/ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        result = {'uri_params': {'Id': 'ZD3IYMVP1KDDM'},
                  'headers': {}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0,
                                   ignore_params=['payload'])[0]

    def test_short_resource_id(self):
        args = ' --id ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        result = {'uri_params': {'Id': 'ZD3IYMVP1KDDM'},
                  'headers': {}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0,
                                   ignore_params=['payload'])[0]


class TestChangeResourceRecord(BaseAWSCommandParamsTest):

    prefix = 'route53 change-resource-record-sets'

    def setUp(self):
        super(TestChangeResourceRecord, self).setUp()

    def test_full_resource_id(self):
        args = ' --hosted-zone-id /change/ZD3IYMVP1KDDM'
        args += ' --change-batch %s' % CHANGEBATCH_JSON
        cmdline = self.prefix + args
        result = {'uri_params': {'HostedZoneId': 'ZD3IYMVP1KDDM'},
                  'headers': {}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0,
                                   ignore_params=['payload'])[0]
        self.assertEqual(self.last_params['payload'].getvalue(),
                         CHANGEBATCH_XML)


class TestGetChange(BaseAWSCommandParamsTest):

    prefix = 'route53 get-change'

    def setUp(self):
        super(TestGetChange, self).setUp()

    def test_full_resource_id(self):
        args = ' --id /change/ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        result = {'uri_params': {'Id': 'ZD3IYMVP1KDDM'},
                  'headers': {}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0,
                                   ignore_params=['payload'])[0]

    def test_short_resource_id(self):
        args = ' --id ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        result = {'uri_params': {'Id': 'ZD3IYMVP1KDDM'},
                  'headers': {}}
        self.assert_params_for_cmd(cmdline, result, expected_rc=0,
                                   ignore_params=['payload'])[0]

        
