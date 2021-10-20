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
import mock

from tests import BaseSessionTest, ClientHTTPStubber


class TestCloudsearchdomain(BaseSessionTest):
    def setUp(self):
        super(TestCloudsearchdomain, self).setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            'cloudsearchdomain', self.region)
        self.http_stubber = ClientHTTPStubber(self.client)

    def test_search(self):
        self.http_stubber.add_response(body=b'{}')
        with self.http_stubber:
            self.client.search(query='foo')
            request = self.http_stubber.requests[0]
            self.assertIn('q=foo', request.body)
            self.assertEqual(request.method, 'POST')
            content_type = b'application/x-www-form-urlencoded'
            self.assertEqual(request.headers.get('Content-Type'), content_type)
