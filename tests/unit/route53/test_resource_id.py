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

        
