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
from botocore.docs.utils import (
    AppendParamDocumentation,
    AutoPopulatedParam,
    HideParamFromOperations,
    escape_controls,
    get_official_service_name,
    py_default,
    py_type_name,
)
from tests import unittest
from tests.unit.docs import BaseDocsTest


class TestPythonTypeName(unittest.TestCase):
    def test_structure(self):
        self.assertEqual('dict', py_type_name('structure'))

    def test_list(self):
        self.assertEqual('list', py_type_name('list'))

    def test_map(self):
        self.assertEqual('dict', py_type_name('map'))

    def test_string(self):
        self.assertEqual('string', py_type_name('string'))

    def test_character(self):
        self.assertEqual('string', py_type_name('character'))

    def test_blob(self):
        self.assertEqual('bytes', py_type_name('blob'))

    def test_timestamp(self):
        self.assertEqual('datetime', py_type_name('timestamp'))

    def test_integer(self):
        self.assertEqual('integer', py_type_name('integer'))

    def test_long(self):
        self.assertEqual('integer', py_type_name('long'))

    def test_float(self):
        self.assertEqual('float', py_type_name('float'))

    def test_double(self):
        self.assertEqual('float', py_type_name('double'))


class TestPythonDefault(unittest.TestCase):
    def test_structure(self):
        self.assertEqual('{...}', py_default('structure'))

    def test_list(self):
        self.assertEqual('[...]', py_default('list'))

    def test_map(self):
        self.assertEqual('{...}', py_default('map'))

    def test_string(self):
        self.assertEqual('\'string\'', py_default('string'))

    def test_blob(self):
        self.assertEqual('b\'bytes\'', py_default('blob'))

    def test_timestamp(self):
        self.assertEqual('datetime(2015, 1, 1)', py_default('timestamp'))

    def test_integer(self):
        self.assertEqual('123', py_default('integer'))

    def test_long(self):
        self.assertEqual('123', py_default('long'))

    def test_double(self):
        self.assertEqual('123.0', py_default('double'))


class TestGetOfficialServiceName(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.service_model.metadata = {'serviceFullName': 'Official Name'}

    def test_no_short_name(self):
        self.assertEqual(
            'Official Name', get_official_service_name(self.service_model)
        )

    def test_aws_short_name(self):
        self.service_model.metadata['serviceAbbreviation'] = 'AWS Foo'
        self.assertEqual(
            'Official Name (Foo)',
            get_official_service_name(self.service_model),
        )

    def test_amazon_short_name(self):
        self.service_model.metadata['serviceAbbreviation'] = 'Amazon Foo'
        self.assertEqual(
            'Official Name (Foo)',
            get_official_service_name(self.service_model),
        )

    def test_short_name_in_official_name(self):
        self.service_model.metadata['serviceFullName'] = 'The Foo Service'
        self.service_model.metadata['serviceAbbreviation'] = 'Amazon Foo'
        self.assertEqual(
            'The Foo Service', get_official_service_name(self.service_model)
        )


class TestAutopopulatedParam(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.name = 'MyMember'
        self.param = AutoPopulatedParam(self.name)

    def test_request_param_not_required(self):
        section = self.doc_structure.add_new_section(self.name)
        section.add_new_section('param-documentation')
        self.param.document_auto_populated_param(
            'docs.request-params', self.doc_structure
        )
        self.assert_contains_line('this parameter is automatically populated')

    def test_request_param_required(self):
        section = self.doc_structure.add_new_section(self.name)
        is_required_section = section.add_new_section('is-required')
        section.add_new_section('param-documentation')
        is_required_section.write('**[REQUIRED]**')
        self.param.document_auto_populated_param(
            'docs.request-params', self.doc_structure
        )
        self.assert_not_contains_line('**[REQUIRED]**')
        self.assert_contains_line('this parameter is automatically populated')

    def test_non_default_param_description(self):
        description = 'This is a custom description'
        self.param = AutoPopulatedParam(self.name, description)
        section = self.doc_structure.add_new_section(self.name)
        section.add_new_section('param-documentation')
        self.param.document_auto_populated_param(
            'docs.request-params', self.doc_structure
        )
        self.assert_contains_line(description)

    def test_request_example(self):
        top_section = self.doc_structure.add_new_section('structure-value')
        section = top_section.add_new_section(self.name)
        example = 'MyMember: \'string\''
        section.write(example)
        self.assert_contains_line(example)
        self.param.document_auto_populated_param(
            'docs.request-example', self.doc_structure
        )
        self.assert_not_contains_line(example)

    def test_param_not_in_section_request_param(self):
        self.doc_structure.add_new_section('Foo')
        self.param.document_auto_populated_param(
            'docs.request-params', self.doc_structure
        )
        self.assertEqual(
            '', self.doc_structure.flush_structure().decode('utf-8')
        )

    def test_param_not_in_section_request_example(self):
        top_section = self.doc_structure.add_new_section('structure-value')
        section = top_section.add_new_section('Foo')
        example = 'Foo: \'string\''
        section.write(example)
        self.assert_contains_line(example)
        self.param.document_auto_populated_param(
            'docs.request-example', self.doc_structure
        )
        self.assert_contains_line(example)


class TestHideParamFromOperations(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.name = 'MyMember'
        self.param = HideParamFromOperations(
            's3', self.name, ['SampleOperation']
        )

    def test_hides_params_from_doc_string(self):
        section = self.doc_structure.add_new_section(self.name)
        param_signature = f':param {self.name}: '
        section.write(param_signature)
        self.assert_contains_line(param_signature)
        self.param.hide_param(
            'docs.request-params.s3.SampleOperation.complete-section',
            self.doc_structure,
        )
        self.assert_not_contains_line(param_signature)

    def test_hides_param_from_example(self):
        structure = self.doc_structure.add_new_section('structure-value')
        section = structure.add_new_section(self.name)
        example = f'{self.name}: \'string\''
        section.write(example)
        self.assert_contains_line(example)
        self.param.hide_param(
            'docs.request-example.s3.SampleOperation.complete-section',
            self.doc_structure,
        )
        self.assert_not_contains_line(example)


class TestAppendParamDocumentation(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.name = 'MyMember'
        self.param = AppendParamDocumentation(self.name, 'hello!')

    def test_appends_documentation(self):
        section = self.doc_structure.add_new_section(self.name)
        param_section = section.add_new_section('param-documentation')
        param_section.writeln('foo')
        self.param.append_documentation(
            'docs.request-params', self.doc_structure
        )
        self.assert_contains_line('foo\n')
        self.assert_contains_line('hello!')


class TestEscapeControls(unittest.TestCase):
    def test_escapes_controls(self):
        escaped = escape_controls('\na\rb\tc\fd\be')
        self.assertEqual(escaped, '\\na\\rb\\tc\\fd\\be')
