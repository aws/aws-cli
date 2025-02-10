#!/usr/bin/env python
# Copyright 2013-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestSendEmail(BaseAWSCommandParamsTest):

    prefix = 'ses send-email'

    def test_plain_text(self):
        args = (' --subject This_is_a_test --from foo@bar.com'
                ' --to fie@baz.com --text This_is_the_message')
        args_list = (self.prefix + args).split()
        result = {
            'Source': 'foo@bar.com',
            'Destination': {'ToAddresses': ['fie@baz.com']},
            'Message': {'Body': {'Text': {'Data': 'This_is_the_message'}},
                        'Subject': {'Data': 'This_is_a_test'}}}
        self.assert_params_for_cmd(args_list, result)

    def test_plain_text_multiple_to(self):
        args = (' --subject This_is_a_test --from foo@bar.com'
                ' --to fie1@baz.com fie2@baz.com --text This_is_the_message')
        args_list = (self.prefix + args).split()
        result = {'Source': 'foo@bar.com',
                  'Destination': {
                      'ToAddresses': ['fie1@baz.com', 'fie2@baz.com']},
                  'Message': {
                      'Body': {'Text': {'Data': 'This_is_the_message'}},
                      'Subject': {'Data': 'This_is_a_test'}}}

        self.assert_params_for_cmd(args_list, result)

    def test_plain_text_multiple_cc(self):
        args = (' --subject This_is_a_test --from foo@bar.com'
                ' --to fie1@baz.com fie2@baz.com --text This_is_the_message'
                ' --cc fie3@baz.com fie4@baz.com')
        args_list = (self.prefix + args).split()
        result = {'Source': 'foo@bar.com',
                  'Destination': {
                      'CcAddresses': ['fie3@baz.com', 'fie4@baz.com'],
                      'ToAddresses': ['fie1@baz.com', 'fie2@baz.com']},
                  'Message': {
                      'Body': {'Text': {'Data': 'This_is_the_message'}},
                      'Subject': {'Data': 'This_is_a_test'}}}

        self.assert_params_for_cmd(args_list, result)

    def test_plain_text_multiple_bcc(self):
        args = (' --subject This_is_a_test --from foo@bar.com'
                ' --to fie1@baz.com fie2@baz.com --text This_is_the_message'
                ' --cc fie3@baz.com fie4@baz.com'
                ' --bcc fie5@baz.com fie6@baz.com')
        args_list = (self.prefix + args).split()

        result = {
            'Source': 'foo@bar.com',
            'Destination': {'BccAddresses': ['fie5@baz.com', 'fie6@baz.com'],
                            'CcAddresses': ['fie3@baz.com', 'fie4@baz.com'],
                            'ToAddresses': ['fie1@baz.com', 'fie2@baz.com']},
            'Message': {
                'Body': {'Text': {'Data': 'This_is_the_message'}},
                'Subject': {'Data': 'This_is_a_test'}}}

        self.assert_params_for_cmd(args_list, result)

    def test_html_text(self):
        args = (' --subject This_is_a_test --from foo@bar.com'
                ' --to fie@baz.com --html This_is_the_html_message')
        args_list = (self.prefix + args).split()
        result = {
            'Source': 'foo@bar.com',
            'Destination': {'ToAddresses': ['fie@baz.com']},
            'Message': {'Subject': {'Data': 'This_is_a_test'},
                        'Body': {
                            'Html': {'Data': 'This_is_the_html_message'}}}}

        self.assert_params_for_cmd(args_list, result)

    def test_html_both(self):
        args = (' --subject This_is_a_test --from foo@bar.com'
                ' --to fie@baz.com --html This_is_the_html_message'
                ' --text This_is_the_text_message')
        args_list = (self.prefix + args).split()
        result = {
            'Source': 'foo@bar.com',
            'Destination': {'ToAddresses': ['fie@baz.com']},
            'Message': {
                'Subject': {'Data': 'This_is_a_test'},
                'Body': {
                    'Text': {'Data': 'This_is_the_text_message'},
                    'Html': {'Data': 'This_is_the_html_message'}}}}
        self.assert_params_for_cmd(args_list, result)

    def test_using_json(self):
        args = (' --message {"Subject":{"Data":"This_is_a_test"},'
                '"Body":{"Text":{"Data":"This_is_the_message"}}}'
                ' --from foo@bar.com'
                ' --destination {"ToAddresses":["fie@baz.com"]}')
        args_list = (self.prefix + args).split()
        result = {'Destination': {'ToAddresses': ['fie@baz.com']},
                  'Message': {
                      'Subject': {
                          'Data': 'This_is_a_test'},
                      'Body': {
                          'Text': {'Data': 'This_is_the_message'}}},
                  'Source': 'foo@bar.com'}

        self.assert_params_for_cmd(args_list, result)

    def test_both_destination_and_to(self):
        args = (' --message {"Subject":{"Data":"This_is_a_test"},'
                '"Body":{"Text":{"Data":"This_is_the_message"}}}'
                ' --from foo@bar.com'
                ' --destination {"ToAddresses":["fie@baz.com"]}'
                ' --to fie2@baz.com')
        args_list = (self.prefix + args).split()
        self.run_cmd(args_list, expected_rc=255)

    def test_both_message_and_text(self):
        args = (' --message {"Subject":{"Data":"This_is_a_test"},'
                '"Body":{"Text":{"Data":"This_is_the_message"}}}'
                ' --from foo@bar.com'
                ' --destination {"ToAddresses":["fie@baz.com"]}'
                ' --text This_is_another_body')
        args_list = (self.prefix + args).split()
        self.run_cmd(args_list, expected_rc=255)
