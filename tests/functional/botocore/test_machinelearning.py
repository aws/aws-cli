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
from tests import BaseSessionTest, ClientHTTPStubber


class TestMachineLearning(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            'machinelearning', self.region
        )
        self.http_stubber = ClientHTTPStubber(self.client)

    def test_predict(self):
        self.http_stubber.add_response(body=b'{}')
        with self.http_stubber:
            custom_endpoint = 'https://myendpoint.amazonaws.com/'
            self.client.predict(
                MLModelId='ml-foo',
                Record={'Foo': 'Bar'},
                PredictEndpoint=custom_endpoint,
            )
            sent_request = self.http_stubber.requests[0]
            self.assertEqual(sent_request.url, custom_endpoint)
