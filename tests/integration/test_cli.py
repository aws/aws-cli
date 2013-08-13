# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import unittest
import time
import os
import sys
import tempfile
import random
import shutil

import botocore.session
from tests.integration import Result, aws


class TestBasicCommandFunctionality(unittest.TestCase):
    """
    These are a set of tests that assert high level features of
    the CLI.  They don't anything exhaustive and is meant as a smoke
    test to verify basic CLI functionality isn't entirely broken.
    """

    def put_object(self, bucket, key, content):
        session = botocore.session.get_session()
        service = session.get_service('s3')
        endpoint = service.get_endpoint('us-east-1')
        http, response = service.get_operation(
            'CreateBucket').call(endpoint, bucket=bucket)
        time.sleep(5)
        self.addCleanup(service.get_operation('DeleteBucket').call,
                        endpoint, bucket=bucket)
        http, response = service.get_operation('PutObject').call(
            endpoint, bucket=bucket, key=key, body=content)
        self.addCleanup(service.get_operation('DeleteObject').call,
                        endpoint, bucket=bucket, key=key)

    def test_ec2_describe_instances(self):
        # Verify we can make a call and get output.
        p = aws('ec2 describe-instances')
        self.assertEqual(p.rc, 0)
        # We don't know what instances a user might have, but we know
        # there should at least be a Reservations key.
        self.assertIn('Reservations', p.json)

    def test_help_output(self):
        p = aws('help')
        self.assertEqual(p.rc, 1)
        self.assertIn('AWS', p.stdout)
        self.assertRegexpMatches(p.stdout, 'The\s+AWS\s+Command Line Interface')

    def test_service_help_output(self):
        p = aws('ec2 help')
        self.assertEqual(p.rc, 1)
        self.assertIn('Amazon EC2', p.stdout)

    def test_operation_help_output(self):
        p = aws('ec2 describe-instances help')
        self.assertEqual(p.rc, 1)
        # XXX: This is a rendering bug that needs to be fixed in bcdoc.  In
        # the RST version there are multiple spaces between certain words.
        # For now we're making the test less strict about formatting, but
        # we eventually should update this test to check exactly for
        # 'The describe-instances operation'.
        self.assertRegexpMatches(p.stdout,
                                 'The\s+describe-instances\s+operation')

    def test_operation_help_with_required_arg(self):
        p = aws('s3api get-object help')
        self.assertEqual(p.rc, 1, p.stderr)
        self.assertIn('get-object', p.stdout)

    def test_param_shorthand(self):
        p = aws(
            'ec2 describe-instances --filters Name=instance-id,Values=i-123')
        self.assertEqual(p.rc, 0)
        self.assertIn('Reservations', p.json)

    def test_param_json(self):
        p = aws(
            'ec2 describe-instances --filters '
            '\'{"Name": "instance-id", "Values": ["i-123"]}\'')
        self.assertEqual(p.rc, 0, p.stdout + p.stderr)
        self.assertIn('Reservations', p.json)

    def test_param_with_bad_json(self):
        p = aws(
            'ec2 describe-instances --filters '
            '\'{"Name": "bad-filter", "Values": ["i-123"]}\'')
        self.assertEqual(p.rc, 1)
        self.assertIn("The filter 'bad-filter' is invalid", p.stdout,
                      "stdout: %s, stderr: %s" % (p.stdout, p.stderr))

    def test_param_with_file(self):
        d = tempfile.mkdtemp()
        self.addCleanup(os.rmdir, d)
        param_file = os.path.abspath(os.path.join(d, 'params.json'))
        with open(param_file, 'w') as f:
            f.write('[{"Name": "instance-id", "Values": ["i-123"]}]')
        self.addCleanup(os.remove, param_file)
        p = aws('ec2 describe-instances --filters file://%s' % param_file)
        self.assertEqual(p.rc, 0)
        self.assertIn('Reservations', p.json)

    def test_streaming_output_operation(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        bucket_name = 'clistream' + str(
            int(time.time())) + str(random.randint(1, 100))

        self.put_object(bucket=bucket_name, key='foobar',
                        content='foobar contents')
        p = aws('s3api get-object --bucket %s --key foobar %s' % (
            bucket_name, os.path.join(d, 'foobar')))
        self.assertEqual(p.rc, 0)
        with open(os.path.join(d, 'foobar')) as f:
            contents = f.read()
        self.assertEqual(contents, 'foobar contents')

    def test_top_level_options_debug(self):
        p = aws('ec2 describe-instances --debug')
        self.assertEqual(p.rc, 0)
        self.assertIn('DEBUG', p.stderr)

    def test_make_requests_to_other_region(self):
        p = aws('ec2 describe-instances --region us-west-2')
        self.assertEqual(p.rc, 0)
        self.assertIn('Reservations', p.json)

    def test_help_usage_top_level(self):
        p = aws('')
        self.assertIn('usage: aws [options] <service_name> '
                      '<operation> [parameters]', p.stderr)
        self.assertIn('too few arguments', p.stderr)

    def test_help_usage_service_level(self):
        p = aws('ec2')
        self.assertIn('usage: aws [options] <service_name> '
                      '<operation> [parameters]', p.stderr)
        self.assertIn('too few arguments', p.stderr)

    def test_help_usage_operation_level(self):
        p = aws('ec2 run-instances')
        self.assertIn('usage: aws [options] <service_name> '
                      '<operation> [parameters]', p.stderr)

    def test_unknown_argument(self):
        p = aws('ec2 describe-instances --filterss')
        self.assertEqual(p.rc, 255)
        self.assertIn('Unknown options: --filterss', p.stderr)

    def test_table_output(self):
        p = aws('ec2 describe-instances --output table --color off')
        # We're not testing the specifics of table output, we just want
        # to make sure the output looks like a table using some heuristics.
        # If this prints JSON instead of a table, for example, this test
        # should fail.
        self.assertEqual(p.rc, 0, p.stderr)
        self.assertIn('-----', p.stdout)
        self.assertIn('+-', p.stdout)
        self.assertIn('DescribeInstances', p.stdout)

    def test_version(self):
        p = aws('--version')
        self.assertEqual(p.rc, 0)
        self.assertTrue(p.stderr.startswith('aws-cli'), p.stderr)

    def test_traceback_printed_when_debug_on(self):
        p = aws('ec2 describe-instances --filters BADKEY=foo --debug')
        self.assertIn('Traceback (most recent call last):', p.stderr, p.stderr)
        # Also should see DEBUG statements:
        self.assertIn('DEBUG', p.stderr, p.stderr)

    def test_leftover_args_in_operation(self):
        p = aws('ec2 describe-instances BADKEY=foo')
        self.assertEqual(p.rc, 255)
        self.assertIn("Unknown option", p.stderr, p.stderr)


if __name__ == '__main__':
    unittest.main()
