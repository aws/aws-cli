# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import time
import tempfile
import random
import shutil

import botocore.session

from awscli.testutils import unittest, aws


class TestIntegCliInputJson(unittest.TestCase):
    """This tests to see if a service properly uses the generated input JSON.

    The s3 service was chosen becuase its operations do not take a lot of time.
    These tests are essentially smoke tests. They are testing that the
    ``--cli-input-json`` works. It is by no means exhaustive.
    """
    def setUp(self):
        self.session = botocore.session.get_session()
        self.region = 'us-west-2'

        # Set up a s3 bucket.
        self.s3 = self.session.create_client('s3', region_name=self.region)
        self.bucket_name = 'cliinputjsontest%s-%s' % (
            int(time.time()), random.randint(1, 1000000))
        self.s3.create_bucket(
            Bucket=self.bucket_name,
            CreateBucketConfiguration={'LocationConstraint': self.region}
        )

        # Add an object to the bucket.
        self.obj_name = 'foo'
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=self.obj_name,
            Body='bar'
        )

        # Create a temporary sample input json file.
        self.input_json = '{"Bucket": "%s", "Key": "%s"}' % \
            (self.bucket_name, self.obj_name)

        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, 'foo.json')
        with open(self.temp_file, 'w') as f:
            f.write(self.input_json)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        self.s3.delete_object(
            Bucket=self.bucket_name,
            Key=self.obj_name
        )
        self.s3.delete_bucket(Bucket=self.bucket_name)

    def test_cli_input_json_no_exta_args(self):
        # Run a head command using the input json
        p = aws('s3api head-object --cli-input-json file://%s --region %s'
                % (self.temp_file, self.region))
        # The head object command should find the object specified by the
        # input json file.
        self.assertEqual(p.rc, 0)

    def test_cli_input_json_exta_args(self):
        # Check that the object can be found.
        p = aws('s3api head-object --cli-input-json file://%s --region %s'
                % (self.temp_file, self.region))
        self.assertEqual(p.rc, 0)

        # Override the ``key`` argument. Should produce a failure because
        # the key ``bar`` does not exist.
        p = aws('s3api head-object --key bar --cli-input-json file://%s '
                '--region %s'
                % (self.temp_file, self.region))
        self.assertEqual(p.rc, 255)
        self.assertIn('Not Found', p.stderr)

    def test_cli_input_json_not_from_file(self):
        # Check that the input json can be used without having to use a file.
        p = aws(
            's3api head-object --region %s --cli-input-json '
            '\'{"Bucket": "%s", "Key": "%s"}\'' %
            (self.region, self.bucket_name, self.obj_name))
        self.assertEqual(p.rc, 0)

    def test_cli_input_json_missing_required(self):
        # Check that the operation properly throws an error if the json is
        # missing any required arguments and the argument is not on the
        # command line.
        p = aws(
            's3api head-object --region %s --cli-input-json '
            '\'{"Key": "%s"}\'' %
            (self.region, self.obj_name))
        self.assertEqual(p.rc, 255)
        self.assertIn('Missing', p.stderr)

    def test_cli_input_json_has_extra_unknown_args(self):
        # Check that the operation properly throws an error if the json
        # has an extra argument that is not defined by the model.
        p = aws(
            's3api head-object --region %s --cli-input-json '
            '\'{"Bucket": "%s", "Key": "%s", "Foo": "bar"}\'' %
            (self.region, self.bucket_name, self.obj_name))
        self.assertEqual(p.rc, 255)
        self.assertIn('Unknown', p.stderr)
