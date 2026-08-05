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
import botocore.session
from tests import unittest


class TestClientMeta(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()

    def test_region_name_on_meta(self):
        client = self.session.create_client('s3', 'us-west-2')
        self.assertEqual(client.meta.region_name, 'us-west-2')

    def test_endpoint_url_on_meta(self):
        client = self.session.create_client(
            's3', 'us-west-2', endpoint_url='https://foo'
        )
        self.assertEqual(client.meta.endpoint_url, 'https://foo')

    def test_client_has_standard_partition_on_meta(self):
        client = self.session.create_client('s3', 'us-west-2')
        self.assertEqual(client.meta.partition, 'aws')

    def test_client_has_china_partition_on_meta(self):
        client = self.session.create_client('s3', 'cn-north-1')
        self.assertEqual(client.meta.partition, 'aws-cn')

    def test_client_has_gov_partition_on_meta(self):
        client = self.session.create_client('s3', 'us-gov-west-1')
        self.assertEqual(client.meta.partition, 'aws-us-gov')

    def test_client_has_no_partition_on_meta_if_custom_region(self):
        client = self.session.create_client('s3', 'myregion')
        self.assertEqual(client.meta.partition, 'aws')
