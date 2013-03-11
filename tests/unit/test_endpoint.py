# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

from tests import unittest

from mock import Mock
from botocore.endpoint import get_endpoint, QueryEndpoint, JSONEndpoint, \
    RestEndpoint
from botocore.auth import SigV4Auth
from botocore.exceptions import UnknownServiceStyle
from botocore.exceptions import UnknownSignatureVersionError


class TestGetEdnpoint(unittest.TestCase):
    def create_mock_service(self, service_type, signature_version='v2'):
        service = Mock()
        service.type = service_type
        service.signature_version = signature_version
        return service

    def test_get_query(self):
        service = self.create_mock_service('query')
        endpoint = get_endpoint(service, 'us-west-2',
                                'https://service.region.amazonaws.com')
        self.assertIsInstance(endpoint, QueryEndpoint)

    def test_get_json(self):
        service = self.create_mock_service('json')
        endpoint = get_endpoint(service, 'us-west-2',
                                'https://service.region.amazonaws.com')
        self.assertIsInstance(endpoint, JSONEndpoint)

    def test_get_rest_xml(self):
        service = self.create_mock_service('rest-xml')
        endpoint = get_endpoint(service, 'us-west-2',
                                'https://service.region.amazonaws.com')
        self.assertIsInstance(endpoint, RestEndpoint)

    def test_get_rest_json(self):
        service = self.create_mock_service('rest-json')
        endpoint = get_endpoint(service, 'us-west-2',
                                'https://service.region.amazonaws.com')
        self.assertIsInstance(endpoint, RestEndpoint)

    def test_unknown_service(self):
        service = self.create_mock_service('rest-query-xml-json')
        with self.assertRaises(UnknownServiceStyle):
            endpoint = get_endpoint(service, 'us-west-2',
                                    'https://service.region.amazonaws.com')

    def test_auth_is_properly_created_for_endpoint(self):
        service = self.create_mock_service('query', signature_version='v4')
        endpoint = get_endpoint(service, 'us-west-2',
                                'https://service.region.amazonaws.com')
        self.assertIsInstance(endpoint.auth, SigV4Auth)

    def test_unknown_auth_handler(self):
        service = self.create_mock_service('query', signature_version='v5000')
        with self.assertRaises(UnknownSignatureVersionError):
            endpoint = get_endpoint(service, 'us-west-2',
                                    'https://service.region.amazonaws.com')


if __name__ == '__main__':
    unittest.main()
