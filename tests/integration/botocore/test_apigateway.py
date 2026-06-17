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
import time

import botocore.session
from botocore import exceptions
from tests import unittest


class TestApigateway(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('apigateway', 'us-east-1')

        # Create a resource to use with this client.
        self.api_name = 'mytestapi'
        self.api_id = self.create_rest_api_or_skip()

    def create_rest_api_or_skip(self):
        try:
            api_id = self.client.create_rest_api(name=self.api_name)['id']
        except exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'TooManyRequestsException':
                raise unittest.SkipTest(
                    "Hit API gateway throttle limit, skipping test."
                )
            raise
        return api_id

    def delete_api(self):
        retries = 0
        while retries < 10:
            try:
                self.client.delete_rest_api(restApiId=self.api_id)
                break
            except exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'TooManyRequestsException':
                    retries += 1
                    time.sleep(5)
                else:
                    raise

    def tearDown(self):
        self.delete_api()

    def test_put_integration(self):
        # The only resource on a brand new api is the path. So use that ID.
        path_resource_id = self.client.get_resources(restApiId=self.api_id)[
            'items'
        ][0]['id']

        # Create a method for the resource.
        self.client.put_method(
            restApiId=self.api_id,
            resourceId=path_resource_id,
            httpMethod='GET',
            authorizationType='None',
        )

        # Put an integration on the method.
        response = self.client.put_integration(
            restApiId=self.api_id,
            resourceId=path_resource_id,
            httpMethod='GET',
            type='HTTP',
            integrationHttpMethod='GET',
            uri='https://api.endpoint.com',
        )
        # Assert the response was successful by checking the integration type
        self.assertEqual(response['type'], 'HTTP')
