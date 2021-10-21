# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from tests import unittest, random_chars

import botocore.session

DEFAULT_ROLE_POLICY = """\
{"Statement": [
    {
        "Action": "sts:AssumeRole",
        "Principal": {
            "Service": "elastictranscoder.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": "1"
    }
]}
"""

class TestElasticTranscoder(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client(
            'elastictranscoder', 'us-east-1')
        self.s3_client = self.session.create_client('s3', 'us-east-1')
        self.iam_client = self.session.create_client('iam', 'us-east-1')

    def create_bucket(self):
        bucket_name = 'ets-bucket-1-%s' % random_chars(50)
        self.s3_client.create_bucket(Bucket=bucket_name)
        waiter = self.s3_client.get_waiter('bucket_exists')
        waiter.wait(Bucket=bucket_name)
        self.addCleanup(
            self.s3_client.delete_bucket, Bucket=bucket_name)
        return bucket_name

    def create_iam_role(self):
        role_name = 'ets-role-name-1-%s' % random_chars(10)
        parsed = self.iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=DEFAULT_ROLE_POLICY)
        arn = parsed['Role']['Arn']
        self.addCleanup(
            self.iam_client.delete_role, RoleName=role_name)
        return arn

    def test_list_streams(self):
        parsed = self.client.list_pipelines()
        self.assertIn('Pipelines', parsed)

    def test_list_presets(self):
        parsed = self.client.list_presets(Ascending='true')
        self.assertIn('Presets', parsed)

    def test_create_pipeline(self):
        # In order to create a pipeline, we need to create 2 s3 buckets
        # and 1 iam role.
        input_bucket = self.create_bucket()
        output_bucket = self.create_bucket()
        role = self.create_iam_role()
        pipeline_name = 'botocore-test-create-%s' % random_chars(10)

        parsed = self.client.create_pipeline(
            InputBucket=input_bucket, OutputBucket=output_bucket,
            Role=role, Name=pipeline_name,
            Notifications={'Progressing': '', 'Completed': '',
                           'Warning': '', 'Error': ''})
        pipeline_id = parsed['Pipeline']['Id']
        self.addCleanup(self.client.delete_pipeline, Id=pipeline_id)
        self.assertIn('Pipeline', parsed)


if __name__ == '__main__':
    unittest.main()
