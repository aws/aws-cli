# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.errorfactory import BaseClientExceptions, ClientExceptionsFactory
from botocore.exceptions import ClientError
from botocore.model import ServiceModel
from tests import unittest


class TestBaseClientExceptions(unittest.TestCase):
    def setUp(self):
        self.code_to_exception = {}
        self.exceptions = BaseClientExceptions(self.code_to_exception)

    def test_has_client_error(self):
        self.assertIs(self.exceptions.ClientError, ClientError)

    def test_from_code(self):
        exception_cls = type('MyException', (ClientError,), {})
        self.code_to_exception['MyExceptionCode'] = exception_cls
        self.assertIs(
            self.exceptions.from_code('MyExceptionCode'), exception_cls
        )

    def test_from_code_nonmatch_defaults_to_client_error(self):
        self.assertIs(
            self.exceptions.from_code('SomeUnknownErrorCode'), ClientError
        )

    def test_gettattr_message(self):
        exception_cls = type('MyException', (ClientError,), {})
        self.code_to_exception['MyExceptionCode'] = exception_cls
        with self.assertRaisesRegex(
            AttributeError, 'Valid exceptions are: MyException'
        ):
            self.exceptions.SomeUnmodeledError


class TestClientExceptionsFactory(unittest.TestCase):
    def setUp(self):
        self.model = {
            "metadata": {
                'endpointPrefix': 'myservice',
                'serviceFullName': 'MyService',
            },
            'operations': {
                'OperationName': {
                    'name': 'OperationName',
                    'errors': [
                        {'shape': 'ExceptionMissingCode'},
                        {'shape': 'ExceptionWithModeledCode'},
                    ],
                },
                'AnotherOperationName': {
                    'name': 'AnotherOperationName',
                    'errors': [
                        {'shape': 'ExceptionForAnotherOperation'},
                        {'shape': 'ExceptionWithModeledCode'},
                    ],
                },
            },
            'shapes': {
                'ExceptionWithModeledCode': {
                    'type': 'structure',
                    'members': {},
                    'error': {'code': 'ModeledCode'},
                    'exception': True,
                },
                'ExceptionMissingCode': {
                    'type': 'structure',
                    'members': {},
                    'exception': True,
                },
                'ExceptionForAnotherOperation': {
                    'type': 'structure',
                    'members': {},
                    'exception': True,
                },
            },
        }
        self.service_model = ServiceModel(self.model)
        self.exceptions_factory = ClientExceptionsFactory()

    def test_class_name(self):
        exceptions = self.exceptions_factory.create_client_exceptions(
            self.service_model
        )
        self.assertEqual(exceptions.__class__.__name__, 'MyServiceExceptions')

    def test_creates_modeled_exception(self):
        exceptions = self.exceptions_factory.create_client_exceptions(
            self.service_model
        )
        self.assertTrue(hasattr(exceptions, 'ExceptionWithModeledCode'))
        modeled_exception = exceptions.ExceptionWithModeledCode
        self.assertEqual(
            modeled_exception.__name__, 'ExceptionWithModeledCode'
        )
        self.assertTrue(issubclass(modeled_exception, ClientError))

    def test_collects_modeled_exceptions_for_all_operations(self):
        exceptions = self.exceptions_factory.create_client_exceptions(
            self.service_model
        )
        # Make sure exceptions were added for all operations by checking
        # an exception only found on an a different operation.
        self.assertTrue(hasattr(exceptions, 'ExceptionForAnotherOperation'))
        modeled_exception = exceptions.ExceptionForAnotherOperation
        self.assertEqual(
            modeled_exception.__name__, 'ExceptionForAnotherOperation'
        )
        self.assertTrue(issubclass(modeled_exception, ClientError))

    def test_creates_modeled_exception_mapping_that_has_code(self):
        exceptions = self.exceptions_factory.create_client_exceptions(
            self.service_model
        )
        exception = exceptions.from_code('ModeledCode')
        self.assertEqual(exception.__name__, 'ExceptionWithModeledCode')
        self.assertTrue(issubclass(exception, ClientError))

    def test_creates_modeled_exception_mapping_that_has_no_code(self):
        exceptions = self.exceptions_factory.create_client_exceptions(
            self.service_model
        )
        # For exceptions that do not have an explicit code associated to them,
        # the code is the name of the exception.
        exception = exceptions.from_code('ExceptionMissingCode')
        self.assertEqual(exception.__name__, 'ExceptionMissingCode')
        self.assertTrue(issubclass(exception, ClientError))
