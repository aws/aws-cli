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
from tests import unittest

import botocore.session


class TestCanChangeParsing(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()

    def test_can_change_timestamp_with_clients(self):
        factory = self.session.get_component('response_parser_factory')
        factory.set_parser_defaults(timestamp_parser=lambda x: str(x))

        # Now if we get a response with timestamps in the model, they
        # will be returned as strings. We're testing service/operation
        # objects, but we should also add a test for clients.
        s3 = self.session.create_client('s3', 'us-west-2')
        parsed = s3.list_buckets()
        dates = [bucket['CreationDate'] for bucket in parsed['Buckets']]
        self.assertTrue(all(isinstance(date, str) for date in dates),
                        "Expected all str types but instead got: %s" % dates)

    def test_maps_service_name_when_overriden(self):
        ses = self.session.get_service_model('ses')
        self.assertEqual(ses.endpoint_prefix, 'email')
        # But we should map the service_name to be the same name
        # used when calling get_service_model which is different
        # than the endpoint_prefix.
        self.assertEqual(ses.service_name, 'ses')

    def test_maps_service_name_from_client(self):
        # Same thing as test_maps_service_name_from_client,
        # except through the client interface.
        client = self.session.create_client('ses', region_name='us-east-1')
        self.assertEqual(client.meta.service_model.service_name, 'ses')
