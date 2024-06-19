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
from awscli.testutils import mock, unittest
from awscli.compat import StringIO
import json
import os
import sys
import re
import locale

from awscli.formatter import Formatter


class TestListUsers(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestListUsers, self).setUp()
        self.first_parsed_response = {
            'Users': [
                {
                    "UserName": "testuser-50",
                    "Path": "/",
                    "CreateDate": "2013-02-12T19:08:52Z",
                    "UserId": "EXAMPLEUSERID",
                    "Arn": "arn:aws:iam::12345:user/testuser1"
                },
            ],
            'Groups': []
        }
        self.second_parsed_response = {
            'Users': [
                {
                    "UserName": "testuser-51",
                    "Path": "/",
                    "CreateDate": "2012-10-14T23:53:39Z",
                    "UserId": "EXAMPLEUSERID",
                    "Arn": "arn:aws:iam::123456:user/testuser2"
                },
            ],
            'Groups': []
        }

        self.parsed_responses = [
            self.first_parsed_response,
            self.second_parsed_response
        ]

    def test_text_response(self):
        output = self.run_cmd('iam list-users --output text', expected_rc=0)[0]
        self.assertEqual(
            output,
            ('USERS\tarn:aws:iam::12345:user/testuser1\t2013-02-12T19:08:52Z\t'
             '/\tEXAMPLEUSERID\ttestuser-50\n'))

        # Test something with a jmespath expression.
        output = self.run_cmd(
            'rds describe-engine-default-parameters ' \
            '--db-parameter-group-family mysql5.1 --output text',
            expected_rc=0)[0]
        self.assertEqual(
            output,
            'ENGINEDEFAULTS\tNone\n')


class TestDescribeChangesets(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestDescribeChangesets, self).setUp()
        self.first_parsed_response = {
            'Capabilities': ['CAPABILITY_IAM'],
            'ChangeSetId': (
                'arn:aws:cloudformation:us-west-2:12345:changeSet'
                '/mychangeset/12345'
            ),
            'ChangeSetName': 'mychangeset',
            'Changes': [{"ChangeId": "1"}],
            'CreationTime': '2019-04-08T14:21:53.765Z',
            'ExecutionStatus': 'AVAILABLE',
            'NotificationARNs': [],
            'RollbackConfiguration': {'RollbackTriggers': []},
            'StackId': (
                'arn:aws:cloudformation:us-west-2:12345:stack'
                '/MyStack/12345'
            ),
            'StackName': 'MyStack',
            'Status': 'CREATE_COMPLETE',
            'NextToken': "more stuff"
        }
        self.second_parsed_response = {
            'Capabilities': ['CAPABILITY_IAM'],
            'ChangeSetId': (
                'arn:aws:cloudformation:us-west-2:12345:changeSet'
                '/mychangeset/12345'
            ),
            'ChangeSetName': 'mychangeset',
            'Changes': [{"ChangeId": "2"}],
            'CreationTime': '2019-04-08T14:21:53.765Z',
            'ExecutionStatus': 'AVAILABLE',
            'NotificationARNs': [],
            'RollbackConfiguration': {'RollbackTriggers': []},
            'StackId': (
                'arn:aws:cloudformation:us-west-2:12345:stack'
                '/MyStack/12345'
            ),
            'StackName': 'MyStack',
            'Status': 'CREATE_COMPLETE'
        }
        self.parsed_responses = [
            self.first_parsed_response,
            self.second_parsed_response,
        ]

    def test_non_aggregate_keys(self):
        output = self.run_cmd(
            ('cloudformation describe-change-set --change-set-name mychangeset'
             ' --stack-name MyStack --output text'),
            expected_rc=0
        )[0]
        fields = output.split()
        self.assertIn((
            "arn:aws:cloudformation:us-west-2:12345:changeSet/mychangeset/"
            "12345"), fields)
        self.assert_in("CAPABILITY_IAM", fields, 1)
        self.assert_in("mychangeset", fields, 1)
        self.assert_in("2019-04-08T14:21:53.765Z", fields, 1)
        self.assert_in("AVAILABLE", fields, 1)
        self.assert_in("MyStack", fields, 1)
        self.assert_in("CREATE_COMPLETE", fields, 1)

    def assert_in(self, key, fields, count=None):
        if count is None:
            self.assertIn(key, fields)
        else:
            actual_count = fields.count(key)
            self.assertEqual(
                count,
                actual_count,
                "%s was found in the output %s times. Expected %s." % (
                    key, actual_count, count
                )
            )
