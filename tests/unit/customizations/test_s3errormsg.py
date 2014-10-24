# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0e
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import copy

from awscli.testutils import unittest
from awscli.customizations import s3errormsg


class TestGetRegionFromEndpoint(unittest.TestCase):

    def test_sigv4_error_message(self):
        parsed = {
            'Error': {
                'Message': 'Please use AWS4-HMAC-SHA256'
            }
        }
        s3errormsg.enhance_error_msg(parsed)
        # We should say how to fix the issue.
        self.assertIn('You can fix this issue',
                      parsed['Error']['Message'])
        # We should mention the --region argument.
        self.assertIn('--region', parsed['Error']['Message'])
        # We should mention get-bucket-location
        self.assertIn('get-bucket-location', parsed['Error']['Message'])

    def test_301_error_message(self):
        parsed = {
            'Error': {
                'Code': 'PermanentRedirect',
                'Message': "Please use the correct endpoint.",
                'Endpoint': "myendpoint",
            }
        }
        s3errormsg.enhance_error_msg(parsed)
        # We should include the endpoint in the error message.
        error_message = parsed['Error']['Message']
        self.assertIn('myendpoint', error_message)

    def test_error_message_not_enhanced(self):
        parsed = {
            'Error': {
                'Message': 'This is a different error message.',
                'Code': 'Other Message'
            }
        }
        expected = copy.deepcopy(parsed)
        s3errormsg.enhance_error_msg(parsed)
        # Nothing should have changed
        self.assertEqual(parsed, expected)

    def test_not_an_error_message(self):
        parsed = {
            'Success': 'response',
            'ResponseMetadata': {}
        }
        expected = copy.deepcopy(parsed)
        s3errormsg.enhance_error_msg(parsed)
        # Nothing should have changed
        self.assertEqual(parsed, expected)
