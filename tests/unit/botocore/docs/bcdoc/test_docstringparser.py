# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock
from tests import unittest

import botocore.docs.bcdoc.docstringparser as parser
from botocore.docs.bcdoc.restdoc import ReSTDocument


class TestDocStringParser(unittest.TestCase):
    def parse(self, html):
        docstring_parser = parser.DocStringParser(ReSTDocument())
        docstring_parser.feed(html)
        docstring_parser.close()
        return docstring_parser.doc.getvalue()

    def assert_contains_exact_lines_in_order(self, actual, expected):
        # Get each line and filter out empty lines
        contents = actual.split(b'\n')
        contents = [line for line in contents if line and not line.isspace()]

        for line in expected:
            self.assertIn(line, contents)
            beginning = contents.index(line)
            contents = contents[beginning:]

    def test_nested_lists(self):
        html = "<ul><li>Wello</li><ul><li>Horld</li></ul></ul>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(result, [
            b'* Wello',
            b'  * Horld'
        ])

    def test_nested_lists_with_extra_white_space(self):
        html = "<ul> <li> Wello</li><ul> <li> Horld</li></ul></ul>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(result, [
            b'* Wello',
            b'  * Horld'
        ])


class TestHTMLTree(unittest.TestCase):
    def setUp(self):
        self.style = mock.Mock()
        self.doc = mock.Mock()
        self.doc.style = self.style
        self.tree = parser.HTMLTree(self.doc)

    def test_add_tag(self):
        self.tree.add_tag('foo')
        self.assertIsInstance(self.tree.current_node, parser.TagNode)
        self.assertEqual(self.tree.current_node.tag, 'foo')

    def test_add_unsupported_tag(self):
        del self.style.start_foo
        del self.style.end_foo
        self.tree.add_tag('foo')
        self.assertIn('foo', self.tree.unhandled_tags)

    def test_add_data(self):
        self.tree.add_data('foo')
        self.assertNotIsInstance(self.tree.current_node, parser.DataNode)
        node = self.tree.head.children[0]
        self.assertIsInstance(node, parser.DataNode)
        self.assertEqual(node.data, 'foo')


class TestStemNode(unittest.TestCase):
    def setUp(self):
        self.style = mock.Mock()
        self.doc = mock.Mock()
        self.doc.style = self.style
        self.node = parser.StemNode()

    def test_add_child(self):
        child = parser.StemNode()
        self.node.add_child(child)
        self.assertIn(child, self.node.children)
        self.assertEqual(child.parent, self.node)

    def test_write(self):
        self.node.add_child(mock.Mock())
        self.node.add_child(mock.Mock())

        self.node.write(mock.Mock())
        for child in self.node.children:
            self.assertTrue(child.write.called)


class TestTagNode(unittest.TestCase):
    def setUp(self):
        self.style = mock.Mock()
        self.doc = mock.Mock()
        self.doc.style = self.style
        self.tag = 'foo'
        self.node = parser.TagNode(self.tag)

    def test_write_calls_style(self):
        self.node.write(self.doc)
        self.assertTrue(self.style.start_foo.called)
        self.assertTrue(self.style.end_foo.called)

    def test_write_unsupported_tag(self):
        del self.style.start_foo
        del self.style.end_foo

        try:
            self.node.write(self.doc)
        except AttributeError as e:
            self.fail(str(e))


class TestDataNode(unittest.TestCase):
    def setUp(self):
        self.style = mock.Mock()
        self.doc = mock.Mock()
        self.doc.style = self.style

    def test_string_data(self):
        node = parser.DataNode('foo')
        self.assertEqual(node.data, 'foo')

    def test_non_string_data_raises_error(self):
        with self.assertRaises(ValueError):
            parser.DataNode(5)

    def test_lstrip(self):
        node = parser.DataNode(' foo')
        node.lstrip()
        self.assertEqual(node.data, 'foo')

    def test_write(self):
        node = parser.DataNode('foo   bar baz')
        self.doc.translate_words.return_value = ['foo', 'bar', 'baz']
        node.write(self.doc)
        self.doc.handle_data.assert_called_once_with('foo bar baz')

    def test_write_space(self):
        node = parser.DataNode(' ')
        node.write(self.doc)
        self.doc.handle_data.assert_called_once_with(' ')
        self.doc.handle_data.reset_mock()

        node = parser.DataNode('              ')
        node.write(self.doc)
        self.doc.handle_data.assert_called_once_with(' ')

    def test_write_empty_string(self):
        node = parser.DataNode('')
        node.write(self.doc)
        self.assertFalse(self.doc.handle_data.called)


class TestLineItemNode(unittest.TestCase):
    def setUp(self):
        self.style = mock.Mock()
        self.doc = mock.Mock()
        self.doc.style = self.style
        self.doc.translate_words.return_value = ['foo']
        self.node = parser.LineItemNode()

    def test_write_strips_white_space(self):
        self.node.add_child(parser.DataNode('  foo'))
        self.node.write(self.doc)
        self.doc.handle_data.assert_called_once_with('foo')

    def test_write_strips_nested_white_space(self):
        self.node.add_child(parser.DataNode('  '))
        tag_child = parser.TagNode('foo')
        tag_child.add_child(parser.DataNode('  '))
        tag_child_2 = parser.TagNode('foo')
        tag_child_2.add_child(parser.DataNode(' foo'))
        tag_child.add_child(tag_child_2)
        self.node.add_child(tag_child)

        self.node.write(self.doc)
        self.doc.handle_data.assert_called_once_with('foo')

    def test_write_only_strips_until_text_is_found(self):
        self.node.add_child(parser.DataNode('  '))
        tag_child = parser.TagNode('foo')
        tag_child.add_child(parser.DataNode('  '))
        tag_child_2 = parser.TagNode('foo')
        tag_child_2.add_child(parser.DataNode(' foo'))
        tag_child_2.add_child(parser.DataNode(' '))
        tag_child.add_child(tag_child_2)
        self.node.add_child(tag_child)

        self.node.write(self.doc)

        calls = [mock.call('foo'), mock.call(' ')]
        self.doc.handle_data.assert_has_calls(calls)
