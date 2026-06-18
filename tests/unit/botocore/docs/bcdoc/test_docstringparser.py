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
import pytest

import botocore.docs.bcdoc.docstringparser as parser
from botocore.docs.bcdoc.restdoc import ReSTDocument
from tests import mock, unittest


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

    def test_tag_with_collapsible_spaces(self):
        html = "<p>  a       bcd efg </p>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(result, [b'a bcd efg'])

    def test_nested_lists(self):
        html = "<ul><li>Wello</li><ul><li>Horld</li></ul></ul>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(
            result, [b'* Wello', b'  * Horld']
        )

    def test_nested_lists_with_extra_white_space(self):
        html = "<ul> <li> Wello</li><ul> <li> Horld</li></ul></ul>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(
            result, [b'* Wello', b'  * Horld']
        )

    def test_link_with_no_period(self):
        html = "<p>This is a test <a href='https://testing.com'>Link</a></p>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(
            result, [b'This is a test `Link <https://testing.com>`__']
        )

    def test_link_with_period(self):
        html = "<p>This is a test <a href='https://testing.com'>Link</a>.</p>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(
            result, [b'This is a test `Link <https://testing.com>`__.']
        )

    def test_code_with_empty_link(self):
        html = "<p>Foo <code> <a>Link</a> </code></p>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(result, [b'Foo ``Link``'])

    def test_code_with_link_spaces(self):
        html = "<p>Foo <code> <a href=\"https://aws.dev\">Link</a> </code></p>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(result, [b'Foo ``Link``'])

    def test_code_with_link_no_spaces(self):
        html = "<p>Foo <code><a href=\"https://aws.dev\">Link</a></code></p>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(result, [b'Foo ``Link``'])

    def test_href_with_spaces(self):
        html = "<p><a href=\" https://testing.com\">Link</a></p>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(
            result, [b' `Link <https://testing.com>`__']
        )

    def test_bold_with_nested_formatting(self):
        html = "<b><code>Test</code>test<a href=\" https://testing.com\">Link</a></b>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(
            result, [b'``Test``test `Link <https://testing.com>`__']
        )

    def test_link_with_nested_formatting(self):
        html = "<a href=\"https://testing.com\"><code>Test</code></a>"
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(
            result, [b'`Test <https://testing.com>`__']
        )

    def test_indentation_with_spaces_between_tags(self):
        # Leading spaces inserted as padding between HTML tags can lead to
        # unexpected indentation in RST. For example, consider the space between
        # ``<p>`` and ``<b>`` in the third line of this example:
        html = (
            "<p>First paragraph </p> "
            "<note> <p> Second paragraph in note </p> </note> "
            "<p> <b>Bold statement:</b> Third paragraph</p>"
            "<p>Last paragraph</p> "
        )
        # If kept, it will appear as indentation in RST and have the effect of
        # pulling the third paragraph into the note:
        #
        # ```
        # First paragraph
        #
        # ..note::
        #   Second paragraph in note <-- intentionally indented
        #
        #  **Bold statement:** Third paragraph <-- unintentionally indented
        #
        # Last paragraph <-- first non-indented paragraph after note
        # ```
        result = self.parse(html)
        self.assert_contains_exact_lines_in_order(
            result,
            #  ↓ no whitespace here
            [b'**Bold statement:** Third paragraph'],
        )


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
        self.doc.translate_words.return_value = []

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

    def test_write_empty_string(self):
        node = parser.DataNode('')
        node.write(self.doc)
        self.assertFalse(self.doc.handle_data.called)


@pytest.mark.parametrize(
    'data, lstrip, rstrip, both',
    [
        ('foo', 'foo', 'foo', 'foo'),
        (' foo', 'foo', ' foo', 'foo'),
        ('   foo', 'foo', '   foo', 'foo'),
        ('\tfoo', 'foo', '\tfoo', 'foo'),
        ('\t \t foo', 'foo', '\t \t foo', 'foo'),
        ('foo ', 'foo ', 'foo', 'foo'),
        ('foo  ', 'foo  ', 'foo', 'foo'),
        ('foo\t\t', 'foo\t\t', 'foo', 'foo'),
    ],
)
def test_datanode_stripping(data, lstrip, rstrip, both):
    doc = mock.Mock()
    doc.style = mock.Mock()
    doc.translate_words.side_effect = lambda words: words

    node = parser.DataNode(data)
    node.lstrip()
    node.write(doc)
    doc.handle_data.assert_called_once_with(lstrip)
    doc.handle_data.reset_mock()

    node = parser.DataNode(data)
    node.rstrip()
    node.write(doc)
    doc.handle_data.assert_called_once_with(rstrip)
    doc.handle_data.reset_mock()

    node = parser.DataNode(data)
    node.lstrip()
    node.rstrip()
    node.write(doc)
    doc.handle_data.assert_called_once_with(both)


@pytest.mark.parametrize(
    'data',
    [
        (' '),
        ('  '),
        ('\t'),
        ('\t \t '),
    ],
)
def test_datanode_stripping_empty_string(data):
    doc = mock.Mock()
    doc.style = mock.Mock()
    doc.translate_words.side_effect = lambda words: words
    node = parser.DataNode(data)
    node.lstrip()
    node.write(doc)
    doc.handle_data.assert_not_called()


@pytest.mark.parametrize(
    'html, expected_lines',
    [
        ('<p>  foo</p>', [b'foo']),
        ('<p>\tfoo</p>', [b'foo']),
        ('<p>  <span>  </span> <span> <span> foo</span></span></p>', [b'foo']),
        ('<p>foo  </p>', [b'foo']),
        ('<p>foo\t</p>', [b'foo']),
        ('<p>  foo  </p>', [b'foo']),
        ('<p>  <span>foo</span>  </p>', [b'foo']),
        ('<p>  <span>foo  </span>  </p>', [b'foo']),
        ('<p>  <span>  foo</span>  </p>', [b'foo']),
        ('<p>  <span>  foo  </span>  </p>', [b'foo']),
        # various nested markup examples
        ('<i>italic</i>', [b'*italic*']),
        ('<p><i>italic</i></p>', [b'*italic*']),
        ('<p><i>italic</i> </p>', [b'*italic*']),
        ('<p><i>italic </i></p>', [b'*italic*']),
        ('<p>foo <i> italic </i> bar</p>', [b'foo *italic* bar']),
        ('<p>  <span> foo <i> bar</i> </span>  </p>', [b'foo *bar*']),
        ('<p>  <span> foo<i> bar</i> </span>  </p>', [b'foo* bar*']),
        ('<p>  <span> foo <i>bar</i> </span>  </p>', [b'foo *bar*']),
        # links
        ('<a href="url">foo</a> <i>bar</i>', [b'`foo <url>`__ *bar*']),
        # ReST does not support link text starting with whitespace
        ('<p>abc<a href="url"> foo</a></p>', [b'abc `foo <url>`__']),
        ('<p>abc<a href="url"> foo </a> bar</p>', [b'abc `foo <url>`__ bar']),
        # code-in-a removed and whitespace removed
        ('<a href="url"> <code>foo</code> </a> bar', [b'`foo <url>`__ bar']),
        # list items
        ('<li>  foo</li>', [b'* foo']),
        ('<li>  <foo>  </foo><foo> foo</foo></li>', [b'* foo']),
        ('<li>  <foo> foo</foo><foo>  </foo></li>', [b'* foo']),
        ('<li><foo>  </foo><foo> foo</foo> <foo>bar</li>', [b'* foo bar']),
        ('<li><foo>  </foo><foo> foo</foo> <foo> bar</li>', [b'* foo bar']),
        ('<li><foo>  </foo><foo> foo</foo><foo> bar</li>', [b'* foo bar']),
        # multiple block tags in sequence are each left and right stripped
        ('<p>  foo</p><p>  bar\t</p>', [b'foo', b'bar']),
        ('<p>  foo</p><li>  bar  </li>', [b'foo', b'* bar']),
        # nested block tags also work
        (
            '<p> <p> foo </p> <p> <span> bar </span> </p> </p>',
            [b'foo', b'bar'],
        ),
    ],
)
def test_whitespace_collapsing(html, expected_lines):
    docstring_parser = parser.DocStringParser(ReSTDocument())
    docstring_parser.feed(html)
    docstring_parser.close()
    actual = docstring_parser.doc.getvalue()

    # Get each line and filter out empty lines
    contents = actual.split(b'\n')
    contents = [line for line in contents if line and not line.isspace()]
    for line in expected_lines:
        assert line in contents
        beginning = contents.index(line)
        contents = contents[beginning:]
