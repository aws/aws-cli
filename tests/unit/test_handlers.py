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
from tests import unittest
import botocore.session
from botocore.hooks import first_non_none_response
from botocore.compat import quote
import base64
import six


class TestHandlers(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()

    def tearDown(self):
        pass

    def test_get_console_output(self):
        event = self.session.create_event('after-parsed', 'ec2',
                                          'GetConsoleOutput',
                                          'String', 'Output')
        value = base64.b64encode(six.b('foobar'))
        rv = self.session.emit(event, shape={}, value=value)
        converted_value = first_non_none_response(rv)
        self.assertEqual(converted_value, 'foobar')

    def test_decode_quoted_jsondoc(self):
        event = self.session.create_event('after-parsed', 'iam',
                                          'GetUserPolicy',
                                          'policyDocumentType',
                                          'PolicyDocument')
        value = quote('{"foo":"bar"}')
        rv = self.session.emit(event, shape={}, value=value)
        converted_value = first_non_none_response(rv)
        self.assertEqual(converted_value, {'foo':'bar'})

    def test_decode_jsondoc(self):
        event = self.session.create_event('after-parsed', 'cloudformation',
                                          'GetTemplate',
                                          'TemplateBody',
                                          'TemplateBody')
        value = '{"foo":"bar"}'
        rv = self.session.emit(event, shape={}, value=value)
        converted_value = first_non_none_response(rv)
        self.assertEqual(converted_value, {'foo':'bar'})



if __name__ == '__main__':
    unittest.main()
