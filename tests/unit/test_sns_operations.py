#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from mock import Mock, sentinel

import botocore.session


class TestSNSOperations(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.sns = self.session.get_service('sns')

    def test_subscribe_with_endpoint(self):
        op = self.sns.get_operation('Subscribe')
        params = op.build_parameters(topic_arn='topic_arn',
                                     protocol='http',
                                     notification_endpoint='http://example.org')
        self.assertEqual(params['Endpoint'], 'http://example.org')

    def test_sns_pre_send_event(self):
        op = self.sns.get_operation('Subscribe')
        calls = []
        self.session.register('before-call.sns.Subscribe',
                              lambda **kwargs: calls.append(kwargs))
        endpoint = Mock()
        endpoint.make_request.return_value = (sentinel.RESPONSE,
                                              sentinel.PARSED)
        op.call(endpoint=endpoint, topic_arn='topic_arn', protocol='http',
                notification_endpoint='http://example.org')
        self.assertEqual(len(calls), 1)
        kwargs = calls[0]
        self.assertEqual(kwargs['operation'], op)
        self.assertEqual(kwargs['endpoint'], endpoint)
        self.assertEqual(kwargs['params']['topic_arn'], 'topic_arn')

    def test_sns_post_send_event_is_invoked(self):
        op = self.sns.get_operation('Subscribe')
        calls = []
        self.session.register('after-call.sns.Subscribe',
                              lambda **kwargs: calls.append(kwargs))
        endpoint = Mock()
        endpoint.make_request.return_value = (sentinel.RESPONSE,
                                              sentinel.PARSED)
        op.call(endpoint=endpoint, topic_arn='topic_arn', protocol='http',
                notification_endpoint='http://example.org')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['operation'], op)
        self.assertEqual(calls[0]['http_response'], sentinel.RESPONSE)
        self.assertEqual(calls[0]['parsed'], sentinel.PARSED)


if __name__ == "__main__":
    unittest.main()
