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


class TestRDSPagination(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('rds')
        self.endpoint = self.service.get_endpoint('us-west-2')

    def test_can_paginate_reserved_instances(self):
        # Using an operation that we know will paginate.
        operation = self.service.get_operation('DescribeReservedDBInstancesOfferings')
        generator = operation.paginate(self.endpoint)
        results = list(itertools.islice(generator, 0, 3))
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0][1]['Marker'] != results[1][1]['Marker'])

    def test_can_paginate_orderable_db(self):
        operation = self.service.get_operation('DescribeOrderableDBInstanceOptions')
        generator = operation.paginate(self.endpoint, engine='mysql')
        results = list(itertools.islice(generator, 0, 2))
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0][1].get('Marker') != results[1][1].get('Marker'))


if __name__ == '__main__':
    unittest.main()
