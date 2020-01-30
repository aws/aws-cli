#!/usr/bin/env python
# Copyright 2013-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestAuthorizeSecurityGroupIngress(BaseAWSCommandParamsTest):

    prefix = 'ec2 authorize-security-group-ingress '

    def test_simple_cidr(self):
        args = self.prefix + (
            '--group-name foobar --protocol tcp --port 22-25 --cidr 0.0.0.0/0')
        result = {'GroupName': 'foobar',
                  'IpPermissions': [{'FromPort': 22, 'IpProtocol': 'tcp',
                                      'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                                      'ToPort': 25}]}
        self.assert_params_for_cmd(args, result)

    def test_all_port(self):
        args = self.prefix + (
            '--group-name foobar --protocol tcp --port all --cidr 0.0.0.0/0')
        result = {'GroupName': 'foobar',
                   'IpPermissions': [{'FromPort': -1, 'IpProtocol': 'tcp',
                                       'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                                       'ToPort': -1}]}
        self.assert_params_for_cmd(args, result)

    def test_icmp_echo_request(self):
        # This corresponds to a from port of 8 and a to port of -1, i.e
        # --port 8--1.
        args = self.prefix + (
            '--group-name foobar --protocol tcp --port 8--1 --cidr 0.0.0.0/0')
        result = {'GroupName': 'foobar',
                  'IpPermissions': [{'FromPort': 8, 'IpProtocol': 'tcp',
                                      'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                                      'ToPort': -1}]}
        self.assert_params_for_cmd(args, result)

    def test_all_protocol(self):
        args = self.prefix + (
            '--group-name foobar --protocol all --port all --cidr 0.0.0.0/0')
        result = {'GroupName': 'foobar',
                   # This is correct, the expected value is the *string*
                   # '-1'.  This is because the IpProtocol is modeled
                   # as a string.
                   'IpPermissions': [{'FromPort': -1, 'IpProtocol': '-1',
                                       'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                                       'ToPort': -1}]}

        self.assert_params_for_cmd(args, result)

    def test_numeric_protocol(self):
        args = self.prefix + (
            '--group-name foobar --protocol 200 --cidr 0.0.0.0/0')
        result = {'GroupName': 'foobar',
                   'IpPermissions': [{'IpProtocol': '200', 'IpRanges':
                                       [{'CidrIp': '0.0.0.0/0'}]}]}
        self.assert_params_for_cmd(args, result)

    def test_negative_one_protocol(self):
        args = self.prefix + (
            '--group-name foobar --protocol -1 --cidr 0.0.0.0/0')
        result = {'GroupName': 'foobar',
                   'IpPermissions': [{'IpProtocol': '-1', 'IpRanges':
                                       [{'CidrIp': '0.0.0.0/0'}]}]}
        self.assert_params_for_cmd(args, result)

    def test_classic_group(self):
        args = self.prefix + (
            '--group-name foobar --protocol udp '
            '--source-group fiebaz --group-owner 11111111')
        result = {'GroupName': 'foobar',
                   'IpPermissions': [{'IpProtocol': 'udp', 'UserIdGroupPairs':
                                       [{'GroupName': 'fiebaz', 'UserId':
                                         '11111111'}]}]}
        self.assert_params_for_cmd(args, result)

    def test_vpc_group(self):
        args = self.prefix + (
            '--group-name foobar --protocol icmp --source-group sg-12345678')
        result = {'GroupName': 'foobar',
                  'IpPermissions': [{'IpProtocol': 'icmp', 'UserIdGroupPairs':
                                      [{'GroupId': 'sg-12345678'}]}]}
        self.assert_params_for_cmd(args, result)

    def test_IpPermissions(self):
        json = (
            '[{"FromPort":8000,"ToPort":9000,'
            '"IpProtocol":"tcp","IpRanges":[{"CidrIp":"192.168.100.0/24"}]}]')
        args = self.prefix + '--group-name foobar --ip-permissions %s' % json
        result = {'GroupName': 'foobar',
                   'IpPermissions': [{'FromPort': 8000, 'ToPort': 9000,
                                      'IpProtocol': 'tcp', 'IpRanges':
                                      [{'CidrIp': '192.168.100.0/24'}]}]}
        self.assert_params_for_cmd(args, result)

    def test_IpPermissions_with_group_id(self):
        json = (
            '[{"FromPort":8000,"ToPort":9000,"IpProtocol":"tcp",'
            '"IpRanges":[{"CidrIp":"192.168.100.0/24"}]}]')
        args = self.prefix + '--group-id sg-12345678 --ip-permissions %s' % json
        result = {'GroupId': 'sg-12345678',
                  'IpPermissions': [{'FromPort': 8000, 'ToPort': 9000,
                                     'IpProtocol': 'tcp', 'IpRanges':
                                     [{'CidrIp': '192.168.100.0/24'}]}]}
        self.assert_params_for_cmd(args, result)

    def test_both(self):
        json = (
            '[{"FromPort":8000,"ToPort":9000,"IpProtocol":"tcp",'
            '"IpRanges":[{"CidrIp":"192.168.100.0/24"}]}]')
        args = self.prefix + '--group-name foobar --port 100 --ip-permissions %s' % json
        self.assert_params_for_cmd(args, expected_rc=252)



class TestRevokeSecurityGroupIngress(TestAuthorizeSecurityGroupIngress):

    prefix = 'ec2 revoke-security-group-ingress '
