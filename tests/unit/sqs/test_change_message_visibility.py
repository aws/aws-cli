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
import unittest
import awscli.clidriver


class TestChangeMessageVisibility(unittest.TestCase):

    def setUp(self):
        self.driver = awscli.clidriver.CLIDriver()
        self.prefix = 'aws sqs change-message-visibility'
        self.queue_url = 'https://queue.amazonaws.com/4444/testcli'
        self.receipt_handle = 'abcedfghijklmnopqrstuvwxyz'

    def test_all_params(self):
        cmdline = self.prefix
        cmdline += ' --queue-url %s' % self.queue_url
        cmdline += ' --receipt-handle %s' % self.receipt_handle
        cmdline += ' --visibility-timeout 30'
        result = {'QueueUrl': self.queue_url,
                  'ReceiptHandle': self.receipt_handle,
                  'VisibilityTimeout': '30'}
        params = self.driver.test(cmdline)
        self.assertEqual(params, result)


if __name__ == "__main__":
    unittest.main()
