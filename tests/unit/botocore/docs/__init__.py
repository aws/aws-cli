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
import json
import os
import shutil
import tempfile

from botocore.client import ClientCreator
from botocore.compat import OrderedDict
from botocore.configprovider import ConfigValueStore
from botocore.docs.bcdoc.restdoc import DocumentStructure
from botocore.hooks import HierarchicalEmitter
from botocore.loaders import Loader
from botocore.model import OperationModel, ServiceModel
from tests import get_botocore_default_config_mapping, mock, unittest


class BaseDocsTest(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        self.version_dirs = os.path.join(
            self.root_dir, 'myservice', '2014-01-01'
        )
        os.makedirs(self.version_dirs)
        self.model_file = os.path.join(self.version_dirs, 'service-2.json')
        self.waiter_model_file = os.path.join(
            self.version_dirs, 'waiters-2.json'
        )
        self.paginator_model_file = os.path.join(
            self.version_dirs, 'paginators-1.json'
        )
        self.example_model_file = os.path.join(
            self.version_dirs, 'examples-1.json'
        )
        self.docs_root_dir = tempfile.mkdtemp()
        self.root_services_path = os.path.join(
            self.docs_root_dir, 'reference', 'services'
        )

        self.json_model = {}
        self.nested_json_model = {}
        self._setup_models()
        self.build_models()
        self.events = HierarchicalEmitter()
        self.setup_client()
        self.doc_name = 'MyDoc'
        self.doc_structure = DocumentStructure(self.doc_name, target='html')

    def tearDown(self):
        shutil.rmtree(self.root_dir)
        shutil.rmtree(self.docs_root_dir)

    def setup_client(self):
        with open(self.example_model_file, 'w') as f:
            json.dump(self.example_json_model, f)

        with open(self.waiter_model_file, 'w') as f:
            json.dump(self.waiter_json_model, f)

        with open(self.paginator_model_file, 'w') as f:
            json.dump(self.paginator_json_model, f)

        with open(self.model_file, 'w') as f:
            json.dump(self.json_model, f)

        myservice_endpoint_rule_set = {
            "version": "1.3",
            "parameters": {},
            "rules": [
                {
                    "conditions": [],
                    "endpoint": {
                        "url": "https://example.com",
                        "properties": {},
                        "headers": {},
                    },
                    "type": "endpoint",
                }
            ],
        }

        def load_service_mock(*args, **kwargs):
            if args[1] == "endpoint-rule-set-1":
                return myservice_endpoint_rule_set
            else:
                return Loader(
                    extra_search_paths=[self.root_dir]
                ).load_service_model(*args, **kwargs)

        self.loader = Loader(extra_search_paths=[self.root_dir])
        self.loader.load_service_model = mock.Mock()
        self.loader.load_service_model.side_effect = load_service_mock

        endpoint_resolver = mock.Mock()
        endpoint_resolver.construct_endpoint.return_value = {
            'hostname': 'foo.us-east-1',
            'partition': 'aws',
            'endpointName': 'us-east-1',
            'signatureVersions': ['v4'],
        }

        default_config_mapping = get_botocore_default_config_mapping()
        self.creator = ClientCreator(
            loader=self.loader,
            endpoint_resolver=endpoint_resolver,
            user_agent='user-agent',
            event_emitter=self.events,
            retry_handler_factory=mock.Mock(),
            retry_config_translator=mock.Mock(),
            exceptions_factory=mock.Mock(),
            config_store=ConfigValueStore(mapping=default_config_mapping),
        )

        self.client = self.creator.create_client('myservice', 'us-east-1')

    def _setup_models(self):
        self.json_model = {
            'metadata': {
                'apiVersion': '2014-01-01',
                'endpointPrefix': 'myservice',
                'signatureVersion': 'v4',
                'serviceFullName': 'AWS MyService',
                'uid': 'myservice-2014-01-01',
                'protocol': 'query',
                'serviceId': 'MyService',
            },
            'operations': {
                'SampleOperation': {
                    'name': 'SampleOperation',
                    'input': {'shape': 'SampleOperationInputOutput'},
                    'output': {'shape': 'SampleOperationInputOutput'},
                }
            },
            'shapes': {
                'SampleOperationInputOutput': {
                    'type': 'structure',
                    'members': OrderedDict(),
                },
                'String': {'type': 'string'},
            },
            'documentation': 'AWS MyService Description',
        }

        self.waiter_json_model = {
            "version": 2,
            "waiters": {
                "SampleOperationComplete": {
                    "delay": 15,
                    "operation": "SampleOperation",
                    "maxAttempts": 40,
                    "acceptors": [
                        {
                            "expected": "complete",
                            "matcher": "pathAll",
                            "state": "success",
                            "argument": "Biz",
                        },
                        {
                            "expected": "failed",
                            "matcher": "pathAny",
                            "state": "failure",
                            "argument": "Biz",
                        },
                    ],
                }
            },
        }

        self.paginator_json_model = {
            "pagination": {
                "SampleOperation": {
                    "input_token": "NextResult",
                    "output_token": "NextResult",
                    "limit_key": "MaxResults",
                    "result_key": "Biz",
                }
            }
        }

        self.example_json_model = {
            "version": 1,
            "examples": {
                "SampleOperation": [
                    {
                        "id": "sample-id",
                        "title": "sample-title",
                        "description": "Sample Description.",
                        "input": OrderedDict(
                            [
                                ("Biz", "foo"),
                            ]
                        ),
                        "comments": {
                            "input": {"Biz": "bar"},
                        },
                    }
                ]
            },
        }

    def get_nested_service_contents(self, service, type, name):
        service_file_path = os.path.join(
            self.root_services_path, service, type, f'{name}.rst'
        )
        with open(service_file_path, 'rb') as f:
            return f.read().decode('utf-8')

    def build_models(self):
        self.service_model = ServiceModel(self.json_model)
        self.operation_model = OperationModel(
            self.json_model['operations']['SampleOperation'],
            self.service_model,
        )

    def add_shape(self, shape):
        shape_name = list(shape.keys())[0]
        self.json_model['shapes'][shape_name] = shape[shape_name]

    def add_shape_to_params(
        self, param_name, shape_name, documentation=None, is_required=False
    ):
        params_shape = self.json_model['shapes']['SampleOperationInputOutput']
        member = {'shape': shape_name}
        if documentation is not None:
            member['documentation'] = documentation
        params_shape['members'][param_name] = member

        if is_required:
            required_list = params_shape.get('required', [])
            required_list.append(param_name)
            params_shape['required'] = required_list

    def add_shape_to_errors(self, shape_name):
        operation = self.json_model['operations']['SampleOperation']
        errors = operation.get('errors', [])
        errors.append({'shape': shape_name})
        operation['errors'] = errors

    def assert_contains_line(self, line):
        contents = self.doc_structure.flush_structure().decode('utf-8')
        self.assertIn(line, contents)

    def assert_contains_lines_in_order(self, lines, contents=None):
        if contents is None:
            contents = self.doc_structure.flush_structure().decode('utf-8')
        for line in lines:
            self.assertIn(line, contents)
            beginning = contents.find(line)
            contents = contents[(beginning + len(line)) :]

    def assert_not_contains_line(self, line):
        contents = self.doc_structure.flush_structure().decode('utf-8')
        self.assertNotIn(line, contents)

    def assert_not_contains_lines(self, lines):
        contents = self.doc_structure.flush_structure().decode('utf-8')
        for line in lines:
            self.assertNotIn(line, contents)
