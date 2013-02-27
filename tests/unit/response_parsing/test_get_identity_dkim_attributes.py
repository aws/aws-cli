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

xml = """<GetIdentityDkimAttributesResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <GetIdentityDkimAttributesResult>
    <DkimAttributes>
      <entry>
        <key>amazon.com</key>
	<value>
          <DkimEnabled>true</DkimEnabled>
          <DkimVerificationStatus>Success</DkimVerificationStatus>
          <DkimTokens>
            <member>vvjuipp74whm76gqoni7qmwwn4w4qusjiainivf6f</member>
            <member>3frqe7jn4obpuxjpwpolz6ipb3k5nvt2nhjpik2oy</member>
            <member>wrqplteh7oodxnad7hsl4mixg2uavzneazxv5sxi2</member>
          </DkimTokens>
	</value>
      </entry>
    </DkimAttributes>
  </GetIdentityDkimAttributesResult>
  <ResponseMetadata>
    <RequestId>bb5a105d-c468-11e1-82eb-dff885ccc06a</RequestId>
  </ResponseMetadata>
</GetIdentityDkimAttributesResponse>"""

data = {'DkimAttributes': {'amazon.com': {'DkimTokens': ['vvjuipp74whm76gqoni7qmwwn4w4qusjiainivf6f', '3frqe7jn4obpuxjpwpolz6ipb3k5nvt2nhjpik2oy', 'wrqplteh7oodxnad7hsl4mixg2uavzneazxv5sxi2'], 'DkimEnabled': True, 'DkimVerificationStatus': 'Success'}}, 'ResponseMetadata': {'RequestId': 'bb5a105d-c468-11e1-82eb-dff885ccc06a'}}


class TestGetIdentityDkimAttributes(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('ses', 'aws')

    def test_get_identity_dkim_attributes(self):
        op = self.service.get_operation('GetIdentityDkimAttributes')
        r = botocore.response.XmlResponse(op)
        r.parse(six.b(xml))
        self.assertEqual(r.get_value(), data)


if __name__ == "__main__":
    unittest.main()
