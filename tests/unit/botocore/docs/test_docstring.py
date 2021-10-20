# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from tests import unittest, mock
from botocore.docs.docstring import LazyLoadedDocstring
from botocore.docs.docstring import ClientMethodDocstring
from botocore.docs.docstring import WaiterDocstring
from botocore.docs.docstring import PaginatorDocstring


class MockedLazyLoadedDocstring(LazyLoadedDocstring):
    def __init__(self, *args, **kwargs):
        super(MockedLazyLoadedDocstring, self).__init__(*args, **kwargs)
        self.mocked_writer_method = mock.Mock()

    def _write_docstring(self, *args, **kwargs):
        self.mocked_writer_method(*args, **kwargs)


class TestLazyLoadedDocstring(unittest.TestCase):
    def test_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            str(LazyLoadedDocstring())

    def test_expandtabs(self):
        docstring = MockedLazyLoadedDocstring()
        docstring.mocked_writer_method.side_effect = (
            lambda section: section.write('foo\t'))
        self.assertEqual('foo ', docstring.expandtabs(1))

    def test_str(self):
        docstring = MockedLazyLoadedDocstring()
        docstring.mocked_writer_method.side_effect = (
            lambda section: section.write('foo'))
        self.assertEqual('foo', str(docstring))

    def test_repr(self):
        docstring = MockedLazyLoadedDocstring()
        docstring.mocked_writer_method.side_effect = (
            lambda section: section.write('foo'))
        self.assertEqual('foo', repr(docstring))

    def test_is_lazy_loaded(self):
        docstring = MockedLazyLoadedDocstring()
        str(docstring)
        str(docstring)
        # The mock.ANY represents the DocumentStructure that is filled out.
        docstring.mocked_writer_method.assert_called_once_with(mock.ANY)

    def test_args_kwargs_passed(self):
        args = ['foo', 'bar']
        kwargs = {'biz': 'baz'}
        docstring = MockedLazyLoadedDocstring(*args, **kwargs)
        str(docstring)
        # The mock.ANY represents the DocumentStructure that is filled out.
        docstring.mocked_writer_method.assert_called_with(
            mock.ANY, *args, **kwargs)


class TestClientMethodDocstring(unittest.TestCase):
    def test_use_correct_docstring_writer(self):
        with mock.patch(
                'botocore.docs.docstring'
                '.document_model_driven_method') as mock_writer:
            docstring = ClientMethodDocstring()
            str(docstring)
            self.assertTrue(mock_writer.called)


class TestWaiterDocstring(unittest.TestCase):
    def test_use_correct_docstring_writer(self):
        with mock.patch(
                'botocore.docs.docstring'
                '.document_wait_method') as mock_writer:
            docstring = WaiterDocstring()
            str(docstring)
            self.assertTrue(mock_writer.called)


class TestPaginatorDocstring(unittest.TestCase):
    def test_use_correct_docstring_writer(self):
        with mock.patch(
                'botocore.docs.docstring'
                '.document_paginate_method') as mock_writer:
            docstring = PaginatorDocstring()
            str(docstring)
            self.assertTrue(mock_writer.called)
