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
import sys

from awscli.testutils import unittest
from awscli.testutils import BaseAWSCommandParamsTest


class TestCreateTags(BaseAWSCommandParamsTest):

    prefix = 'ec2 create-tags'

    def test_create_tag_normal(self):
        cmdline = self.prefix
        cmdline += ' --resources i-12345678 --tags Key=Name,Value=bar'
        result = {
            'Resources': ['i-12345678'],
            'Tags': [{'Key': 'Name', 'Value': 'bar'}]}
        self.assert_params_for_cmd(cmdline, result)
