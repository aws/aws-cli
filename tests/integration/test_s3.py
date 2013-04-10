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
import time
from tests import unittest
from collections import defaultdict
try:
    from itertools import izip_longest as zip_longest
except ImportError:
    from itertools import zip_longest

import botocore.session


class BaseS3Test(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')


class TestS3(BaseS3Test):
    def test_can_make_request(self):
        # Basic smoke test to ensure we can talk to s3.
        operation = self.service.get_operation('ListBuckets')
        http, result = operation.call(self.endpoint)
        self.assertEqual(http.status_code, 200)
        # Can't really assume anything about whether or not they have buckets,
        # but we can assume something about the structure of the response.
        # TODO: implement this once the output structure is finalized.


class TestS3Pagination(BaseS3Test):

    def setUp(self):
        super(TestS3Pagination, self).setUp()
        self.bucket_name = 'botocoretest%s' % int(time.time())
        operation = self.service.get_operation('CreateBucket')
        operation.call(self.endpoint, bucket=self.bucket_name)
        self.keys = []

    def tearDown(self):
        for key in self.keys:
            operation = self.service.get_operation('DeleteObject')
            operation.call(self.endpoint, bucket=self.bucket_name,
                           key=key)
        operation = self.service.get_operation('DeleteBucket')
        operation.call(self.endpoint, bucket=self.bucket_name)

    def create_object(self, key_name):
        self.keys.append(key_name)
        operation = self.service.get_operation('PutObject')
        operation.call(self.endpoint, bucket=self.bucket_name, key=key_name,
                       body='foo')

    def test_can_paginate(self):
        for i in range(5):
            key_name = 'key%s' % i
            self.create_object(key_name)
        operation = self.service.get_operation('ListObjects')
        generator = operation.paginate(self.endpoint, max_keys=1,
                                       bucket=self.bucket_name)
        responses = list(generator)
        self.assertEqual(len(responses), 5)
        data = [r[1] for r in responses]
        key_names = [el['Contents'][0]['Key']
                     for el in data]
        self.assertEqual(key_names, ['key0', 'key1', 'key2', 'key3', 'key4'])

    def test_result_key_iters(self):
        for i in range(5):
            key_name = 'key/%s/%s' % (i, i)
            self.create_object(key_name)
            key_name2 = 'key/%s' % i
            self.create_object(key_name2)
        operation = self.service.get_operation('ListObjects')
        generator = operation.paginate(self.endpoint, max_keys=2,
                                       prefix='key/',
                                       delimiter='/',
                                       bucket=self.bucket_name)
        iterators = generator.result_key_iters()
        response = defaultdict(list)
        key_names = [i.result_key for i in iterators]
        for vals in zip_longest(*iterators):
            for k, val in zip(key_names, vals):
                response[k].append(val)
        self.assertIn('Contents', response)
        self.assertIn('CommonPrefixes', response)


if __name__ == '__main__':
    unittest.main()
