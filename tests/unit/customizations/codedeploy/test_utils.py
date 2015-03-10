# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import sys

from argparse import Namespace
from mock import MagicMock, patch
from awscli.customizations.codedeploy.utils import validate_s3_location

from awscli.testutils import unittest


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.region = 'us-east-1'
        self.arg_name = 's3-location'
        self.bucket = 'bucket'
        self.key = 'key'

        self.globals = MagicMock()
        self.session = MagicMock()
        self.params = Namespace()
        self.params.session = self.session

    def test_validate_s3_location_returns_bucket_key(self):
        self.params.s3_location = 's3://{0}/{1}'.format(self.bucket, self.key)
        validate_s3_location(self.params, self.arg_name)
        self.assertIn('bucket', self.params)
        self.assertEquals(self.bucket, self.params.bucket)
        self.assertIn('key', self.params)
        self.assertEquals(self.key, self.params.key)

    def test_validate_s3_location_not_present(self):
        validate_s3_location(self.params, 'unknown')
        self.assertNotIn('bucket', self.params)
        self.assertNotIn('key', self.params)

    def test_validate_s3_location_throws_on_invalid_location(self):
        self.params.s3_location = 'invalid-s3-location'
        with self.assertRaisesRegexp(
                ValueError,
                '--{0} must specify the Amazon S3 URL format as '
                's3://<bucket>/<key>.'.format(self.arg_name)):
            validate_s3_location(self.params, self.arg_name)


if __name__ == "__main__":
    unittest.main()
