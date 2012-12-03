#!/usr/bin/env
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
import botocore.parameters
import botocore.exceptions


class TimestampTest(unittest.TestCase):

    def test_timestamp(self):
        p = botocore.parameters.TimestampParameter(name='foo')
        d = {}
        ts = '2012-10-12T00:00'
        p.build_parameter(ts, d)
        assert d['foo'] == ts
        ts = '2012-10-1200:00'
        with self.assertRaises(botocore.exceptions.ValidationError):
            p.build_parameter(ts, d)

    def test_integer(self):
        p = botocore.parameters.IntegerParameter(name='foo')
        d = {}
        p.build_parameter('123', d)
        assert d['foo'] == '123'
        with self.assertRaises(botocore.exceptions.ValidationError):
            p.build_parameter('123.4', d)

    def test_integer_range(self):
        p = botocore.parameters.IntegerParameter(name='foo', min=0, max=10)
        d = {}
        p.build_parameter('9', d)
        assert d['foo'] == '9'
        with self.assertRaises(botocore.exceptions.ValidationError):
            p.build_parameter('8.4', d)
        with self.assertRaises(botocore.exceptions.RangeError):
            p.build_parameter('100', d)

    def test_float(self):
        p = botocore.parameters.FloatParameter(name='foo')
        d = {}
        p.build_parameter('123.4', d)
        assert d['foo'] == '123.4'
        with self.assertRaises(botocore.exceptions.ValidationError):
            p.build_parameter('true', d)

    def test_float_range(self):
        p = botocore.parameters.FloatParameter(name='foo', min=0, max=10)
        d = {}
        p.build_parameter('9.0', d)
        assert d['foo'] == '9.0'
        with self.assertRaises(botocore.exceptions.RangeError):
            p.build_parameter('100', d)

    def test_boolean(self):
        p = botocore.parameters.BooleanParameter(name='foo')
        d = {}
        p.build_parameter('true', d)
        assert d['foo'] == 'true'
        p.build_parameter('True', d)
        assert d['foo'] == 'true'
        p.build_parameter('TRUE', d)
        assert d['foo'] == 'true'
        p.build_parameter('false', d)
        assert d['foo'] == 'false'
        p.build_parameter('False', d)
        assert d['foo'] == 'false'
        p.build_parameter('FALSE', d)
        assert d['foo'] == 'false'
        with self.assertRaises(botocore.exceptions.ValidationError):
            p.build_parameter('100', d)


if __name__ == "__main__":
    unittest.main()
