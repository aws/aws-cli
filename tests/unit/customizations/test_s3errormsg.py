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

    def test_kms_sigv4_error_message(self):
        parsed = {
            'Error': {
                'Message': (
                    'Requests specifying Server Side Encryption with '
                    'AWS KMS managed keys require AWS Signature Version 4.')
            }
        }
        s3errormsg.enhance_error_msg(parsed)
        # We should say how you enable it.
        self.assertIn('You can enable AWS Signature Version 4',
                      parsed['Error']['Message'])
        # We should mention the command that needs to be run.
        self.assertIn(
            'aws configure set s3.signature_version s3v4',
            parsed['Error']['Message'])

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

    def test_none_message_does_not_crash(self):
        # Empty <Message></Message> parsed as None must not raise TypeError.
        parsed = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': None,
            }
        }
        # Should not raise TypeError
        s3errormsg.enhance_error_msg(parsed)
        # Message should remain None since no error pattern matched
        self.assertIsNone(parsed['Error']['Message'])

    def test_none_message_with_sigv4_code(self):
        # None Message should not match sigv4 pattern.
        parsed = {
            'Error': {
                'Code': 'AuthorizationHeaderMalformed',
                'Message': None,
            }
        }
        s3errormsg.enhance_error_msg(parsed)
        # Should not have been enhanced (no match)
        self.assertIsNone(parsed['Error']['Message'])

    def test_none_message_with_kms_context(self):
        # None Message should not match KMS sigv4 pattern.
        parsed = {
            'Error': {
                'Code': 'InvalidArgument',
                'Message': None,
            }
        }
        s3errormsg.enhance_error_msg(parsed)
        self.assertIsNone(parsed['Error']['Message'])

    def test_none_code_does_not_crash(self):
        # None Code should not crash PermanentRedirect check.
        parsed = {
            'Error': {
                'Code': None,
                'Message': 'Some error message.',
            }
        }
        expected = copy.deepcopy(parsed)
        s3errormsg.enhance_error_msg(parsed)
        # Nothing should have changed
        self.assertEqual(parsed, expected)

    def test_empty_string_message_does_not_crash(self):
        # Empty string Message should be handled without crashing.
        parsed = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': '',
            }
        }
        expected = copy.deepcopy(parsed)
        s3errormsg.enhance_error_msg(parsed)
        self.assertEqual(parsed, expected)

    def test_permanent_redirect_with_none_message(self):
        # PermanentRedirect with None Message should not crash.
        parsed = {
            'Error': {
                'Code': 'PermanentRedirect',
                'Message': None,
                'Endpoint': 'myendpoint',
            }
        }
        s3errormsg.enhance_error_msg(parsed)
        # Should have enhanced the message despite None original
        self.assertIn('myendpoint', parsed['Error']['Message'])
