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
import awscli.clidriver


class TestGetQueueAttributes(BaseAWSCommandParamsTest):

    prefix = 'sqs get-queue-attributes'
    queue_url = 'https://queue.amazonaws.com/4444/testcli'

    def test_no_attr(self):
        cmdline = self.prefix + ' --queue-url %s' % self.queue_url
        result = {'QueueUrl': self.queue_url}
        self.assert_params_for_cmd(cmdline, result)

    def test_all(self):
        cmdline = self.prefix + ' --queue-url %s' % self.queue_url
        cmdline += ' --attribute-names All'
        result = {'QueueUrl': self.queue_url,
                  'AttributeNames': ['All']}
        self.assert_params_for_cmd(cmdline, result)

    def test_one(self):
        cmdline = self.prefix + ' --queue-url %s' % self.queue_url
        cmdline += ' --attribute-names VisibilityTimeout'
        result = {'QueueUrl': self.queue_url,
                  'AttributeNames': ['VisibilityTimeout']}
        self.assert_params_for_cmd(cmdline, result)

    def test_two(self):
        cmdline = self.prefix + ' --queue-url %s' % self.queue_url
        cmdline += ' --attribute-names VisibilityTimeout QueueArn'
        result = {'QueueUrl': self.queue_url,
                  'AttributeNames': ['VisibilityTimeout', 'QueueArn']}
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
