# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import mock
import textwrap

from awscli.clidriver import create_clidriver
from awscli.autoprompt.doc import DocsGetter
from awscli.testutils import unittest


class TestDocsGetter(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.help_command = self.driver.create_help_command()
        self.help_command.doc = mock.Mock()
        self.help_command.doc.getvalue = mock.Mock()
        self.base_docs_getter = DocsGetter(self.driver)

    def test_get_doc_content(self):
        self.help_command.doc.getvalue.return_value = b'Dummy content.'
        content = self.base_docs_getter.get_doc_content(self.help_command)
        self.assertEqual(content, 'Dummy content.\n')

    def test_get_rst_doc_in_txt(self):
        content = textwrap.dedent("""\
            MySection
            =========

            This is some text.
            Here's a list:

            * foo
            * bar

            Literal text: ``--foo-bar``
        """)
        expected_response = textwrap.dedent("""\

            MYSECTION

            This is some text. Here's a list:

            * foo

            * bar

            Literal text: --foo-bar
        """)
        self.help_command.doc.getvalue.return_value = content.encode('utf-8')
        response = self.base_docs_getter.get_doc_content(self.help_command)
        self.assertEqual(response, expected_response)

    def test_get_doc_content_strips_carriage_returns(self):
        content = textwrap.dedent("""\
            MySection\r
            =========\r
        """)
        expected_response = textwrap.dedent("""\

            MYSECTION
        """)
        self.help_command.doc.getvalue.return_value = content.encode('utf-8')
        response = self.base_docs_getter.get_doc_content(self.help_command)
        self.assertEqual(response, expected_response)

    def test_get_empty_doc_content(self):
        self.help_command.doc.getvalue.return_value = b''
        content = self.base_docs_getter.get_doc_content(self.help_command)
        self.assertEqual(content, '')
