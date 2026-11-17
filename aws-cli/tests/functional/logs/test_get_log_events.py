# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestGetLogEvents(BaseAWSCommandParamsTest):
    prefix = 'logs get-log-events'

    # TODO: Get rid of this test once we do the following:
    # 1) Add support for pagination operations that return repeat next
    #    tokens to indicate that pagination has ended. Currently an
    #    error is thrown for this.
    # 2) We add a pagination model for GetLogEvents
    def test_cannot_paginate(self):
        cmdline = self.prefix
        cmdline += ' --log-group-name foo'
        cmdline += ' --log-stream-name bar'
        cmdline += ' --page-size 5'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=252)
        self.assertIn('Unknown options', stderr)
        self.assertIn('--page-size', stderr)
