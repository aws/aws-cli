# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import unittest
from tests.unit import BaseAWSCommandParamsTest
import sys
import re

import mock
import six
import httpretty

import awscli
from awscli.clidriver import CLIDriver
from awscli.clidriver import create_clidriver
from botocore.hooks import HierarchicalEmitter
from botocore.base import get_search_path


GET_DATA = {
    'cli': {
        'description': 'description',
        'synopsis': 'usage: foo',
        'options': {
            "service_name": {
                "choices": "{provider}/_services",
                "metavar": "service_name"
            },
            "--debug": {
                "action": "store_true",
                "help": "Turn on debug logging"
            },
            "--output": {
                "choices": [
                    "json",
                    "text",
                    "table"
                ],
                "metavar": "output_format"
            },
            "--profile": {
                "help": "Use a specific profile from your credential file",
                "metavar": "profile_name"
            },
            "--region": {
                "choices": "{provider}/_regions",
                "metavar": "region_name"
            },
            "--endpoint-url": {
                "help": "Override service's default URL with the given URL",
                "metavar": "endpoint_url"
            },
            "--no-verify-ssl": {
                "action": "store_true",
                "help": "Override default behavior of verifying SSL certificates"
            },
            "--no-paginate": {
                "action": "store_false",
                "help": "Disable automatic pagination",
                "dest": "paginate"
            },
        }
    },
    'aws/_services': {'s3':{}},
    'aws/_regions': {},
}

GET_VARIABLE = {
    'provider': 'aws',
    'output': 'json',
}


class FakeSession(object):
    def __init__(self, emitter=None):
        self.operation = None
        if emitter is None:
            emitter = HierarchicalEmitter()
        self.emitter = emitter

    def register(self, event_name, handler):
        self.emitter.register(event_name, handler)

    def emit(self, event_name, **kwargs):
        return self.emitter.emit(event_name, **kwargs)

    def get_available_services(self):
        return ['s3']

    def get_data(self, name):
        return GET_DATA[name]

    def get_variable(self, name):
        return GET_VARIABLE[name]

    def get_service(self, name):
        # Get service returns a service object,
        # so we'll just return a Mock object with
        # enough of the "right stuff".
        service = mock.Mock()
        list_objects = mock.Mock(name='operation')
        list_objects.cli_name = 'list-objects'
        list_objects.params = []
        operation = mock.Mock()
        param = mock.Mock()
        param.type = 'string'
        param.py_name = 'bucket'
        param.cli_name = '--bucket'
        param.name = 'bucket'
        operation.params = [param]
        operation.cli_name = 'list-objects'
        operation.name = 'ListObjects'
        operation.is_streaming.return_value = False
        operation.paginate.return_value.build_full_result.return_value = {
            'foo': 'paginate'}
        operation.call.return_value = (mock.Mock(), {'foo': 'bar'})
        self.operation = operation
        service.operations = [list_objects]
        service.cli_name = 's3'
        service.endpoint_prefix = 's3'
        service.get_operation.return_value = operation
        operation.service = service
        operation.service.session = self
        return service

    def get_service_data(self, service_name):
        import botocore.session
        s = botocore.session.get_session()
        actual = s.get_service_data(service_name)
        foo = actual['operations']['ListObjects']['input']['members']
        return {'operations': {'ListObjects': {'input': {
            'members': dict.fromkeys(
                ['Bucket', 'Delimiter', 'Marker', 'MaxKeys', 'Prefix']),
        }}}}


    def user_agent(self):
        return 'user_agent'


class TestCliDriver(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()

    def test_session_can_be_passed_in(self):
        driver = CLIDriver(session=self.session)
        self.assertEqual(driver.session, self.session)

    def test_paginate_rc(self):
        driver = CLIDriver(session=self.session)
        rc = driver.main('s3 list-objects --bucket foo'.split())
        self.assertEqual(rc, 0)


class TestCliDriverHooks(unittest.TestCase):
    # These tests verify the proper hooks are emitted in clidriver.
    def setUp(self):
        self.session = FakeSession()
        self.emitter = mock.Mock()
        self.emitter.emit.return_value = []
        self.stdout = six.StringIO()
        self.stderr = six.StringIO()
        self.stdout_patch = mock.patch('sys.stdout', self.stdout)
        self.stdout_patch.start()
        self.stderr_patch = mock.patch('sys.stderr', self.stderr)
        self.stderr_patch.start()

    def tearDown(self):
        self.stdout_patch.stop()
        self.stderr_patch.stop()

    def assert_events_fired_in_order(self, events):
        args = self.emitter.emit.call_args_list
        actual_events = [arg[0][0] for arg in args]
        self.assertEqual(actual_events, events)

    def serialize_param(self, param, value, **kwargs):
        if param.py_name == 'bucket':
            return value + '-altered!'

    def test_expected_events_are_emitted_in_order(self):
        self.emitter.emit.return_value = []
        self.session.emitter = self.emitter
        driver = CLIDriver(session=self.session)
        driver.main('s3 list-objects --bucket foo'.split())
        self.assert_events_fired_in_order([
            # Events fired while parser is being created.
            'building-command-table',
            'building-operation-table.s3',
            'building-argument-table.s3.ListObjects',
            'process-cli-arg.s3.list-objects',
        ])

    def test_cli_driver_changes_args(self):
        emitter = HierarchicalEmitter()
        emitter.register('process-cli-arg.s3.list-objects', self.serialize_param)
        self.session.emitter = emitter
        driver = CLIDriver(session=self.session)
        driver.main('s3 list-objects --bucket foo'.split())
        self.assertIn(mock.call.paginate(mock.ANY, bucket='foo-altered!'),
                      self.session.operation.method_calls)

    def test_unknown_params_raises_error(self):
        driver = CLIDriver(session=self.session)
        rc = driver.main('s3 list-objects --bucket foo --unknown-arg foo'.split())
        self.assertEqual(rc, 255)
        self.assertIn('Unknown options', self.stderr.getvalue())

    def test_unknown_command_suggests_help(self):
        driver = CLIDriver(session=self.session)
        # We're catching SystemExit here because this is raised from the bowels
        # of argparser so short of patching the ArgumentParser's exit() method,
        # we can just catch SystemExit.
        with self.assertRaises(SystemExit):
            # Note the typo in 'list-objects'
            driver.main('s3 list-objecst --bucket foo --unknown-arg foo'.split())
        # Tell the user what went wrong.
        self.assertIn("Invalid choice: 'list-objecst'", self.stderr.getvalue())
        # Offer the user a suggestion.
        self.assertIn("maybe you meant:\n\n  * list-objects", self.stderr.getvalue())


class TestSearchPath(unittest.TestCase):
    def tearDown(self):
        six.moves.reload_module(awscli)

    @mock.patch('os.pathsep', ';')
    @mock.patch('os.environ', {'AWS_DATA_PATH': 'c:\\foo;c:\\bar'})
    def test_windows_style_search_path(self):
        driver = CLIDriver()
        # Because the os.environ patching happens at import time,
        # we have to force a reimport of the module to test our changes.
        six.moves.reload_module(awscli)
        # Our two overrides should be the last two elements in the search path.
        search_path = get_search_path(driver.session)[-2:]
        self.assertEqual(search_path, ['c:\\foo', 'c:\\bar'])


class TestAWSCommand(BaseAWSCommandParamsTest):
    # These tests will simulate running actual aws commands
    # but with the http part mocked out.
    def last_request_headers(self):
        return httpretty.httpretty.last_request.headers

    def test_aws_with_region(self):
        driver = create_clidriver()
        driver.main('ec2 describe-instances --region us-east-1'.split())
        host = self.last_request_headers()['Host']
        self.assertEqual(host, 'ec2.us-east-1.amazonaws.com')

        driver.main('ec2 describe-instances --region us-west-2'.split())
        host = self.last_request_headers()['Host']
        self.assertEqual(host, 'ec2.us-west-2.amazonaws.com')


if __name__ == '__main__':
    unittest.main()
