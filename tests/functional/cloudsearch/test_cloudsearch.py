#!/usr/bin/env python
# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestCloudSearchDefineExpression(BaseAWSCommandParamsTest):

    prefix = 'cloudsearch define-expression'

    def test_flattened(self):
        cmdline = self.prefix
        cmdline += ' --domain-name abc123'
        cmdline += ' --name foo'
        cmdline += ' --expression 10'
        result = {
            'DomainName': 'abc123',
            'Expression': {'ExpressionName': 'foo',
                           'ExpressionValue': '10'}}
        self.assert_params_for_cmd(cmdline, result)


class TestCloudSearchDefineIndexField(BaseAWSCommandParamsTest):

    prefix = 'cloudsearch define-index-field'

    def test_flattened(self):
        cmdline = self.prefix
        cmdline += ' --domain-name abc123'
        cmdline += ' --name foo'
        cmdline += ' --type int'
        cmdline += ' --default-value 10'
        cmdline += ' --search-enabled false'
        result = {
            'DomainName': 'abc123',
            'IndexField': {'IndexFieldName': 'foo',
                           'IndexFieldType': 'int',
                           'IntOptions': {'DefaultValue': 10,
                                          'SearchEnabled': False}}}
        self.assert_params_for_cmd(cmdline, result)

    def test_latlon(self):
        cmdline = self.prefix
        cmdline += ' --domain-name abc123'
        cmdline += ' --name foo'
        cmdline += ' --type latlon'
        cmdline += ' --default-value 10'
        cmdline += ' --search-enabled false'
        result = {
            'DomainName': 'abc123',
            'IndexField': {
                'IndexFieldName': 'foo',
                'IndexFieldType': 'latlon',
                'LatLonOptions': {
                    'DefaultValue': '10', 'SearchEnabled': False}}}
        self.assert_params_for_cmd(cmdline, result)
