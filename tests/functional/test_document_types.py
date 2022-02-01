# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import copy
import json
import os

from botocore.loaders import Loader

from awscli.testutils import (
    create_clidriver, FileCreator, BaseAWSCommandParamsTest,
    BaseAWSHelpOutputTest
)

# NOTE: Typically, the functional tests reuse preexisting models. However
# because document types was released without any service model using them,
# we are using through a fake service model to fully test document type
# behavior.
DOCTYPE_MODEL = {
    "version": "2.0",
    "metadata": {
        "apiVersion": "2011-06-15",
        "endpointPrefix": "doctype",
        "protocol": "json",
        "jsonVersion": "1.1",
        "serviceAbbreviation": "AWS DocType",
        "serviceFullName": "AWS DocType",
        "serviceId": "DocType",
        "signatureVersion": "v4",
        "targetPrefix": "DocType",
        "uid": "doctype-2011-06-15",
    },
    "operations": {
        "DescribeResource": {
            "name": "DescribeResource",
            "http": {
                "method": "POST",
                "requestUri": "/"
            },
            "input": {"shape": "DescribeResourceShape"},
            "output": {"shape": "DescribeResourceShape"},
            "errors": [],
            "documentation": "<p>Describes resource.</p>"
        }
    },
    "shapes": {
        "DescribeResourceShape": {
            "type": "structure",
            "members": {
                "DocTypeParam": {"shape": "DocType"},
                "ModeledMixedWithDocTypeParam": {"shape": "Mixed"},
                "ListOfDocTypesParam": {"shape": "ListOfDocTypes"},
                "MapOfDocTypesParam": {"shape": "MapOfDocTypes"},
                "NestedListsOfDocTypesParam": {
                    "shape": "NestedListsOfDocTypes"
                }
            }
        },
        "DocType": {
            "type": "structure",
            "members": {},
            "document": True,
            "documentation": "<p>Document type</p>"
        },
        "ListOfDocTypes": {
            "type": "list",
            "member": {"shape": "DocType"}
        },
        "MapOfDocTypes": {
            "type": "map",
            "key": {"shape": "String"},
            "value": {"shape": "DocType"}
        },
        "NestedListsOfDocTypes": {
            "type": "list",
            "member": {"shape": "ListOfDocTypes"}
        },
        "Mixed": {
            "type": "structure",
            "members": {
                "DocType": {"shape": "DocType"},
                "StringMember": {"shape": "String"},
                "ListOfDocTypes": {"shape": "ListOfDocTypes"},
                "MapOfDocTypes": {"shape": "MapOfDocTypes"},
                "NestedListsOfDocTypes": {"shape": "NestedListsOfDocTypes"}
            },
            "documentation": (
                "<p>Structure with modeled and document type parameter</p>"),
        },
        "String": {"type": "string"}
    }
}


def _add_doctype_service_model(file_creator, session, model=None):
    if model is None:
        model = DOCTYPE_MODEL
    file_creator.create_file(
        os.path.join('doctype', '2011-06-15', 'service-2.json'),
        json.dumps(model)
    )
    data_path = session.get_config_variable('data_path').split(os.pathsep)
    loader = Loader()
    loader.search_paths.extend(data_path + [file_creator.rootdir])
    session.register_component('data_loader', loader)


class TestDocumentTypeIO(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestDocumentTypeIO, self).setUp()
        self.files = FileCreator()
        _add_doctype_service_model(self.files, self.driver.session)

    def tearDown(self):
        super(TestDocumentTypeIO, self).tearDown()
        self.files.remove_all()

    def assert_raises_shorthand_syntax_error(self, cmdline,
                                             stderr_contains=None):
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=255)
        if stderr_contains:
            self.assertIn(stderr_contains, stderr)

    def nested_doctype_shorthand_error(self, parameter_name, member_name):
        return (
            "Error parsing parameter '%s': Shorthand syntax does not support "
            "document types. Use JSON input for top-level argument to specify "
            "nested parameter: %s" % (parameter_name, member_name)
        )

    def test_can_provide_json_for_doc_type(self):
        cmdline = [
            'doctype', 'describe-resource', '--doc-type-param',
            '{"foo":"bar"}'
        ]
        self.assert_params_for_cmd(
            cmdline, params={'DocTypeParam': {"foo": "bar"}})

    def test_can_provide_json_for_doc_type_with_scalar_value(self):
        cmdline = [
            'doctype', 'describe-resource', '--doc-type-param',
            '"json-string"'
        ]
        self.assert_params_for_cmd(
            cmdline, params={'DocTypeParam': 'json-string'})

    def test_can_provide_json_for_doc_type_in_list(self):
        cmdline = [
            'doctype', 'describe-resource', '--list-of-doc-types-param',
            '["foo", {"bar": "baz"}, 1, null]'
        ]
        self.assert_params_for_cmd(
            cmdline,
            params={'ListOfDocTypesParam': ["foo", {"bar": "baz"}, 1, None]}
        )

    def test_can_provide_json_for_doc_type_in_map(self):
        cmdline = [
            'doctype', 'describe-resource', '--map-of-doc-types-param',
            '{"key1": "foo", "key2": {"bar": "baz"}, "key3": 1}'
        ]
        self.assert_params_for_cmd(
            cmdline,
            params={
                'MapOfDocTypesParam': {
                    "key1": "foo",
                    "key2": {"bar": "baz"},
                    "key3": 1
                }
            }
        )

    def test_can_provide_json_for_doc_type_in_nested_list(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--nested-lists-of-doc-types-param',
            '[["foo", {"bar": "baz"}, 1, null]]'
        ]
        self.assert_params_for_cmd(
            cmdline,
            params={
                'NestedListsOfDocTypesParam': [
                    ["foo", {"bar": "baz"}, 1, None]
                ]
            }
        )

    def test_can_provide_json_for_nested_doc_type(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--modeled-mixed-with-doc-type-param',
            (
                '{'
                '   "DocType": {"foo": "bar"},'
                '   "ListOfDocTypes": ["foo", {"bar": "baz"}, 1, null],'
                '   "MapOfDocTypes": {'
                '       "key1": "foo", "key2": {"bar": "baz"}, "key3": 1},'
                '   "NestedListsOfDocTypes":[["foo", {"bar": "baz"}, 1, null]]'
                '}'
            )
        ]
        self.assert_params_for_cmd(
            cmdline,
            params={
                'ModeledMixedWithDocTypeParam': {
                    'DocType': {'foo': 'bar'},
                    'ListOfDocTypes': ["foo", {"bar": "baz"}, 1, None],
                    'MapOfDocTypes': {
                        "key1": "foo",
                        "key2": {"bar": "baz"},
                        "key3": 1
                    },
                    'NestedListsOfDocTypes': [["foo", {"bar": "baz"}, 1, None]]
                }
            }
        )

    def test_shorthand_not_supported_for_doc_type_argument(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--doc-type-param', 'foo=1',
        ]
        self.assert_raises_shorthand_syntax_error(
            cmdline,
            stderr_contains=(
                "Error parsing parameter '--doc-type-param': Invalid JSON"
            )
        )

    def test_shorthand_not_supported_for_doc_type_in_list(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--list-of-doc-types-param', 'bar,1,null',
        ]
        self.assert_raises_shorthand_syntax_error(
            cmdline,
            stderr_contains=(
                "Error parsing parameter '--list-of-doc-types-param': "
                "Invalid JSON"
            )
        )

    def test_shorthand_not_supported_for_doc_type_in_map(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--map-of-doc-types-param', 'key1={foo=bar}',
        ]
        self.assert_raises_shorthand_syntax_error(
            cmdline,
            stderr_contains=(
                "Error parsing parameter '--map-of-doc-types-param': "
                "Invalid JSON"
            )
        )

    def test_shorthand_not_supported_for_doc_type_in_nested_list(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--nested-lists-of-doc-types-param', '[bar,1,null],[foo,2]',
        ]
        self.assert_raises_shorthand_syntax_error(
            cmdline,
            stderr_contains=(
                "Error parsing parameter '--nested-lists-of-doc-types-param': "
                "Invalid JSON"
            )
        )

    def test_shorthand_not_supported_for_nested_doc_type(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--modeled-mixed-with-doc-type-param',
            'DocType={foo=bar}',
        ]
        self.assert_raises_shorthand_syntax_error(
            cmdline,
            stderr_contains=self.nested_doctype_shorthand_error(
                '--modeled-mixed-with-doc-type-param', member_name='DocType'
            )
        )

    def test_shorthand_not_supported_for_nested_doc_type_in_list(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--modeled-mixed-with-doc-type-param',
            'ListOfDocTypes=[{foo=bar}]',
        ]
        self.assert_raises_shorthand_syntax_error(
            cmdline,
            stderr_contains=self.nested_doctype_shorthand_error(
                '--modeled-mixed-with-doc-type-param',
                member_name='ListOfDocTypes'
            )
        )

    def test_shorthand_not_supported_for_nested_doc_type_in_map(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--modeled-mixed-with-doc-type-param',
            'MapOfDocTypes={key={foo=bar}}',
        ]
        self.assert_raises_shorthand_syntax_error(
            cmdline,
            stderr_contains=self.nested_doctype_shorthand_error(
                '--modeled-mixed-with-doc-type-param',
                member_name='MapOfDocTypes'
            )
        )

    def test_shorthand_not_supported_for_nested_doc_type_in_nested_list(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--modeled-mixed-with-doc-type-param',
            'NestedListsOfDocTypes=[[{foo=bar}]]',
        ]
        self.assert_raises_shorthand_syntax_error(
            cmdline,
            stderr_contains=self.nested_doctype_shorthand_error(
                '--modeled-mixed-with-doc-type-param',
                member_name='NestedListsOfDocTypes'
            )
        )

    def test_can_use_shorthand_if_only_modeled_members_used(self):
        cmdline = [
            'doctype', 'describe-resource',
            '--modeled-mixed-with-doc-type-param',
            'StringMember=str-val',
        ]
        self.assert_params_for_cmd(
            cmdline,
            params={
                'ModeledMixedWithDocTypeParam': {
                    'StringMember': 'str-val',
                }
            }
        )

    def test_can_generate_cli_skeleton(self):
        cmdline = [
            'doctype', 'describe-resource', '--generate-cli-skeleton'
        ]
        stdout, _, _ = self.run_cmd(cmdline)
        skeleton_output = json.loads(stdout)
        self.assertEqual(
            skeleton_output,
            {
                'DocTypeParam': {},
                'ModeledMixedWithDocTypeParam': {
                    'DocType': {},
                    'StringMember': '',
                    'ListOfDocTypes': [{}],
                    'MapOfDocTypes': {'KeyName': {}},
                    'NestedListsOfDocTypes': [[{}]]
                },
                'ListOfDocTypesParam': [{}],
                'MapOfDocTypesParam': {'KeyName': {}},
                'NestedListsOfDocTypesParam': [[{}]]
            }
        )


class TestDocTypesHelp(BaseAWSHelpOutputTest):
    def setUp(self):
        super(TestDocTypesHelp, self).setUp()
        self.files = FileCreator()
        _add_doctype_service_model(self.files, self.driver.session)

    def tearDown(self):
        super(TestDocTypesHelp, self).tearDown()
        self.files.remove_all()

    def run_help(self):
        self.driver.main(
            ['doctype', 'describe-resource', 'help'])

    def filter_params_in_model(self, include_params):
        model = copy.deepcopy(DOCTYPE_MODEL)
        request_members = model['shapes']['DescribeResourceShape']['members']
        for request_member in list(request_members):
            if request_member not in include_params:
                del request_members[request_member]

        self.driver = create_clidriver()
        _add_doctype_service_model(self.files, self.driver.session, model)

    def assert_has_document_value_in_json_syntax(self, parameter):
        self.assert_text_order(
            'JSON Syntax::',
            '{...}',
            starting_from=parameter
        )

    def assert_no_shorthand_syntax(self):
        self.assert_not_contains('Shorthand Sytanx::')

    def test_includes_note_about_document_types(self):
        self.run_help()
        self.assert_contains('uses document type values')

    def test_does_not_include_note_if_no_document_types(self):
        self.filter_params_in_model([])
        self.assert_not_contains('uses document type values')

    def test_annotates_as_document_type_for_input(self):
        self.run_help()
        self.assert_contains('``--doc-type-param`` (document)')

    def test_annotates_as_document_type_for_output(self):
        self.run_help()
        self.assert_contains('DocTypeParam -> (document)')

    def test_json_syntax_for_doc_type_argument(self):
        self.filter_params_in_model(include_params=['DocTypeParam'])
        self.run_help()
        self.assert_has_document_value_in_json_syntax(
            parameter='--doc-type-param')

    def test_json_syntax_for_doc_type_in_list(self):
        self.filter_params_in_model(include_params=['ListOfDocTypesParam'])
        self.run_help()
        self.assert_has_document_value_in_json_syntax(
            parameter='--list-of-doc-types-param')

    def test_json_syntax_for_doc_type_in_map(self):
        self.filter_params_in_model(include_params=['MapOfDocTypesParam'])
        self.run_help()
        self.assert_has_document_value_in_json_syntax(
            parameter='--map-of-doc-types-param')

    def test_json_syntax_for_doc_type_in_nested_list(self):
        self.filter_params_in_model(
            include_params=['NestedListsOfDocTypesParam'])
        self.run_help()
        self.assert_has_document_value_in_json_syntax(
            parameter='--nested-lists-of-doc-types-param')

    def test_json_syntax_for_nested_doc_type(self):
        self.filter_params_in_model(
            include_params=['ModeledMixedWithDocTypeParam'])
        self.run_help()
        self.assert_text_order(
            'JSON Syntax::',
            '"DocType": {...},',
            '"ListOfDocTypes": [',
            '"MapOfDocTypes": {"string": {...}',
            '"NestedListsOfDocTypes": [',
            starting_from='--modeled-mixed-with-doc-type-param'
        )

    def test_shorthand_not_documented_for_doc_type_argument(self):
        self.filter_params_in_model(include_params=['DocTypeParam'])
        self.run_help()
        self.assert_no_shorthand_syntax()

    def test_shorthand_not_documented_for_doc_type_in_list(self):
        self.filter_params_in_model(include_params=['ListOfDocTypesParam'])
        self.run_help()
        self.assert_no_shorthand_syntax()

    def test_shorthand_not_documented_for_doc_type_in_map(self):
        self.filter_params_in_model(include_params=['MapOfDocTypesParam'])
        self.run_help()
        self.assert_no_shorthand_syntax()

    def test_shorthand_not_documented_for_doc_type_in_nested_list(self):
        self.filter_params_in_model(
            include_params=['NestedListsOfDocTypesParam'])
        self.run_help()
        self.assert_no_shorthand_syntax()

    def test_documents_shorthand_for_only_modeled_members(self):
        self.filter_params_in_model(
            include_params=['ModeledMixedWithDocTypeParam'])
        self.run_help()
        self.assert_text_order(
            'Shorthand Syntax::',
            'StringMember=string',
            starting_from='--modeled-mixed-with-doc-type-param'
        )
        self.assert_not_contains('DocTypeParam=')
        self.assert_not_contains('ListOfDocTypesParam=')
        self.assert_not_contains('MapOfDocTypesParam=')
        self.assert_not_contains('NestedListsOfDocTypesParam=')
