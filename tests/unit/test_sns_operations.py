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
import botocore.session


class TestSNSOperations(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.sns = self.session.get_service('sns')

    def test_subscribe_with_endpoint(self):
        op = self.sns.get_operation('Subscribe')
        # There's an override for endpoint, so we need to make sure
        # notification_endpoint gets mapped to Endpoint.
        params = op.build_parameters(topic_arn='topic_arn',
                                     protocol='http',
                                     notification_endpoint='http://example.org')
        self.assertEqual(params['Endpoint'], 'http://example.org')


if __name__ == "__main__":
    unittest.main()
