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
from botocore.compat import six
from botocore.docs.bcdoc.style import ReSTStyle
from botocore.docs.bcdoc.restdoc import ReSTDocument


class TestStyle(unittest.TestCase):

    def test_spaces(self):
        style = ReSTStyle(None, 4)
        self.assertEqual(style.spaces(), '')
        style.indent()
        self.assertEqual(style.spaces(), '    ')
        style.indent()
        self.assertEqual(style.spaces(), '        ')
        style.dedent()
        self.assertEqual(style.spaces(), '    ')
        style.dedent()
        self.assertEqual(style.spaces(), '')
        style.dedent()
        self.assertEqual(style.spaces(), '')

    def test_bold(self):
        style = ReSTStyle(ReSTDocument())
        style.bold('foobar')
        self.assertEqual(style.doc.getvalue(), six.b('**foobar** '))

    def test_empty_bold(self):
        style = ReSTStyle(ReSTDocument())
        style.start_b()
        style.end_b()
        self.assertEqual(style.doc.getvalue(), six.b(''))

    def test_italics(self):
        style = ReSTStyle(ReSTDocument())
        style.italics('foobar')
        self.assertEqual(style.doc.getvalue(), six.b('*foobar* '))

    def test_empty_italics(self):
        style = ReSTStyle(ReSTDocument())
        style.start_i()
        style.end_i()
        self.assertEqual(style.doc.getvalue(), six.b(''))

    def test_p(self):
        style = ReSTStyle(ReSTDocument())
        style.start_p()
        style.doc.write('foo')
        style.end_p()
        self.assertEqual(style.doc.getvalue(), six.b('\n\nfoo\n\n'))

    def test_code(self):
        style = ReSTStyle(ReSTDocument())
        style.code('foobar')
        self.assertEqual(style.doc.getvalue(), six.b('``foobar`` '))

    def test_empty_code(self):
        style = ReSTStyle(ReSTDocument())
        style.start_code()
        style.end_code()
        self.assertEqual(style.doc.getvalue(), six.b(''))

    def test_h1(self):
        style = ReSTStyle(ReSTDocument())
        style.h1('foobar fiebaz')
        self.assertEqual(
            style.doc.getvalue(),
            six.b('\n\n*************\nfoobar fiebaz\n*************\n\n'))

    def test_h2(self):
        style = ReSTStyle(ReSTDocument())
        style.h2('foobar fiebaz')
        self.assertEqual(
            style.doc.getvalue(),
            six.b('\n\n=============\nfoobar fiebaz\n=============\n\n'))

    def test_h3(self):
        style = ReSTStyle(ReSTDocument())
        style.h3('foobar fiebaz')
        self.assertEqual(
            style.doc.getvalue(),
            six.b('\n\n-------------\nfoobar fiebaz\n-------------\n\n'))

    def test_ref(self):
        style = ReSTStyle(ReSTDocument())
        style.ref('foobar', 'http://foo.bar.com')
        self.assertEqual(style.doc.getvalue(),
                         six.b(':doc:`foobar <http://foo.bar.com>`'))

    def test_examples(self):
        style = ReSTStyle(ReSTDocument())
        self.assertTrue(style.doc.keep_data)
        style.start_examples()
        self.assertFalse(style.doc.keep_data)
        style.end_examples()
        self.assertTrue(style.doc.keep_data)

    def test_codeblock(self):
        style = ReSTStyle(ReSTDocument())
        style.codeblock('foobar')
        self.assertEqual(style.doc.getvalue(),
                         six.b('::\n\n  foobar\n\n\n'))

    def test_important(self):
        style = ReSTStyle(ReSTDocument())
        style.start_important()
        style.end_important()
        self.assertEqual(style.doc.getvalue(),
                         six.b('\n\n.. warning::\n\n  \n\n'))

    def test_note(self):
        style = ReSTStyle(ReSTDocument())
        style.start_note()
        style.end_note()
        self.assertEqual(style.doc.getvalue(),
                         six.b('\n\n.. note::\n\n  \n\n'))

    def test_danger(self):
        style = ReSTStyle(ReSTDocument())
        style.start_danger()
        style.end_danger()
        self.assertEqual(style.doc.getvalue(),
                         six.b('\n\n.. danger::\n\n  \n\n'))

    def test_toctree_html(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'html'
        style.toctree()
        style.tocitem('foo')
        style.tocitem('bar')
        self.assertEqual(
            style.doc.getvalue(),
            six.b('\n.. toctree::\n  :maxdepth: 1'
                  '\n  :titlesonly:\n\n  foo\n  bar\n'))

    def test_toctree_man(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'man'
        style.toctree()
        style.tocitem('foo')
        style.tocitem('bar')
        self.assertEqual(style.doc.getvalue(),
                         six.b('\n\n\n* foo\n\n\n* bar\n\n'))

    def test_hidden_toctree_html(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'html'
        style.hidden_toctree()
        style.hidden_tocitem('foo')
        style.hidden_tocitem('bar')
        self.assertEqual(
            style.doc.getvalue(),
            six.b('\n.. toctree::\n  :maxdepth: 1'
                  '\n  :hidden:\n\n  foo\n  bar\n'))

    def test_hidden_toctree_non_html(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'man'
        style.hidden_toctree()
        style.hidden_tocitem('foo')
        style.hidden_tocitem('bar')
        self.assertEqual(
            style.doc.getvalue(),
            six.b(''))

    def test_href_link(self):
        style = ReSTStyle(ReSTDocument())
        style.start_a(attrs=[('href', 'http://example.org')])
        style.doc.write('example')
        style.end_a()
        self.assertEqual(
            style.doc.getvalue(),
            six.b('`example <http://example.org>`__ ')
        )

    def test_escape_href_link(self):
        style = ReSTStyle(ReSTDocument())
        style.start_a(attrs=[('href', 'http://example.org')])
        style.doc.write('foo: the next bar')
        style.end_a()
        self.assertEqual(
            style.doc.getvalue(),
            six.b('`foo\\: the next bar <http://example.org>`__ '))

    def test_handle_no_text_hrefs(self):
        style = ReSTStyle(ReSTDocument())
        style.start_a(attrs=[('href', 'http://example.org')])
        style.end_a()
        self.assertEqual(style.doc.getvalue(),
                         six.b('`<http://example.org>`__ '))

    def test_sphinx_reference_label_html(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'html'
        style.sphinx_reference_label('foo', 'bar')
        self.assertEqual(style.doc.getvalue(), six.b(':ref:`bar <foo>`'))

    def test_sphinx_reference_label_html_no_text(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'html'
        style.sphinx_reference_label('foo')
        self.assertEqual(style.doc.getvalue(), six.b(':ref:`foo <foo>`'))

    def test_sphinx_reference_label_non_html(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'man'
        style.sphinx_reference_label('foo', 'bar')
        self.assertEqual(style.doc.getvalue(), six.b('bar'))

    def test_sphinx_reference_label_non_html_no_text(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'man'
        style.sphinx_reference_label('foo')
        self.assertEqual(style.doc.getvalue(), six.b('foo'))

    def test_table_of_contents(self):
        style = ReSTStyle(ReSTDocument())
        style.table_of_contents()
        self.assertEqual(style.doc.getvalue(), six.b('.. contents:: '))

    def test_table_of_contents_with_title(self):
        style = ReSTStyle(ReSTDocument())
        style.table_of_contents(title='Foo')
        self.assertEqual(style.doc.getvalue(), six.b('.. contents:: Foo\n'))

    def test_table_of_contents_with_title_and_depth(self):
        style = ReSTStyle(ReSTDocument())
        style.table_of_contents(title='Foo', depth=2)
        self.assertEqual(style.doc.getvalue(),
                         six.b('.. contents:: Foo\n   :depth: 2\n'))

    def test_sphinx_py_class(self):
        style = ReSTStyle(ReSTDocument())
        style.start_sphinx_py_class('FooClass')
        style.end_sphinx_py_class()
        self.assertEqual(style.doc.getvalue(),
                         six.b('\n\n.. py:class:: FooClass\n\n  \n\n'))

    def test_sphinx_py_method(self):
        style = ReSTStyle(ReSTDocument())
        style.start_sphinx_py_method('method')
        style.end_sphinx_py_method()
        self.assertEqual(style.doc.getvalue(),
                         six.b('\n\n.. py:method:: method\n\n  \n\n'))

    def test_sphinx_py_method_with_params(self):
        style = ReSTStyle(ReSTDocument())
        style.start_sphinx_py_method('method', 'foo=None')
        style.end_sphinx_py_method()
        self.assertEqual(
            style.doc.getvalue(),
            six.b('\n\n.. py:method:: method(foo=None)\n\n  \n\n'))

    def test_sphinx_py_attr(self):
        style = ReSTStyle(ReSTDocument())
        style.start_sphinx_py_attr('Foo')
        style.end_sphinx_py_attr()
        self.assertEqual(style.doc.getvalue(),
                         six.b('\n\n.. py:attribute:: Foo\n\n  \n\n'))

    def test_write_py_doc_string(self):
        style = ReSTStyle(ReSTDocument())
        docstring = (
            'This describes a function\n'
            ':param foo: Describes foo\n'
            'returns: None'
        )
        style.write_py_doc_string(docstring)
        self.assertEqual(style.doc.getvalue(), six.b(docstring + '\n'))

    def test_new_line(self):
        style = ReSTStyle(ReSTDocument())
        style.new_line()
        self.assertEqual(style.doc.getvalue(), six.b('\n'))

        style.do_p = False
        style.new_line()
        self.assertEqual(style.doc.getvalue(), six.b('\n\n'))

    def test_list(self):
        style = ReSTStyle(ReSTDocument())
        style.li('foo')
        self.assertEqual(style.doc.getvalue(), six.b('\n* foo\n\n'))

    def test_non_top_level_lists_are_indented(self):
        style = ReSTStyle(ReSTDocument())

        # Start the top level list
        style.start_ul()

        # Write one list element
        style.start_li()
        style.doc.handle_data('foo')
        style.end_li()

        self.assertEqual(style.doc.getvalue(), six.b("\n\n\n* foo\n"))

        # Start the nested list
        style.start_ul()

        # Write an element to the nested list
        style.start_li()
        style.doc.handle_data('bar')
        style.end_li()

        self.assertEqual(style.doc.getvalue(),
                         six.b("\n\n\n* foo\n\n\n  \n  * bar\n  "))

    def test_external_link(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'html'
        style.external_link('MyLink', 'http://example.com/foo')
        self.assertEqual(style.doc.getvalue(),
                         six.b('`MyLink <http://example.com/foo>`_'))

    def test_external_link_in_man_page(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'man'
        style.external_link('MyLink', 'http://example.com/foo')
        self.assertEqual(style.doc.getvalue(), six.b('MyLink'))

    def test_internal_link(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'html'
        style.internal_link('MyLink', '/index')
        self.assertEqual(
            style.doc.getvalue(),
            six.b(':doc:`MyLink </index>`')
        )

    def test_internal_link_in_man_page(self):
        style = ReSTStyle(ReSTDocument())
        style.doc.target = 'man'
        style.internal_link('MyLink', '/index')
        self.assertEqual(style.doc.getvalue(), six.b('MyLink'))
