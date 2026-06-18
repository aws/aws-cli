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
from botocore.docs.bcdoc.restdoc import DocumentStructure, ReSTDocument
from tests import unittest


class TestReSTDocument(unittest.TestCase):
    def test_write(self):
        doc = ReSTDocument()
        doc.write('foo')
        self.assertEqual(doc.getvalue(), b'foo')

    def test_writeln(self):
        doc = ReSTDocument()
        doc.writeln('foo')
        self.assertEqual(doc.getvalue(), b'foo\n')

    def test_include_doc_string(self):
        doc = ReSTDocument()
        doc.include_doc_string('<p>this is a <code>test</code></p>')
        self.assertEqual(doc.getvalue(), b'\n\nthis is a ``test``\n\n')

    def test_remove_doc_string(self):
        doc = ReSTDocument()
        doc.writeln('foo')
        doc.include_doc_string('<p>this is a <code>test</code></p>')
        doc.remove_last_doc_string()
        self.assertEqual(doc.getvalue(), b'foo\n')

    def test_add_links(self):
        doc = ReSTDocument()
        doc.hrefs['foo'] = 'https://example.com/'
        self.assertEqual(
            doc.getvalue(), b'\n\n.. _foo: https://example.com/\n'
        )


class TestDocumentStructure(unittest.TestCase):
    def setUp(self):
        self.name = 'mydoc'
        self.doc_structure = DocumentStructure(self.name)

    def test_name(self):
        self.assertEqual(self.doc_structure.name, self.name)

    def test_path(self):
        self.assertEqual(self.doc_structure.path, [self.name])
        self.doc_structure.path = ['foo']
        self.assertEqual(self.doc_structure.path, ['foo'])

    def test_add_new_section(self):
        section = self.doc_structure.add_new_section('mysection')

        # Ensure the name of the section is correct
        self.assertEqual(section.name, 'mysection')

        # Ensure we can get the section.
        self.assertEqual(self.doc_structure.get_section('mysection'), section)

        # Ensure the path is correct
        self.assertEqual(section.path, ['mydoc', 'mysection'])

        # Ensure some of the necessary attributes are passed to the
        # the section.
        self.assertEqual(
            section.style.indentation, self.doc_structure.style.indentation
        )
        self.assertEqual(
            section.translation_map, self.doc_structure.translation_map
        )
        self.assertEqual(section.hrefs, self.doc_structure.hrefs)

    def test_delete_section(self):
        section = self.doc_structure.add_new_section('mysection')
        self.assertEqual(self.doc_structure.get_section('mysection'), section)
        self.doc_structure.delete_section('mysection')
        with self.assertRaises(KeyError):
            section.get_section('mysection')

    def test_create_sections_at_instantiation(self):
        sections = ['intro', 'middle', 'end']
        self.doc_structure = DocumentStructure(
            self.name, section_names=sections
        )
        # Ensure the sections are attached to the new document structure.
        for section_name in sections:
            section = self.doc_structure.get_section(section_name)
            self.assertEqual(section.name, section_name)

    def test_flush_structure(self):
        section = self.doc_structure.add_new_section('mysection')
        subsection = section.add_new_section('mysubsection')
        self.doc_structure.writeln('1')
        section.writeln('2')
        subsection.writeln('3')
        second_section = self.doc_structure.add_new_section('mysection2')
        second_section.writeln('4')
        contents = self.doc_structure.flush_structure()

        # Ensure the contents were flushed out correctly
        self.assertEqual(contents, b'1\n2\n3\n4\n')

    def test_flush_structure_hrefs(self):
        section = self.doc_structure.add_new_section('mysection')
        section.writeln('section contents')
        self.doc_structure.hrefs['foo'] = 'www.foo.com'
        section.hrefs['bar'] = 'www.bar.com'
        contents = self.doc_structure.flush_structure()
        self.assertIn(b'.. _foo: www.foo.com', contents)
        self.assertIn(b'.. _bar: www.bar.com', contents)

    def test_available_sections(self):
        self.doc_structure.add_new_section('mysection')
        self.doc_structure.add_new_section('mysection2')
        self.assertEqual(
            self.doc_structure.available_sections, ['mysection', 'mysection2']
        )

    def test_context(self):
        context = {'Foo': 'Bar'}
        section = self.doc_structure.add_new_section(
            'mysection', context=context
        )
        self.assertEqual(section.context, context)

        # Make sure if context is not specified it is empty.
        section = self.doc_structure.add_new_section('mysection2')
        self.assertEqual(section.context, {})

    def test_remove_all_sections(self):
        self.doc_structure.add_new_section('mysection2')
        self.doc_structure.remove_all_sections()
        self.assertEqual(self.doc_structure.available_sections, [])

    def test_clear_text(self):
        self.doc_structure.write('Foo')
        self.doc_structure.clear_text()
        self.assertEqual(self.doc_structure.flush_structure(), b'')
