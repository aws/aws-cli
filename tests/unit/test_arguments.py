# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import unittest
from awscli import arguments
from botocore.model import StringShape, OperationModel, ServiceModel


class DemoArgument(arguments.CustomArgument):
    pass


class TestArgumentClasses(unittest.TestCase):
    def test_can_set_required(self):
        arg = DemoArgument('test-arg')
        self.assertFalse(arg.required)
        arg.required = True
        self.assertTrue(arg.required)


class TestCLIArgument(unittest.TestCase):
    def setUp(self):
        self.service_name = 'baz'
        self.service_model = ServiceModel({
            'metadata': {
                'endpointPrefix': 'bad',
            },
            'operations': {
                'SampleOperation': {
                    'name': 'SampleOperation',
                    'input': {'shape': 'Input'}
                }
            },
            'shapes': {
                'StringShape': {'type': 'string'},
                'Input': {
                    'type': 'structure',
                    'members': {
                        'Foo': {'shape': 'StringShape'}
                    }
                }
            }
        }, self.service_name)
        self.operation_model = self.service_model.operation_model(
            'SampleOperation')
        self.argument_model = self.operation_model.input_shape.members['Foo']
        self.event_emitter = mock.Mock()

    def create_argument(self):
        return arguments.CLIArgument(
            self.argument_model.name, self.argument_model,
            self.operation_model, self.event_emitter)

    def test_unpack_uses_service_name_in_event(self):
        self.event_emitter.emit.return_value = ['value']
        argument = self.create_argument()
        params = {}
        argument.add_to_params(params, 'value')
        expected_event_name = 'process-cli-arg.%s.%s' % (
            self.service_name, 'sample-operation')
        actual_event_name = self.event_emitter.emit.call_args[0][0]
        self.assertEqual(actual_event_name, expected_event_name)

    def test_list_type_has_correct_nargs_value(self):
        # We don't actually care about the values, we just need a ListArgument
        # type.
        arg = arguments.ListArgument(
            argument_model=self.argument_model,
            event_emitter=self.event_emitter,
            is_required=True,
            name='test-nargs',
            operation_model=None,
            serialized_name='TestNargs'
        )
        self.assertEqual(arg.nargs, '*')
