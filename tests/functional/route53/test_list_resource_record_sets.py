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


class TestGetHostedZone(BaseAWSCommandParamsTest):

    prefix = 'route53 list-resource-record-sets'

    def test_no_pagination_args(self):
        args = ' --hosted-zone-id /hostedzone/ZD3IYMVP1KDDM'
        cmdline = self.prefix + args
        self.assert_params_for_cmd(
            cmdline, {'HostedZoneId': 'ZD3IYMVP1KDDM'}, expected_rc=0)

    def test_with_max_items_pagination(self):
        args = ' --hosted-zone-id /hostedzone/ZD3IYMVP1KDDM --max-items 1'
        cmdline = self.prefix + args
        # We don't map to the service's max-items
        self.assert_params_for_cmd(
            cmdline, {'HostedZoneId': 'ZD3IYMVP1KDDM'}, expected_rc=0)

    def test_with_max_override_starting_args(self):
        args = (
            ' --hosted-zone-id /hostedzone/ZD3IYMVP1KDDM'
            ' --max-items 1'
            ' --start-record-name foo')
        cmdline = self.prefix + args
        # Here we _should_ be mapping to the service's arguments
        # because --start-record-name triggered the disabling of
        # pagination.
        self.assert_params_for_cmd(
            cmdline, {'HostedZoneId': 'ZD3IYMVP1KDDM',
                      'StartRecordName': 'foo',
                      'MaxItems': '1'},
            expected_rc=0)
