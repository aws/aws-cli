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
<GetQueueAttributesResponse xmlns="http://queue.amazonaws.com/doc/2011-10-01/">
  <GetQueueAttributesResult>
    <Attribute>
      <Name>QueueArn</Name>
      <Value>arn:aws:sqs:us-east-1:419278470775:test1351044153</Value>
    </Attribute>
    <Attribute>
      <Name>ApproximateNumberOfMessages</Name>
      <Value>0</Value>
    </Attribute>
    <Attribute>
      <Name>ApproximateNumberOfMessagesNotVisible</Name>
      <Value>0</Value>
    </Attribute>
    <Attribute>
      <Name>ApproximateNumberOfMessagesDelayed</Name>
      <Value>0</Value>
    </Attribute>
    <Attribute>
      <Name>CreatedTimestamp</Name>
      <Value>1351044153</Value>
    </Attribute>
    <Attribute>
      <Name>LastModifiedTimestamp</Name>
      <Value>1351044214</Value>
    </Attribute>
    <Attribute>
      <Name>VisibilityTimeout</Name>
      <Value>45</Value>
    </Attribute>
    <Attribute>
      <Name>MaximumMessageSize</Name>
      <Value>65536</Value>
    </Attribute>
    <Attribute>
      <Name>MessageRetentionPeriod</Name>
      <Value>345600</Value>
    </Attribute>
    <Attribute>
      <Name>DelaySeconds</Name>
      <Value>0</Value>
  </Attribute>
  </GetQueueAttributesResult>
  <ResponseMetadata>
    <RequestId>0c8d2786-b7b4-56e2-a823-6e80a404d6fd</RequestId>
  </ResponseMetadata>
</GetQueueAttributesResponse>"""

data = {'Attributes': {'ApproximateNumberOfMessagesNotVisible': '0', 'MessageRetentionPeriod': '345600', 'ApproximateNumberOfMessagesDelayed': '0', 'MaximumMessageSize': '65536', 'CreatedTimestamp': '1351044153', 'ApproximateNumberOfMessages': '0', 'DelaySeconds': '0', 'VisibilityTimeout': '45', 'LastModifiedTimestamp': '1351044214', 'QueueArn': 'arn:aws:sqs:us-east-1:419278470775:test1351044153'}, 'ResponseMetadata': {'RequestId': '0c8d2786-b7b4-56e2-a823-6e80a404d6fd'}}


class TestGetQueueAttributes(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('sqs', 'aws')

    def test_get_queue_attributes(self):
        op = self.service.get_operation('GetQueueAttributes')
        r = botocore.response.XmlResponse(op)
        r.parse(six.b(xml))
        self.maxDiff = None
        self.assertEqual(r.get_value(), data)


if __name__ == "__main__":
    unittest.main()
