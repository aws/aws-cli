# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

from awscli.bcdoc.restdoc import ReSTDocument


class TestReSTDocument:
    @pytest.fixture
    def doc(self):
        return ReSTDocument()

    def _write_array(self, doc, arr):
        for elt in arr:
            doc.write(elt)

    def test_find_last_write(self, doc):
        self._write_array(doc, ['a', 'b', 'c', 'd', 'e'])
        expected_index = 0
        assert doc.find_last_write('a') == expected_index

    def test_find_last_write_duplicates(self, doc):
        self._write_array(doc, ['a', 'b', 'c', 'a', 'e'])
        expected_index = 3
        assert doc.find_last_write('a') == expected_index

    def test_find_last_write_not_found(self, doc):
        self._write_array(doc, ['a', 'b', 'c', 'd', 'e'])
        assert doc.find_last_write('f') is None

    def test_insert_write(self, doc):
        self._write_array(doc, ['foo', 'bar'])
        doc.insert_write(1, 'baz')
        assert doc.getvalue() == b'foobazbar'
