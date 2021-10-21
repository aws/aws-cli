# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import BaseSessionTest, ClientHTTPStubber
from botocore.exceptions import UnknownFIPSEndpointError


class TestBlockFIPS(BaseSessionTest):
    def _make_client(self, service, region):
        client = self.session.create_client(service, region)
        http_stubber = ClientHTTPStubber(client)
        http_stubber.add_response(body=b'{}')
        return client, http_stubber

    def test_allows_known_fips_pseudo_regions_api_call(self):
        region = 'fips-us-east-1'
        client, http_stubber = self._make_client('accessanalyzer', region)
        with http_stubber:
            client.list_analyzers()

    def test_allows_known_fips_pseudo_regions_presign(self):
        region = 'fips-us-east-1'
        client, _ = self._make_client('accessanalyzer', region)
        url = client.generate_presigned_url('list_analyzers', Params={})
        self.assertIn('access-analyzer-fips', url)

    def test_allows_known_fips_pseudo_regions_presign_post(self):
        region = 'fips-us-gov-west-1'
        client, _ = self._make_client('s3', region)
        post = client.generate_presigned_post('foo-bucket', 'foo-key')
        self.assertIn('s3-fips', post['url'])

    def test_allows_general_client_function(self):
        region = 'fips-us-gov-weast-1'
        client, _ = self._make_client('accessanalyzer', region)
        can_paginate = client.can_paginate('list_analyzers')
        self.assertTrue(can_paginate)

    def test_blocks_unknown_fips_pseudo_regions_api_call(self):
        region = 'FIPS-us-weast-1'
        client, http_stubber = self._make_client('accessanalyzer', region)
        with http_stubber:
            with self.assertRaises(UnknownFIPSEndpointError):
                client.list_analyzers()

    def test_blocks_unknown_fips_pseudo_regions_presign(self):
        region = 'us-weast-1-fips'
        client, _ = self._make_client('accessanalyzer', region)
        with self.assertRaises(UnknownFIPSEndpointError):
            url = client.generate_presigned_url('list_analyzers', Params={})

    def test_blocks_unknown_fips_pseudo_regions_presign_post(self):
        region = 'fips-us-gov-weast-1'
        client, _ = self._make_client('s3', region)
        with self.assertRaises(UnknownFIPSEndpointError):
            post = client.generate_presigned_post('foo-bucket', 'foo-key')
