# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.exceptions import ClientError


class TestCloudformation(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('cloudformation', 'us-east-1')

    def test_handles_errors_with_template_body(self):
        # GetTemplate has a customization in handlers.py, so we're ensuring
        # it handles the case when a stack does not exist.
        with self.assertRaises(ClientError):
            self.client.get_template(
                StackName='does-not-exist-%s' % random_chars(10))


if __name__ == '__main__':
    unittest.main()
