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
import logging
import os
import tempfile
import shutil

import botocore.session

from awscli.testutils import unittest, aws, random_bucket_name


LOG = logging.getLogger(__name__)
_SHARED_BUCKET = random_bucket_name()
_DEFAULT_REGION = 'us-west-2'


def setup_module():
    s3 = botocore.session.get_session().create_client('s3')
    waiter = s3.get_waiter('bucket_exists')
    params = {
        'Bucket': _SHARED_BUCKET,
        'CreateBucketConfiguration': {
            'LocationConstraint': _DEFAULT_REGION,
        }
    }
    try:
        s3.create_bucket(**params)
    except Exception as e:
        # A create_bucket can fail for a number of reasons.
        # We're going to defer to the waiter below to make the
        # final call as to whether or not the bucket exists.
        LOG.debug("create_bucket() raised an exception: %s", e, exc_info=True)
    waiter.wait(Bucket=_SHARED_BUCKET)


def clear_out_bucket(bucket, delete_bucket=False):
    s3 = botocore.session.get_session().create_client(
        's3', region_name=_DEFAULT_REGION)
    page = s3.get_paginator('list_objects')
    # Use pages paired with batch delete_objects().
    for page in page.paginate(Bucket=bucket):
        keys = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
        if keys:
            s3.delete_objects(Bucket=bucket, Delete={'Objects': keys})
    if delete_bucket:
        try:
            s3.delete_bucket(Bucket=bucket)
        except Exception as e:
            # We can sometimes get exceptions when trying to
            # delete a bucket.  We'll let the waiter make
            # the final call as to whether the bucket was able
            # to be deleted.
            LOG.debug("delete_bucket() raised an exception: %s",
                      e, exc_info=True)
            waiter = s3.get_waiter('bucket_not_exists')
            waiter.wait(Bucket=bucket)


def teardown_module():
    clear_out_bucket(_SHARED_BUCKET, delete_bucket=True)


class TestIntegCliInputJson(unittest.TestCase):
    """This tests to see if a service properly uses the generated input JSON.

    The s3 service was chosen becuase its operations do not take a lot of time.
    These tests are essentially smoke tests. They are testing that the
    ``--cli-input-json`` works. It is by no means exhaustive.
    """
    def setUp(self):
        self.session = botocore.session.get_session()
        self.region = _DEFAULT_REGION

        # Set up a s3 bucket.
        self.s3 = self.session.create_client('s3', region_name=self.region)
        self.bucket_name = _SHARED_BUCKET

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
