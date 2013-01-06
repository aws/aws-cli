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
import os
import botocore.session
import botocore.exceptions


class TestConfig(unittest.TestCase):

    def setUp(self):
        data_path = os.path.join(os.path.dirname(__file__), 'data')
        os.environ['BOTO_DATA_PATH'] = data_path
        self.session = botocore.session.get_session()

    def test_data_not_found(self):
        self.assertRaises(botocore.exceptions.DataNotFoundError,
                          self.session.get_data, 'bar')

    def test_data_bad(self):
        self.assertRaises(botocore.exceptions.DataNotFoundError,
                          self.session.get_data, 'baz')

    def test_all_data(self):
        data = self.session.get_data('foo')
        assert 'test_key_1' in data
        assert 'test_key_2' in data

    def test_not_there(self):
        self.assertRaises(botocore.exceptions.DataNotFoundError,
                          self.session.get_data,
                          'foo/test_key_4')

    def test_sub_data(self):
        data = self.session.get_data('foo/test_key_2')
        assert len(data) == 2
        assert 'test_value_2_1' in data
        assert 'test_value_2_2' in data

    def test_sublist_data(self):
        data = self.session.get_data('foo/test_key_3/test_list_2')
        assert 'name' in data
        assert data['name'] == 'test_list_2'
        assert 'value' in data
        assert data['value'] == 'test_list_value_2'



if __name__ == "__main__":
    unittest.main()
