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
import unittest
import itertools

import botocore.session


class TestEC2(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()

    def test_can_make_request(self):
        # Basic smoke test to ensure we can talk to ec2.
        service = self.session.get_service('ec2')
        endpoint = service.get_endpoint('us-west-2')
        operation = service.get_operation('DescribeAvailabilityZones')
        http, result = operation.call(endpoint)
        zones = list(sorted(a['ZoneName'] for a in result['AvailabilityZones']))
        self.assertEqual(zones, ['us-west-2a', 'us-west-2b', 'us-west-2c'])


class TestEC2Pagination(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('ec2')
        self.endpoint = self.service.get_endpoint('us-west-2')

    def test_can_paginate(self):
        # Using an operation that we know will paginate.
        operation = self.service.get_operation('DescribeReservedInstancesOfferings')
        generator = operation.paginate(self.endpoint)
        results = list(itertools.islice(generator, 0, 3))
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0][1]['NextToken'] != results[1][1]['NextToken'])


if __name__ == '__main__':
    unittest.main()
