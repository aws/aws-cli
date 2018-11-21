# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.model import ServiceModel, OperationModel

from awscli.customizations.dynamodb.transform import ParameterTransformer
from awscli.testutils import unittest


class BaseTransformationTest(unittest.TestCase):
    def setUp(self):
        self.target_shape = 'MyShape'
        self.original_value = 'orginal'
        self.transformed_value = 'transformed'
        self.transformer = ParameterTransformer()
        self.json_model = {}
        self.nested_json_model = {}
        self.setup_models()
        self.build_models()

    def setup_models(self):
        self.json_model = {
            'operations': {
                'SampleOperation': {
                    'name': 'SampleOperation',
                    'input': {'shape': 'SampleOperationInputOutput'},
                    'output': {'shape': 'SampleOperationInputOutput'}
                }
            },
            'shapes': {
                'SampleOperationInputOutput': {
                    'type': 'structure',
                    'members': {}
                },
                'String': {
                    'type': 'string'
                }
            }
        }

    def build_models(self):
        self.service_model = ServiceModel(self.json_model)
        self.operation_model = OperationModel(
            self.json_model['operations']['SampleOperation'],
            self.service_model
        )

    def add_input_shape(self, shape):
        self.add_shape(shape)
        params_shape = self.json_model['shapes']['SampleOperationInputOutput']
        shape_name = list(shape.keys())[0]
        params_shape['members'][shape_name] = {'shape': shape_name}

    def add_shape(self, shape):
        shape_name = list(shape.keys())[0]
        self.json_model['shapes'][shape_name] = shape[shape_name]


class TestInputOutputTransformer(BaseTransformationTest):
    def setUp(self):
        super(TestInputOutputTransformer, self).setUp()
        self.transformation = lambda params: self.transformed_value
        self.add_shape({self.target_shape: {'type': 'string'}})

    def test_transform_structure(self):
        input_params = {
            'Structure': {
                'TransformMe': self.original_value,
                'LeaveAlone': self.original_value,
            }
        }
        input_shape = {
            'Structure': {
                'type': 'structure',
                'members': {
                    'TransformMe': {'shape': self.target_shape},
                    'LeaveAlone': {'shape': 'String'}
                }
            }
        }

        self.add_input_shape(input_shape)
        self.transformer.transform(
            params=input_params, model=self.operation_model.input_shape,
            transformation=self.transformation,
            target_shape=self.target_shape)
        self.assertEqual(
            input_params,
            {'Structure': {
                'TransformMe': self.transformed_value,
                'LeaveAlone': self.original_value}}
        )

    def test_transform_map(self):
        input_params = {
            'TransformMe': {'foo': self.original_value},
            'LeaveAlone': {'foo': self.original_value}
        }

        targeted_input_shape = {
            'TransformMe': {
                'type': 'map',
                'key': {'shape': 'String'},
                'value': {'shape': self.target_shape}
            }
        }

        untargeted_input_shape = {
            'LeaveAlone': {
                'type': 'map',
                'key': {'shape': 'String'},
                'value': {'shape': 'String'}
            }
        }

        self.add_input_shape(targeted_input_shape)
        self.add_input_shape(untargeted_input_shape)

        self.transformer.transform(
            params=input_params, model=self.operation_model.input_shape,
            transformation=self.transformation,
            target_shape=self.target_shape)
        self.assertEqual(
            input_params,
            {'TransformMe': {'foo': self.transformed_value},
             'LeaveAlone': {'foo': self.original_value}}
        )

    def test_transform_list(self):
        input_params = {
            'TransformMe': [
                self.original_value, self.original_value
            ],
            'LeaveAlone': [
                self.original_value, self.original_value
            ]
        }

        targeted_input_shape = {
            'TransformMe': {
                'type': 'list',
                'member': {'shape': self.target_shape}
            }
        }

        untargeted_input_shape = {
            'LeaveAlone': {
                'type': 'list',
                'member': {'shape': 'String'}
            }
        }

        self.add_input_shape(targeted_input_shape)
        self.add_input_shape(untargeted_input_shape)

        self.transformer.transform(
            params=input_params, model=self.operation_model.input_shape,
            transformation=self.transformation, target_shape=self.target_shape)
        self.assertEqual(
            input_params,
            {'TransformMe': [self.transformed_value, self.transformed_value],
             'LeaveAlone': [self.original_value, self.original_value]}
        )

    def test_transform_nested_structure(self):
        input_params = {
            'WrapperStructure': {
                'Structure': {
                    'TransformMe': self.original_value,
                    'LeaveAlone': self.original_value
                }
            }
        }

        structure_shape = {
            'Structure': {
                'type': 'structure',
                'members': {
                    'TransformMe': {'shape': self.target_shape},
                    'LeaveAlone': {'shape': 'String'}
                }
            }
        }

        input_shape = {
            'WrapperStructure': {
                'type': 'structure',
                'members': {'Structure': {'shape': 'Structure'}}}
        }
        self.add_shape(structure_shape)
        self.add_input_shape(input_shape)

        self.transformer.transform(
            params=input_params, model=self.operation_model.input_shape,
            transformation=self.transformation,
            target_shape=self.target_shape)
        self.assertEqual(
            input_params,
            {'WrapperStructure': {
                'Structure': {'TransformMe': self.transformed_value,
                              'LeaveAlone': self.original_value}}}
        )

    def test_transform_nested_map(self):
        input_params = {
            'TargetedWrapperMap': {
                'foo': {
                    'bar': self.original_value
                }
            },
            'UntargetedWrapperMap': {
                'foo': {
                    'bar': self.original_value
                }
            }

        }

        targeted_map_shape = {
            'TransformMeMap': {
                'type': 'map',
                'key': {'shape': 'String'},
                'value': {'shape': self.target_shape}
            }
        }

        targeted_wrapper_shape = {
            'TargetedWrapperMap': {
                'type': 'map',
                'key': {'shape': 'Name'},
                'value': {'shape': 'TransformMeMap'}}
        }

        self.add_shape(targeted_map_shape)
        self.add_input_shape(targeted_wrapper_shape)

        untargeted_map_shape = {
            'LeaveAloneMap': {
                'type': 'map',
                'key': {'shape': 'String'},
                'value': {'shape': 'String'}
            }
        }

        untargeted_wrapper_shape = {
            'UntargetedWrapperMap': {
                'type': 'map',
                'key': {'shape': 'Name'},
                'value': {'shape': 'LeaveAloneMap'}}
        }

        self.add_shape(untargeted_map_shape)
        self.add_input_shape(untargeted_wrapper_shape)

        self.transformer.transform(
            params=input_params, model=self.operation_model.input_shape,
            transformation=self.transformation, target_shape=self.target_shape)
        self.assertEqual(
            input_params,
            {'TargetedWrapperMap': {'foo': {'bar': self.transformed_value}},
             'UntargetedWrapperMap': {'foo': {'bar': self.original_value}}}
        )

    def test_transform_nested_list(self):
        input_params = {
            'TargetedWrapperList': [
                [self.original_value, self.original_value]
            ],
            'UntargetedWrapperList': [
                [self.original_value, self.original_value]
            ]
        }

        targeted_list_shape = {
            'TransformMe': {
                'type': 'list',
                'member': {'shape': self.target_shape}
            }
        }

        targeted_wrapper_shape = {
            'TargetedWrapperList': {
                'type': 'list',
                'member': {'shape': 'TransformMe'}}
        }

        self.add_shape(targeted_list_shape)
        self.add_input_shape(targeted_wrapper_shape)

        untargeted_list_shape = {
            'LeaveAlone': {
                'type': 'list',
                'member': {'shape': 'String'}
            }
        }

        untargeted_wrapper_shape = {
            'UntargetedWrapperList': {
                'type': 'list',
                'member': {'shape': 'LeaveAlone'}}
        }

        self.add_shape(untargeted_list_shape)
        self.add_input_shape(untargeted_wrapper_shape)

        self.transformer.transform(
            params=input_params, model=self.operation_model.input_shape,
            transformation=self.transformation,
            target_shape=self.target_shape)
        self.assertEqual(
            input_params,
            {'TargetedWrapperList': [[
                self.transformed_value, self.transformed_value]],
             'UntargetedWrapperList': [[
                 self.original_value, self.original_value]]}
        )

    def test_transform_incorrect_type_for_structure(self):
        input_params = {
            'Structure': 'foo'
        }

        input_shape = {
            'Structure': {
                'type': 'structure',
                'members': {
                    'TransformMe': {'shape': self.target_shape},
                }
            }
        }

        self.add_input_shape(input_shape)

        self.transformer.transform(
            params=input_params, model=self.operation_model.input_shape,
            transformation=self.transformation,
            target_shape=self.target_shape)
        self.assertEqual(input_params, {'Structure': 'foo'})

    def test_transform_incorrect_type_for_map(self):
        input_params = {
            'Map': 'foo'
        }

        input_shape = {
            'Map': {
                'type': 'map',
                'key': {'shape': 'String'},
                'value': {'shape': self.target_shape}
            }
        }

        self.add_input_shape(input_shape)

        self.transformer.transform(
            params=input_params, model=self.operation_model.input_shape,
            transformation=self.transformation,
            target_shape=self.target_shape)
        self.assertEqual(input_params, {'Map': 'foo'})

    def test_transform_incorrect_type_for_list(self):
        input_params = {
            'List': 'foo'
        }

        input_shape = {
            'List': {
                'type': 'list',
                'member': {'shape': self.target_shape}
            }
        }

        self.add_input_shape(input_shape)

        self.transformer.transform(
            params=input_params, model=self.operation_model.input_shape,
            transformation=self.transformation, target_shape=self.target_shape)
        self.assertEqual(input_params, {'List': 'foo'})
