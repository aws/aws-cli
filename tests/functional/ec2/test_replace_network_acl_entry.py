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


class TestReplaceNetworkACLEntry(BaseAWSCommandParamsTest):

    prefix = 'ec2 replace-network-acl-entry'

    def test_tcp(self):
        cmdline = self.prefix
        cmdline += ' --network-acl-id acl-12345678'
        cmdline += ' --rule-number 100'
        cmdline += ' --protocol tcp'
        cmdline += ' --rule-action allow'
        cmdline += ' --ingress'
        cmdline += ' --port-range From=22,To=22'
        cmdline += ' --cidr-block 0.0.0.0/0'
        result = {'NetworkAclId': 'acl-12345678',
                  'RuleNumber': 100,
                  'Protocol': '6',
                  'RuleAction': 'allow',
                  'Egress': False,
                  'CidrBlock': '0.0.0.0/0',
                  'PortRange': {'From': 22, 'To': 22}}
        self.assert_params_for_cmd(cmdline, result)

    def test_udp(self):
        cmdline = self.prefix
        cmdline += ' --network-acl-id acl-12345678'
        cmdline += ' --rule-number 100'
        cmdline += ' --protocol udp'
        cmdline += ' --rule-action allow'
        cmdline += ' --ingress'
        cmdline += ' --port-range From=22,To=22'
        cmdline += ' --cidr-block 0.0.0.0/0'
        result = {'NetworkAclId': 'acl-12345678',
                  'RuleNumber': 100,
                  'Protocol': '17',
                  'RuleAction': 'allow',
                  'Egress': False,
                  'CidrBlock': '0.0.0.0/0',
                  'PortRange': {'From': 22, 'To': 22}}
        self.assert_params_for_cmd(cmdline, result)

    def test_icmp(self):
        cmdline = self.prefix
        cmdline += ' --network-acl-id acl-12345678'
        cmdline += ' --rule-number 100'
        cmdline += ' --protocol icmp'
        cmdline += ' --rule-action allow'
        cmdline += ' --ingress'
        cmdline += ' --port-range From=22,To=22'
        cmdline += ' --cidr-block 0.0.0.0/0'
        result = {'NetworkAclId': 'acl-12345678',
                  'RuleNumber': 100,
                  'Protocol': '1',
                  'RuleAction': 'allow',
                  'Egress': False,
                  'CidrBlock': '0.0.0.0/0',
                  'PortRange': {'From': 22, 'To': 22}}
        self.assert_params_for_cmd(cmdline, result)

    def test_all(self):
        cmdline = self.prefix
        cmdline += ' --network-acl-id acl-12345678'
        cmdline += ' --rule-number 100'
        cmdline += ' --protocol all'
        cmdline += ' --rule-action allow'
        cmdline += ' --ingress'
        cmdline += ' --port-range From=22,To=22'
        cmdline += ' --cidr-block 0.0.0.0/0'
        result = {'NetworkAclId': 'acl-12345678',
                  'RuleNumber': 100,
                  'Protocol': '-1',
                  'RuleAction': 'allow',
                  'Egress': False,
                  'CidrBlock': '0.0.0.0/0',
                  'PortRange': {'From': 22, 'To': 22}}
        self.assert_params_for_cmd(cmdline, result)

    def test_number(self):
        cmdline = self.prefix
        cmdline += ' --network-acl-id acl-12345678'
        cmdline += ' --rule-number 100'
        cmdline += ' --protocol 99'
        cmdline += ' --rule-action allow'
        cmdline += ' --ingress'
        cmdline += ' --port-range From=22,To=22'
        cmdline += ' --cidr-block 0.0.0.0/0'
        result = {'NetworkAclId': 'acl-12345678',
                  'RuleNumber': 100,
                  'Protocol': '99',
                  'RuleAction': 'allow',
                  'Egress': False,
                  'CidrBlock': '0.0.0.0/0',
                  'PortRange': {'From': 22, 'To': 22}}
        self.assert_params_for_cmd(cmdline, result)

