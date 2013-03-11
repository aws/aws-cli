#!/usr/bin/env python
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import six
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

data = {'QueueUrls': ['https://queue.amazonaws.com/419278470775/blat', 'https://queue.amazonaws.com/419278470775/test1348104148', 'https://queue.amazonaws.com/419278470775/test1348112370', 'https://queue.amazonaws.com/419278470775/test1351037239', 'https://queue.amazonaws.com/419278470775/test1351044153', 'https://queue.amazonaws.com/419278470775/testcli'], 'ResponseMetadata': {'RequestId': '6447266c-d0e0-5c10-8e26-6f57c3adec51'}}


class TestListQueuesAttributes(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('sqs', 'aws')

    def test_list_queues(self):
        op = self.service.get_operation('ListQueues')
        r = botocore.response.XmlResponse(op)
        r.parse(six.b(xml))
        self.maxDiff = None
        self.assertEqual(r.get_value(), data)


if __name__ == "__main__":
    unittest.main()
