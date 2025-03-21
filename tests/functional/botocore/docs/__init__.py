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
from botocore.docs.service import ServiceDocumenter
from botocore.session import get_session

from tests import unittest


class BaseDocsFunctionalTest(unittest.TestCase):
    def setUp(self):
        self._session = get_session()

    def assert_contains_line(self, line, contents):
        contents = contents.decode('utf-8')
        self.assertIn(line, contents)

    def assert_contains_lines_in_order(self, lines, contents):
        contents = contents.decode('utf-8')
        for line in lines:
            self.assertIn(line, contents)
            beginning = contents.find(line)
            contents = contents[(beginning + len(line)) :]

    def assert_not_contains_line(self, line, contents):
        contents = contents.decode('utf-8')
        self.assertNotIn(line, contents)

    def assert_not_contains_lines(self, lines, contents):
        contents = contents.decode('utf-8')
        for line in lines:
            self.assertNotIn(line, contents)

    def get_title_section_for(self, service_name):
        contents = (
            ServiceDocumenter(service_name, self._session)
            .document_service()
            .decode('utf-8')
        )
        start_of_table_of_contents = 'Table of Contents'
        start_index = contents.find(start_of_table_of_contents)
        contents = contents[:start_index]
        contents = contents.encode('utf-8')
        return contents

    def get_method_document_block(self, operation_name, contents):
        contents = contents.decode('utf-8')
        start_method_document = '  .. py:method:: %s(' % operation_name
        start_index = contents.find(start_method_document)
        self.assertNotEqual(start_index, -1, 'Method is not found in contents')
        contents = contents[start_index:]
        end_index = contents.find(
            '  .. py:method::', len(start_method_document)
        )
        contents = contents[:end_index]
        return contents.encode('utf-8')

    def get_parameter_document_block(self, param_name, contents):
        contents = contents.decode('utf-8')
        start_param_document = '    :type %s:' % param_name
        start_index = contents.find(start_param_document)
        self.assertNotEqual(start_index, -1, 'Param is not found in contents')
        contents = contents[start_index:]
        end_index = contents.find('    :type', len(start_param_document))
        contents = contents[:end_index]
        return contents.encode('utf-8')

    def get_parameter_documentation_from_service(
        self, service_name, method_name, param_name
    ):
        contents = ServiceDocumenter(
            service_name, self._session
        ).document_service()
        method_contents = self.get_method_document_block(method_name, contents)
        return self.get_parameter_document_block(param_name, method_contents)

    def get_docstring_for_method(self, service_name, method_name):
        contents = ServiceDocumenter(
            service_name, self._session
        ).document_service()
        method_contents = self.get_method_document_block(method_name, contents)
        return method_contents

    def assert_is_documented_as_autopopulated_param(
        self, service_name, method_name, param_name, doc_string=None
    ):
        contents = ServiceDocumenter(
            service_name, self._session
        ).document_service()
        method_contents = self.get_method_document_block(method_name, contents)

        # Ensure it is not in the example.
        self.assert_not_contains_line(
            '%s=\'string\'' % param_name, method_contents
        )

        # Ensure it is in the params.
        param_contents = self.get_parameter_document_block(
            param_name, method_contents
        )

        # Ensure it is not labeled as required.
        self.assert_not_contains_line('REQUIRED', param_contents)

        # Ensure the note about autopopulation was added.
        if doc_string is None:
            doc_string = 'Please note that this parameter is automatically'
        self.assert_contains_line(doc_string, param_contents)
