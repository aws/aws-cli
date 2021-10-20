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
from tests import unittest
import itertools

import botocore.session
from botocore.exceptions import ClientError


class TestEC2(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client(
            'ec2', region_name='us-west-2')

    def test_can_make_request(self):
        # Basic smoke test to ensure we can talk to ec2.
        result = self.client.describe_availability_zones()
        zones = list(
            sorted(a['ZoneName'] for a in result['AvailabilityZones']))
        self.assertTrue(
            set(['us-west-2a', 'us-west-2b', 'us-west-2c']).issubset(zones))

    def test_get_console_output_handles_error(self):
        # Want to ensure the underlying ClientError is propogated
        # on error.
        with self.assertRaises(ClientError):
            self.client.get_console_output(InstanceId='i-12345')


class TestEC2Pagination(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client(
            'ec2', region_name='us-west-2')

    def test_can_paginate(self):
        # Using an operation that we know will paginate.
        paginator = self.client.get_paginator(
            'describe_reserved_instances_offerings')
        pages = paginator.paginate()
        results = list(itertools.islice(pages, 0, 3))
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0]['NextToken'] != results[1]['NextToken'])

    def test_can_paginate_with_page_size(self):
        # Using an operation that we know will paginate.
        paginator = self.client.get_paginator(
            'describe_reserved_instances_offerings')
        pages = paginator.paginate(PaginationConfig={'PageSize': 1})
        results = list(itertools.islice(pages, 0, 3))
        self.assertEqual(len(results), 3)
        for parsed in results:
            reserved_inst_offer = parsed['ReservedInstancesOfferings']
            # There should be no more than  one reserved instance
            # offering on each page.
            self.assertLessEqual(len(reserved_inst_offer), 1)

    def test_can_fall_back_to_old_starting_token(self):
        # Using an operation that we know will paginate.
        paginator = self.client.get_paginator(
            'describe_reserved_instances_offerings')
        pages = paginator.paginate(PaginationConfig={'NextToken': 'None___1'})

        try:
            results = list(itertools.islice(pages, 0, 3))
            self.assertEqual(len(results), 3)
            self.assertTrue(results[0]['NextToken'] != results[1]['NextToken'])
        except ValueError:
            self.fail("Old style paginator failed.")


if __name__ == '__main__':
    unittest.main()
