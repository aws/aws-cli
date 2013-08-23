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
import os
import sys
import re

from six.moves import cStringIO
import httpretty
import mock

ADD_USER_RESPONSE = """\
<AddUserToGroupResponse xmlns="https://iam.amazonaws.com/doc/2010-05-08/">
  <ResponseMetadata>
      <RequestId>b8ff9277-0c3a-11e3-941e-8d1b33bbf528</RequestId>
  </ResponseMetadata>
</AddUserToGroupResponse>
"""


class TestGetPasswordData(BaseAWSCommandParamsTest):

    prefix = 'iam add-user-to-group '

    def register_uri(self):
        httpretty.register_uri(httpretty.POST, re.compile('.*'),
                               body=ADD_USER_RESPONSE)

    def test_empty_response_prints_nothing(self):
        captured = cStringIO()
        args = ' --group-name foo --user-name bar'
        cmdline = self.prefix + args
        result = {'GroupName': 'foo', 'UserName': 'bar'}
        with mock.patch('sys.stdout', captured):
            self.assert_params_for_cmd(cmdline, result, expected_rc=0)
        output = captured.getvalue()
        # We should have printed nothing because the parsed response
        # is an empty dict: {}.
        self.assertEqual(output, '')
