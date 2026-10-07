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

from botocore.paginate import PageIterator

from awscli.formatter import Formatter, TextFormatter


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


class TestTextFormatterResumeToken(unittest.TestCase):
    """Tests for issue #10449: --query must not corrupt the NextToken hint."""

    def _make_formatter(self, query=None):
        args = mock.Mock()
        args.query = query
        return TextFormatter(args)

    def _make_paginated_response(self, pages, resume_token=None):
        result_key = mock.Mock()
        result_key.expression = 'Users'
        result_key.search.side_effect = lambda page: page.get('Users', [])

        response = mock.Mock(spec=PageIterator)
        response.result_keys = [result_key]
        response.non_aggregate_part = {}
        response.__iter__ = mock.Mock(return_value=iter(pages))
        response.resume_token = resume_token
        return response

    def test_resume_token_printed_without_query(self):
        formatter = self._make_formatter(query=None)
        stream = StringIO()
        pages = [{'Users': [{'UserName': 'alice'}]}]
        response = self._make_paginated_response(pages, resume_token='tok123')
        formatter('list-users', response, stream)
        output = stream.getvalue()
        self.assertIn('NEXTTOKEN', output)
        self.assertIn('tok123', output)

    def test_resume_token_not_filtered_to_none_when_query_set(self):
        # Regression test for #10449: a JMESPath query on data keys
        # must not cause the NextToken hint to print as "None".
        query = mock.Mock()
        query.search.side_effect = lambda data: (
            None if 'NextToken' in data
            else [u['UserName'] for u in data.get('Users', [])]
        )
        formatter = self._make_formatter(query=query)
        stream = StringIO()
        pages = [{'Users': [{'UserName': 'alice'}]}]
        response = self._make_paginated_response(pages, resume_token='tok123')
        formatter('list-users', response, stream)
        output = stream.getvalue()
        self.assertIn('NEXTTOKEN', output)
        self.assertIn('tok123', output)
        self.assertNotIn('None', output)

    def test_no_resume_token_output_when_not_truncated(self):
        formatter = self._make_formatter(query=None)
        stream = StringIO()
        pages = [{'Users': [{'UserName': 'alice'}]}]
        response = self._make_paginated_response(pages, resume_token=None)
        formatter('list-users', response, stream)
        output = stream.getvalue()
        self.assertNotIn('NEXTTOKEN', output)
