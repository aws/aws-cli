#!/usr/bin/env python
# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestObjectLambdaHandling(BaseAWSCommandParamsTest):

    prefixes = [
        's3 ls s3://{object_lambda_arn}',
        's3 cp s3://{object_lambda_arn} .',
        's3 mv s3://{object_lambda_arn} .',
        's3 sync s3://{object_lambda_arn} .',
        's3 rm s3://{object_lambda_arn}',
        's3 mb s3://{object_lambda_arn}',
        's3 presign s3://{object_lambda_arn}',
        's3 rb s3://{object_lambda_arn}',
        's3 website s3://{object_lambda_arn}',
    ]

    def test_object_lambda_arn_with_colon_raises_exception(self):
        object_lambda_arn = ('arn:aws:s3-object-lambda:us-west-2:123456789012:'
                             'accesspoint:my-accesspoint')
        object_lambda_arn_with_key = '%s/my-key' % object_lambda_arn
        for prefix in self.prefixes:
            cmdline = prefix.format(object_lambda_arn=object_lambda_arn)
            _, stderr, _ = self.run_cmd(cmdline, 252)
            self.assertIn('s3 commands do not support', stderr)
            cmdline = prefix.format(
                object_lambda_arn=object_lambda_arn_with_key)
            _, stderr, _ = self.run_cmd(cmdline, 252)
            self.assertIn('s3 commands do not support', stderr)

    def test_object_lambda_arn_with_slash_raises_exception(self):
        object_lambda_arn = ('arn:aws:s3-object-lambda:us-west-2:123456789012:'
                             'accesspoint/my-accesspoint')
        object_lambda_arn_with_key = '%s/my-key' % object_lambda_arn
        for prefix in self.prefixes:
            cmdline = prefix.format(object_lambda_arn=object_lambda_arn)
            _, stderr, _ = self.run_cmd(cmdline, 252)
            self.assertIn('s3 commands do not support', stderr)
            cmdline = prefix.format(
                object_lambda_arn=object_lambda_arn_with_key)
            _, stderr, _ = self.run_cmd(cmdline, 252)
            self.assertIn('s3 commands do not support', stderr)
