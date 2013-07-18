#!/usr/bin/env
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
from tests import unittest
import botocore.parameters
import botocore.payload
from botocore.compat import json

XML_BODY1 = """<foobar xmlns="http://foobar.com/"><foo>value1</foo><bar>value2</bar></foobar>"""
XML_BODY2 = """<foo>value1</foo>"""


class TestPayloads(unittest.TestCase):

    def test_json_payload_scalar(self):
        payload = botocore.payload.JSONPayload()
        p = botocore.parameters.StringParameter(None, name='foo')
        payload.add_param(p, 'value1')
        p = botocore.parameters.StringParameter(None, name='bar')
        payload.add_param(p, 'value2')
        json_body = json.loads(payload.getvalue())
        params = {"foo": "value1", "bar": "value2"}
        self.assertEqual(json_body, params)

    def test_json_payload_list(self):
        payload = botocore.payload.JSONPayload()
        p = botocore.parameters.ListParameter(None, name='foo')
        p.members = {'type': 'string'}
        p.handle_subtypes()
        value = ['This', 'is', 'a', 'test']
        payload.add_param(p, value)
        json_body = json.loads(payload.getvalue())
        params = {"foo": ["This", "is", "a", "test"]}
        self.assertEqual(json_body, params)

    def test_xml_payload_scalar(self):
        payload = botocore.payload.XMLPayload(root_element_name='foobar',
                                              namespace='http://foobar.com/')
        p = botocore.parameters.StringParameter(None, name='foo')
        payload.add_param(p, 'value1')
        p = botocore.parameters.StringParameter(None, name='bar')
        payload.add_param(p, 'value2')
        xml_body = payload.getvalue()
        self.assertEqual(xml_body, XML_BODY1)

    def test_xml_payload_scalar_no_root(self):
        payload = botocore.payload.XMLPayload(root_element_name=None)
        p = botocore.parameters.StringParameter(None, name='foo')
        payload.add_param(p, 'value1')
        p = botocore.parameters.StringParameter(None, name='bar')
        payload.add_param(p, 'value2')
        xml_body = payload.getvalue()
        self.assertEqual(xml_body, XML_BODY2)

if __name__ == "__main__":
    unittest.main()
