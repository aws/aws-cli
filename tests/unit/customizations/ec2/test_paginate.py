# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from argparse import Namespace

from awscli.testutils import unittest
from awscli.customizations.ec2.paginate import EC2PageSizeInjector


class TestEC2PageSizeInjector(unittest.TestCase):
    def test_register(self):
        target_operations = {
            'foo': [],
            'bar': []
        }
        injector = EC2PageSizeInjector()
        injector.TARGET_OPERATIONS = target_operations
        event_emitter = mock.Mock()
        injector.register(event_emitter)

        call_args = event_emitter.register_last.call_args_list
        events_registered = sorted([c[0][0] for c in call_args])
        expected_events = sorted([
            'calling-command.ec2.bar',
            'calling-command.ec2.foo'
        ])
        self.assertEqual(events_registered, expected_events)

    def test_inject(self):
        target_operations = {'foo': []}
        injector = EC2PageSizeInjector()
        injector.DEFAULT_PAGE_SIZE = 5
        injector.TARGET_OPERATIONS = target_operations
        parsed_globals = Namespace(paginate=True)
        call_parameters = {}
        event_name = 'operation-args-parsed.ec2.foo'
        injector.inject(
            event_name=event_name,
            parsed_globals=parsed_globals,
            call_parameters=call_parameters
        )
        page_size = call_parameters.get('PaginationConfig', {}).get('PageSize')
        self.assertEqual(page_size, 5)

    def test_no_paginate(self):
        target_operations = {'foo': []}
        injector = EC2PageSizeInjector()
        injector.TARGET_OPERATIONS = target_operations
        parsed_globals = Namespace(paginate=False)
        call_parameters = {}
        event_name = 'operation-args-parsed.ec2.foo'
        injector.inject(
            event_name=event_name,
            parsed_globals=parsed_globals,
            call_parameters=call_parameters
        )
        page_size = call_parameters.get('PaginationConfig', {}).get('PageSize')
        self.assertIsNone(page_size)

    def test_global_whitelist(self):
        target_operations = {'foo': []}
        injector = EC2PageSizeInjector()
        injector.UNIVERSAL_WHITELIST = ['bar']
        injector.TARGET_OPERATIONS = target_operations
        parsed_globals = Namespace(paginate=True)
        call_parameters = {'baz': True}
        event_name = 'operation-args-parsed.ec2.foo'
        injector.inject(
            event_name=event_name,
            parsed_globals=parsed_globals,
            call_parameters=call_parameters
        )
        page_size = call_parameters.get('PaginationConfig', {}).get('PageSize')
        self.assertIsNone(page_size)

    def test_operation_whitelist(self):
        target_operations = {'foo': ['bar']}
        injector = EC2PageSizeInjector()
        injector.UNIVERSAL_WHITELIST = []
        injector.TARGET_OPERATIONS = target_operations
        parsed_globals = Namespace(paginate=True)
        call_parameters = {'baz': True}
        event_name = 'operation-args-parsed.ec2.foo'
        injector.inject(
            event_name=event_name,
            parsed_globals=parsed_globals,
            call_parameters=call_parameters
        )
        page_size = call_parameters.get('PaginationConfig', {}).get('PageSize')
        self.assertIsNone(page_size)

    def test_non_target_operation(self):
        target_operations = {'foo': []}
        injector = EC2PageSizeInjector()
        injector.TARGET_OPERATIONS = target_operations
        parsed_globals = Namespace(paginate=True)
        call_parameters = {}
        event_name = 'operation-args-parsed.ec2.baz'
        injector.inject(
            event_name=event_name,
            parsed_globals=parsed_globals,
            call_parameters=call_parameters
        )
        page_size = call_parameters.get('PaginationConfig', {}).get('PageSize')
        self.assertIsNone(page_size)
