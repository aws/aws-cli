# Copyright 2012-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.servicecatalog import utils
from awscli.testutils import unittest


class TestUtils(unittest.TestCase):

    def test_make_url_no_version(self):
        url = utils.make_url('us-east-1', 'foo-bucket-name', 'a/b/c', None)
        self.assertEqual("https://s3.amazonaws.com/foo-bucket-name/a/b/c", url)

    def test_make_url_no_version_other_region(self):
        url = utils.make_url('us-west-2', 'foo-bucket-name', 'a/b/c', None)
        self.assertEqual(
            "https://s3-us-west-2.amazonaws.com/foo-bucket-name/a/b/c",
            url)

    def test_make_url_with_version(self):
        url = utils.make_url('us-east-1', 'foo-bucket-name', 'a/b/c', 5)
        self.assertEqual(
            "https://s3.amazonaws.com/foo-bucket-name/a/b/c?versionId=5",
            url)
