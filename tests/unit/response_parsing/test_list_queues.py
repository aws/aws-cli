#!/usr/bin/env python
# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import botocore.session
import botocore.response

xml = """<?xml version="1.0"?>
<ListQueuesResponse xmlns="http://queue.amazonaws.com/doc/2011-10-01/">
  <ListQueuesResult>
    <QueueUrl>https://queue.amazonaws.com/419278470775/blat</QueueUrl>
    <QueueUrl>https://queue.amazonaws.com/419278470775/test1348104148</QueueUrl>
    <QueueUrl>https://queue.amazonaws.com/419278470775/test1348112370</QueueUrl>
    <QueueUrl>https://queue.amazonaws.com/419278470775/test1351037239</QueueUrl>
    <QueueUrl>https://queue.amazonaws.com/419278470775/test1351044153</QueueUrl>
    <QueueUrl>https://queue.amazonaws.com/419278470775/testcli</QueueUrl>
  </ListQueuesResult>
  <ResponseMetadata>
    <RequestId>6447266c-d0e0-5c10-8e26-6f57c3adec51</RequestId>
  </ResponseMetadata>
</ListQueuesResponse>"""

data = {u'QueueUrl': [u'https://queue.amazonaws.com/419278470775/blat', u'https://queue.amazonaws.com/419278470775/test1348104148', u'https://queue.amazonaws.com/419278470775/test1348112370', u'https://queue.amazonaws.com/419278470775/test1351037239', u'https://queue.amazonaws.com/419278470775/test1351044153', u'https://queue.amazonaws.com/419278470775/testcli'], u'ResponseMetadata': {u'RequestId': u'6447266c-d0e0-5c10-8e26-6f57c3adec51'}}


class TestListQueuesAttributes(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('sqs', 'aws')

    def test_list_queues(self):
        op = self.service.get_operation('ListQueues')
        r = botocore.response.Response(op)
        r.parse(xml)
        print r.get_value()
        self.assertEqual(r.get_value(), data)


if __name__ == "__main__":
    unittest.main()
