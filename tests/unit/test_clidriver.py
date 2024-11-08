# -*- coding: utf-8 -*-
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
import contextlib
import platform
import re

from awscli.testutils import unittest
from awscli.testutils import BaseAWSCommandParamsTest
import logging
import io

from awscli.testutils import mock

import awscrt.io
from botocore import xform_name
import sys

from botocore.awsrequest import AWSResponse
from botocore.exceptions import NoCredentialsError
from botocore.compat import OrderedDict
import botocore.model

import awscli
from awscli.clidriver import CLIDriver
from awscli.clidriver import create_clidriver
from awscli.clidriver import CustomArgument
from awscli.clidriver import CLICommand
from awscli.clidriver import construct_cli_error_handlers_chain
from awscli.clidriver import ServiceCommand
from awscli.clidriver import ServiceOperation
from awscli.paramfile import URIArgumentHandler
from awscli.customizations.commands import BasicCommand
from awscli import formatter
from awscli.argparser import HELP_BLURB
from awscli.compat import StringIO
from botocore.hooks import HierarchicalEmitter
from botocore.configprovider import create_botocore_default_config_mapping
from botocore.configprovider import ConfigChainFactory
from botocore.configprovider import ConfigValueStore


GET_DATA = {
    'cli': {
        'description': 'description',
        'synopsis': 'usage: foo',
        'options': {
            "debug": {
                "action": "store_true",
                "help": "Turn on debug logging"
            },
            "output": {
                "choices": [
                    "json",
                    "text",
                    "table"
                ],
                "metavar": "output_format"
            },
            "query": {
                "help": ""
            },
            "profile": {
                "help": "",
                "metavar": "profile_name"
            },
            "region": {
                "metavar": "region_name"
            },
            "endpoint-url": {
                "help": "",
                "metavar": "endpoint_url"
            },
            "no-verify-ssl": {
                "action": "store_false",
                "dest": "verify_ssl",
                "help": "",
            },
            "no-paginate": {
                "action": "store_false",
                "help": "",
                "dest": "paginate"
            },
            "page-size": {
                "type": "int",
                "help": "",
            },
            "read-timeout": {
                "type": "int",
                "help": ""
            },
            "connect-timeout": {
                "type": "int",
                "help": ""
            }
        }
    },
}

GET_VARIABLE = {
    'provider': 'aws',
    'output': 'json',
    'api_versions': {},
    'pager': 'less'
}


MINI_SERVICE = {
  "metadata":{
    "apiVersion":"2006-03-01",
    "endpointPrefix":"s3",
    "globalEndpoint":"s3.amazonaws.com",
    "signatureVersion":"s3",
    "protocol":"rest-xml"
  },
  "operations":{
    "ListObjects":{
      "name":"ListObjects",
      "http":{
        "method":"GET",
        "requestUri":"/{Bucket}"
      },
      "input":{"shape":"ListObjectsRequest"},
      "output":{"shape":"ListObjectsOutput"},
    },
    "IdempotentOperation":{
      "name":"IdempotentOperation",
      "http":{
        "method":"GET",
        "requestUri":"/{Bucket}"
      },
      "input":{"shape":"IdempotentOperationRequest"},
      "output":{"shape":"ListObjectsOutput"},
    },
  },
  "shapes":{
    "ListObjectsOutput":{
      "type":"structure",
      "members":{
        "IsTruncated":{
          "shape":"IsTruncated",
          "documentation":""
        },
        "NextMarker":{
          "shape":"NextMarker",
        },
        "Contents":{"shape":"Contents"},
      },
    },
    "IdempotentOperationRequest":{
      "type":"structure",
      "required": "token",
      "members":{
        "token":{
          "shape":"Token",
          "idempotencyToken": True,
        },
      }
    },
    "ListObjectsRequest":{
      "type":"structure",
      "required":["Bucket"],
      "members":  OrderedDict([
        ("Bucket", {
          "shape":"BucketName",
          "location":"uri",
          "locationName":"Bucket"
        }),
        ("Marker", {
          "shape":"Marker",
          "location":"querystring",
          "locationName":"marker",
        }),
        ("MaxKeys", {
          "shape":"MaxKeys",
          "location":"querystring",
          "locationName":"max-keys",
        }),
      ]),
    },
    "BucketName":{"type":"string"},
    "MaxKeys":{"type":"integer"},
    "Marker":{"type":"string"},
    "IsTruncated":{"type":"boolean"},
    "NextMarker":{"type":"string"},
    "Contents":{"type":"string"},
    "Token":{"type":"string"},
  }
}


class FakeSession(object):
    def __init__(self, emitter=None):
        self.operation = None
        if emitter is None:
            emitter = HierarchicalEmitter()
        self.emitter = emitter
        self.profile = None
        self.stream_logger_args = None
        self.credentials = 'fakecredentials'
        self.session_vars = {}
        self.config_store = self._register_config_store()
        self.user_agent_name = 'aws-cli'
        self.user_agent_version = '100.100.100'

    def _register_config_store(self):
        chain_builder = ConfigChainFactory(session=self)
        config_store = ConfigValueStore(
            mapping=create_botocore_default_config_mapping(chain_builder)
        )
        return config_store

    def register(self, event_name, handler):
        self.emitter.register(event_name, handler)

    def emit(self, event_name, **kwargs):
        return self.emitter.emit(event_name, **kwargs)

    def emit_first_non_none_response(self, event_name, **kwargs):
        responses = self.emitter.emit(event_name, **kwargs)
        for _, response in responses:
            if response is not None:
                return response

    def get_component(self, name):
        if name == 'event_emitter':
            return self.emitter
        if name == 'config_store':
            return self.config_store

    def create_client(self, *args, **kwargs):
        client = mock.Mock()
        client.list_objects.return_value = {}
        client.can_paginate.return_value = False
        return client

    def get_available_services(self):
        return ['s3']

    def get_data(self, name):
        return GET_DATA[name]

    def get_config_variable(self, name):
        if name in GET_VARIABLE:
            return GET_VARIABLE[name]
        return self.session_vars[name]

    def get_service_model(self, name, api_version=None):
        return botocore.model.ServiceModel(
            MINI_SERVICE, service_name='s3')

    def user_agent(self):
        return 'user_agent'

    def set_stream_logger(self, *args, **kwargs):
        self.stream_logger_args = (args, kwargs)

    def get_credentials(self):
        return self.credentials

    def set_config_variable(self, name, value):
        if name == 'profile':
            self.profile = value
        else:
            self.session_vars[name] = value

    def get_scoped_config(self):
        return GET_VARIABLE.copy()


class FakeCommand(BasicCommand):
    def _run_main(self, args, parsed_globals):
        # We just return success. If this code is reached, it means that
        # all the logic in the __call__ method has sucessfully been run.
        # We subclass it here because the default implementation raises
        # an exception and we don't want that behavior.
        return 0


class FakeCommandVerify(FakeCommand):
    def _run_main(self, args, parsed_globals):
        # Verify passed arguments exist and then return success.
        # This will fail if the expected structure is missing, e.g.
        # if a string is passed in args instead of the expected
        # structure from a custom schema.
        assert args.bar[0]['Name'] == 'test'
        return 0


class TestCliDriver(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()
        self.session.set_config_variable('cli_auto_prompt', 'off')
        self.driver = CLIDriver(session=self.session)

    def test_session_can_be_passed_in(self):
        self.assertEqual(self.driver.session, self.session)

    def test_paginate_rc(self):
        rc = self.driver.main('s3 list-objects --bucket foo'.split())
        self.assertEqual(rc, 0)

    def test_no_profile(self):
        self.driver.main('s3 list-objects --bucket foo'.split())
        self.assertEqual(self.driver.session.profile, None)

    def test_profile(self):
        self.driver.main('s3 list-objects --bucket foo --profile foo'.split())
        self.assertEqual(self.driver.session.profile, 'foo')

    def test_region_is_set_for_session(self):
        driver = CLIDriver(session=self.session)
        driver.main('s3 list-objects --bucket foo --region us-east-2'.split())
        self.assertEqual(
            driver.session.get_config_variable('region'), 'us-east-2')

    @mock.patch('awscli.clidriver.set_stream_logger')
    def test_error_logger(self, set_stream_logger):
        self.driver.main('s3 list-objects --bucket foo --profile foo'.split())
        expected = {'log_level': logging.ERROR, 'logger_name': 'awscli'}
        set_stream_logger.assert_called_with(**expected)

    def test_ctrl_c_is_handled(self):
        fake_client = mock.Mock()
        fake_client.list_objects.side_effect = KeyboardInterrupt
        fake_client.can_paginate.return_value = False
        self.driver.session.create_client = mock.Mock(return_value=fake_client)
        rc = self.driver.main('s3 list-objects --bucket foo'.split())
        self.assertEqual(rc, 130)

    def test_error_unicode(self):
        stderr_b = io.BytesIO()
        stderr = io.TextIOWrapper(stderr_b, encoding="UTF-8")
        fake_client = mock.Mock()
        fake_client.list_objects.side_effect = Exception(u"☃")
        fake_client.can_paginate.return_value = False
        self.driver.session.create_client = mock.Mock(return_value=fake_client)
        with mock.patch("sys.stderr", stderr):
            with mock.patch("locale.getpreferredencoding", lambda: "UTF-8"):
                rc = self.driver.main('s3 list-objects --bucket foo'.split())
        stderr.flush()
        self.assertEqual(rc, 255)
        self.assertEqual(stderr_b.getvalue().strip(), u"☃".encode("UTF-8"))

    def test_can_access_subcommand_table(self):
        table = self.driver.subcommand_table
        self.assertEqual(list(table), self.session.get_available_services())

    def test_can_access_argument_table(self):
        arg_table = self.driver.arg_table
        expected = list(GET_DATA['cli']['options'])
        self.assertEqual(list(arg_table), expected)

    def test_cli_driver_can_keep_log_handlers(self):
        fake_stderr = io.StringIO()
        with contextlib.redirect_stderr(fake_stderr):
            driver = create_clidriver(['--debug'])
            rc = driver.main(['ec2', '--debug'])
        self.assertEqual(rc, 252)
        self.assertEqual(2, fake_stderr.getvalue().count('CLI version:'))

    def test_cli_driver_can_remove_log_handlers(self):
        fake_stderr = io.StringIO()
        with contextlib.redirect_stderr(fake_stderr):
            driver = create_clidriver(['--debug'])
            rc = driver.main(['ec2'])
        self.assertEqual(rc, 252)
        self.assertEqual(1, fake_stderr.getvalue().count('CLI version:'))

    @mock.patch('awscrt.io.init_logging')
    def test_debug_enables_crt_logging(self, mock_init_logging):
        with contextlib.redirect_stderr(io.StringIO()):
            self.driver.main(
                ['s3', 'list-objects', '--bucket', 'foo', '--debug'])
        mock_init_logging.assert_called_with(
            awscrt.io.LogLevel.Debug, 'stderr'
        )

    @mock.patch('awscrt.io.init_logging')
    def test_no_debug_disables_crt_logging(self, mock_init_logging):
        self.driver.main(['s3', 'list-objects', '--bucket', 'foo'])
        mock_init_logging.assert_called_with(
            awscrt.io.LogLevel.NoLogs, 'stderr'
        )


class TestCliDriverHooks(unittest.TestCase):
    # These tests verify the proper hooks are emitted in clidriver.
    def setUp(self):
        self.session = FakeSession()
        self.session.set_config_variable('cli_auto_prompt', 'off')
        self.emitter = mock.Mock()
        self.emitter.emit.return_value = []
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.stdout_patch = mock.patch('sys.stdout', self.stdout)
        #self.stdout_patch.start()
        self.stderr_patch = mock.patch('sys.stderr', self.stderr)
        self.stderr_patch.start()

    def tearDown(self):
        #self.stdout_patch.stop()
        self.stderr_patch.stop()

    def assert_events_fired_in_order(self, events):
        args = self.emitter.emit.call_args_list
        actual_events = [arg[0][0] for arg in args]
        self.assertEqual(actual_events, events)

    def serialize_param(self, param, value, **kwargs):
        if kwargs['cli_argument'].name == 'bucket':
            return value + '-altered!'

    def test_expected_events_are_emitted_in_order(self):
        self.emitter.emit.return_value = []
        self.session.emitter = self.emitter
        driver = CLIDriver(session=self.session)
        driver.main('s3 list-objects --bucket foo'.split())
        self.assert_events_fired_in_order([
            # Events fired while parser is being created.
            'building-command-table.main',
            'building-top-level-params',
            'top-level-args-parsed',
            'session-initialized',
            'building-command-table.s3',
            'building-argument-table.s3.list-objects',
            'before-building-argument-table-parser.s3.list-objects',
            'building-command-table.s3_list-objects',
            'operation-args-parsed.s3.list-objects',
            'load-cli-arg.s3.list-objects.bucket',
            'process-cli-arg.s3.list-objects',
            'load-cli-arg.s3.list-objects.marker',
            'load-cli-arg.s3.list-objects.max-keys',
            'calling-command.s3.list-objects'
        ])

    def test_create_help_command(self):
        # When we generate the HTML docs, we don't actually run
        # commands, we just call the create_help_command methods.
        # We want to make sure that in this case, the corresponding
        # building-command-table events are fired.
        # The test above will prove that is true when running a command.
        # This test proves it is true when generating the HTML docs.
        self.emitter.emit.return_value = []
        self.session.emitter = self.emitter
        driver = CLIDriver(session=self.session)
        main_hc = driver.create_help_command()
        command = main_hc.command_table['s3']
        command.create_help_command()
        self.assert_events_fired_in_order([
            # Events fired while parser is being created.
            'building-command-table.main',
            'building-top-level-params',
            'building-command-table.s3',
        ])

    def test_unknown_command_suggests_help(self):
        driver = CLIDriver(
            session=self.session,
            error_handler=construct_cli_error_handlers_chain()
        )

        # Note the typo in 'list-objects'
        rc = driver.main(
            's3 list-objecst --bucket foo --unknown-arg foo'.split()
        )
        self.assertEqual(rc, 252)
        # Tell the user what went wrong.
        self.assertIn("Invalid choice: 'list-objecst'", self.stderr.getvalue())
        # Offer the user a suggestion.
        self.assertIn("maybe you meant:\n\n  * list-objects", self.stderr.getvalue())


class TestSearchPath(unittest.TestCase):
    @mock.patch('os.pathsep', ';')
    @mock.patch('os.environ', {'AWS_DATA_PATH': 'c:\\foo;c:\\bar'})
    def test_windows_style_search_path(self):
        driver = CLIDriver()
        # Our two overrides should be the last two elements in the search path.
        search_paths = driver.session.get_component(
            'data_loader').search_paths
        self.assertIn('c:\\foo', search_paths)
        self.assertIn('c:\\bar', search_paths)


class TestAWSCommand(BaseAWSCommandParamsTest):
    # These tests will simulate running actual aws commands
    # but with the http part mocked out.
    def setUp(self):
        super(TestAWSCommand, self).setUp()
        self.stderr = StringIO()
        self.stderr_patch = mock.patch('sys.stderr', self.stderr)
        self.stderr_patch.start()

    def tearDown(self):
        super(TestAWSCommand, self).tearDown()
        self.stderr_patch.stop()

    def inject_new_param(self, argument_table, **kwargs):
        argument = CustomArgument('unknown-arg', {})
        argument.add_to_arg_table(argument_table)

    def inject_command(self, command_table, session, **kwargs):
        command = FakeCommand(session)
        command.NAME = 'foo'
        command.ARG_TABLE = [
            {'name': 'bar', 'action': 'store'}
        ]
        command_table['foo'] = command

    def inject_command_schema(self, command_table, session, **kwargs):
        command = FakeCommandVerify(session)
        command.NAME = 'foo'

        # Build a schema using all the types we are interested in
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "Name": {
                        "type": "string",
                        "required": True
                    },
                    "Count": {
                        "type": "integer"
                    }
                }
            }
        }

        command.ARG_TABLE = [
            {'name': 'bar', 'schema': schema}
        ]

        command_table['foo'] = command

    def test_event_emission_for_top_level_params(self):
        driver = create_clidriver()
        # --unknown-foo is an unknown arg, so we expect a 252 rc.
        rc = driver.main('ec2 describe-instances --unknown-arg foo'.split())
        self.assertEqual(rc, 252)
        self.assertIn('Unknown options: --unknown-arg', self.stderr.getvalue())

        # The argument table is memoized in the CLIDriver object. So
        # when we call main() above, it will get created and cached
        # and the argument table won't get created again (and therefore
        # the building-top-level-params event will not get generated again).
        # So, for this test we need to create a new driver object.
        driver = create_clidriver()
        driver.session.register(
            'building-top-level-params', self.inject_new_param)
        driver.session.register(
            'top-level-args-parsed',
            lambda parsed_args, **kwargs: args_seen.append(parsed_args))

        args_seen = []

        # Now we should get an rc of 0 as the arg is expected
        # (though nothing actually does anything with the arg).
        self.patch_make_request()
        rc = driver.main('ec2 describe-instances --unknown-arg foo'.split())
        self.assertEqual(rc, 0)
        self.assertEqual(len(args_seen), 1)
        self.assertEqual(args_seen[0].unknown_arg, 'foo')

    @mock.patch('awscli.paramfile.URIArgumentHandler',
                spec=URIArgumentHandler)
    def test_custom_arg_paramfile(self, mock_handler):
        mock_paramfile = mock.Mock(autospec=True)
        mock_paramfile.return_value = None
        mock_handler.return_value = mock_paramfile

        driver = create_clidriver()
        driver.session.register(
            'building-argument-table', self.inject_new_param)

        self.patch_make_request()
        rc = driver.main(
            'ec2 describe-instances --unknown-arg file:///foo'.split())

        self.assertEqual(rc, 0)

        # Make sure uri_param was called
        mock_paramfile.assert_any_call(
            event_name='load-cli-arg.ec2.describe-instances.unknown-arg',
            operation_name='describe-instances',
            param=mock.ANY,
            service_name='ec2',
            value='file:///foo',
        )
        # Make sure it was called with our passed-in URI
        self.assertEqual(
            'file:///foo',
            mock_paramfile.call_args_list[-1][1]['value'])

    @mock.patch('awscli.paramfile.URIArgumentHandler',
                spec=URIArgumentHandler)
    def test_custom_command_paramfile(self, mock_handler):
        mock_paramfile = mock.Mock(autospec=True)
        mock_paramfile.return_value = None
        mock_handler.return_value = mock_paramfile

        driver = create_clidriver()
        driver.session.register(
            'building-command-table', self.inject_command)

        self.patch_make_request()
        rc = driver.main(
            'ec2 foo --bar file:///foo'.split())

        self.assertEqual(rc, 0)

        mock_paramfile.assert_any_call(
            event_name='load-cli-arg.custom.foo.bar',
            operation_name='foo',
            param=mock.ANY,
            service_name='custom',
            value='file:///foo',
        )

    def test_custom_command_schema(self):
        driver = create_clidriver()
        driver.session.register(
            'building-command-table', self.inject_command_schema)

        self.patch_make_request()

        # Test single shorthand item
        rc = driver.main(
            'ec2 foo --bar Name=test,Count=4'.split())

        self.assertEqual(rc, 0)

        # Test shorthand list of items with optional values
        rc = driver.main(
            'ec2 foo --bar Name=test,Count=4 Name=another'.split())

        self.assertEqual(rc, 0)

        # Test missing require shorthand item
        rc = driver.main(
            'ec2 foo --bar Count=4'.split())

        self.assertEqual(rc, 252)

        # Test extra unknown shorthand item
        rc = driver.main(
            'ec2 foo --bar Name=test,Unknown='.split())

        self.assertEqual(rc, 252)

        # Test long form JSON
        rc = driver.main(
            'ec2 foo --bar {"Name":"test","Count":4}'.split())

        self.assertEqual(rc, 0)

        # Test malformed long form JSON
        rc = driver.main(
            'ec2 foo --bar {"Name":"test",Count:4}'.split())

        self.assertEqual(rc, 252)

    def test_empty_params_gracefully_handled(self):
        # Simulates the equivalent in bash: --identifies ""
        cmd = 'ses get-identity-dkim-attributes --identities'.split()
        cmd.append('')
        self.assert_params_for_cmd(cmd,expected_rc=0)

    def test_file_param_does_not_exist(self):
        driver = create_clidriver()
        rc = driver.main('ec2 describe-instances '
                         '--filters file://does/not/exist.json'.split())
        self.assertEqual(rc, 252)
        error_msg = self.stderr.getvalue()
        self.assertIn("Error parsing parameter '--filters': "
                      "Unable to load paramfile file://does/not/exist.json",
                      error_msg)
        self.assertIn("No such file or directory", error_msg)

    def test_aws_configure_in_error_message_no_credentials(self):
        driver = create_clidriver()
        def raise_exception(*args, **kwargs):
            raise NoCredentialsError()
        driver.session.register(
            'building-command-table',
            lambda command_table, **kwargs: \
                command_table.__setitem__('ec2', raise_exception))
        with mock.patch('sys.stderr') as f:
            driver.main('ec2 describe-instances'.split())
        self.assertEqual(
            f.write.call_args_list[1][0][0],
            'Unable to locate credentials. '
            'You can configure credentials by running "aws configure".')

    def test_override_calling_command(self):
        self.driver = create_clidriver()

        # Make a function that will return an override such that its value
        # is used over whatever is returned by the invoker which is usually
        # zero.
        def override_with_rc(**kwargs):
            return 20

        self.driver.session.register('calling-command', override_with_rc)
        rc = self.driver.main('ec2 describe-instances'.split())
        # Check that the overriden rc is as expected.
        self.assertEqual(rc, 20)

    def test_override_calling_command_error(self):
        self.driver = create_clidriver()

        # Make a function that will return an error. The handler will cause
        # an error to be returned and later raised.
        def override_with_error(**kwargs):
            return ValueError()

        self.driver.session.register('calling-command', override_with_error)
        # An exception should be thrown as a result of the handler, which
        # will result in 255 rc.
        rc = self.driver.main('ec2 describe-instances'.split())
        self.assertEqual(rc, 255)

    def test_help_blurb_in_error_message(self):
        rc = self.driver.main([])
        self.assertEqual(rc, 252)
        self.assertIn(HELP_BLURB, self.stderr.getvalue())

    def test_help_blurb_in_service_error_message(self):
        rc = self.driver.main(['ec2'])
        self.assertEqual(rc, 252)
        self.assertIn(HELP_BLURB, self.stderr.getvalue())

    def test_help_blurb_in_operation_error_message(self):
        rc = self.driver.main(['s3api', 'list-objects'])
        self.assertEqual(rc, 252)
        self.assertIn(HELP_BLURB, self.stderr.getvalue())

    def test_help_blurb_in_unknown_argument_error_message(self):
        args = ['s3api', 'list-objects', '--help']
        driver = create_clidriver(args)
        rc = driver.main(args)
        self.assertEqual(rc, 252)
        self.assertIn(HELP_BLURB, self.stderr.getvalue())

    def test_idempotency_token_is_not_required_in_help_text(self):
        rc = self.driver.main(['servicecatalog', 'create-constraint'])
        self.assertEqual(rc, 252)
        self.assertNotIn('--idempotency-token', self.stderr.getvalue())

    @mock.patch('awscli.clidriver.platform.system', return_value='Linux')
    @mock.patch('awscli.clidriver.platform.machine', return_value='x86_64')
    @mock.patch('awscli.clidriver.distro.id', return_value='amzn')
    @mock.patch('awscli.clidriver.distro.major_version', return_value='1')
    def test_user_agent_for_linux(self, *args):
        driver = create_clidriver()
        expected_user_agent = 'md/installer#source md/distrib#amzn.1'
        self.assertEqual(expected_user_agent,
                         driver.session.user_agent_extra)

    def test_user_agent(self, *args):
        driver = create_clidriver()
        user_agent_extra_pattern = re.compile(
            r'^md/installer#source'
        )
        self.assertIsNotNone(
            user_agent_extra_pattern.match(driver.session.user_agent_extra)
        )
        # check that distro didn't fail
        self.assertFalse('unknown' in driver.session.user_agent_extra)

    @mock.patch('awscli.clidriver.platform.system', return_value='Linux')
    @mock.patch('awscli.clidriver.distro.id', side_effect=Exception())
    def test_user_agent_handles_distro_exception(self, *args):
        driver = create_clidriver()
        self.assertTrue('unknown' in driver.session.user_agent_extra)


class TestHowClientIsCreated(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestHowClientIsCreated, self).setUp()
        self.endpoint_creator_patch = mock.patch(
            'botocore.args.EndpointCreator')
        self.endpoint_creator = self.endpoint_creator_patch.start()
        self.create_endpoint = \
                self.endpoint_creator.return_value.create_endpoint
        self.endpoint = self.create_endpoint.return_value
        self.endpoint.host = 'https://example.com'
        # Have the endpoint give a dummy empty response.
        http_response = AWSResponse(None, 200, {}, None)
        self.endpoint.make_request.return_value = (
            http_response, {})

    def tearDown(self):
        super(TestHowClientIsCreated, self).tearDown()
        self.endpoint_creator_patch.stop()

    def test_aws_with_endpoint_url(self):
        self.assert_params_for_cmd(
            'ec2 describe-instances --endpoint-url https://foobar.com/',
            expected_rc=0)
        self.assertEqual(self.create_endpoint.call_args[1]['endpoint_url'],
                         'https://foobar.com/')

    def test_aws_with_region(self):
        self.assert_params_for_cmd(
            'ec2 describe-instances --region us-west-2',
            expected_rc=0)
        self.assertEqual(
            self.create_endpoint.call_args[1]['region_name'], 'us-west-2')

    def test_can_use_new_aws_region_env_var(self):
        self.environ['AWS_REGION'] = 'us-east-2'
        self.environ['AWS_DEFAULT_REGION'] = 'us-west-1'
        self.assert_params_for_cmd(
            'ec2 describe-instances',
            expected_rc=0)
        self.assertEqual(
            self.create_endpoint.call_args[1]['region_name'], 'us-east-2')

    def test_aws_with_verify_false(self):
        self.assert_params_for_cmd(
            'ec2 describe-instances --region us-east-1 --no-verify-ssl',
            expected_rc=0)
        # Because we used --no-verify-ssl, create_endpoint should be
        # called with verify=False
        call_args = self.create_endpoint.call_args
        self.assertFalse(call_args[1]['verify'])

    def test_aws_with_cacert_env_var(self):
        self.environ['AWS_CA_BUNDLE'] = '/path/cacert.pem'
        self.assert_params_for_cmd(
            'ec2 describe-instances --region us-east-1',
            expected_rc=0)
        call_args = self.create_endpoint.call_args
        self.assertEqual(call_args[1]['verify'], '/path/cacert.pem')

    def test_aws_with_read_timeout(self):
        self.assert_params_for_cmd(
            'lambda invoke --function-name foo out.log --cli-read-timeout 90',
            expected_rc=0)
        call_args = self.create_endpoint.call_args
        self.assertEqual(call_args[1]['timeout'][1], 90)

    def test_aws_with_blocking_read_timeout(self):
        self.assert_params_for_cmd(
            'lambda invoke --function-name foo out.log --cli-read-timeout 0',
            expected_rc=0)
        call_args = self.create_endpoint.call_args
        self.assertEqual(call_args[1]['timeout'][1], None)

    def test_aws_with_connnect_timeout(self):
        self.assert_params_for_cmd(
            'lambda invoke --function-name foo out.log '
            '--cli-connect-timeout 90',
            expected_rc=0)
        call_args = self.create_endpoint.call_args
        self.assertEqual(call_args[1]['timeout'][0], 90)

    def test_aws_with_blocking_connect_timeout(self):
        self.assert_params_for_cmd(
            'lambda invoke --function-name foo out.log '
            '--cli-connect-timeout 0',
            expected_rc=0)
        call_args = self.create_endpoint.call_args
        self.assertEqual(call_args[1]['timeout'][0], None)

    def test_aws_with_read_and_connnect_timeout(self):
        self.assert_params_for_cmd(
            'lambda invoke --function-name foo out.log '
            '--cli-read-timeout 70 --cli-connect-timeout 90',
            expected_rc=0)
        call_args = self.create_endpoint.call_args
        self.assertEqual(call_args[1]['timeout'], (90, 70))


class TestVerifyArgument(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestVerifyArgument, self).setUp()
        self.driver.session.register('top-level-args-parsed', self.record_args)
        self.recorded_args = None

    def record_args(self, parsed_args, **kwargs):
        self.recorded_args = parsed_args

    def test_no_verify_argument(self):
        self.assert_params_for_cmd('s3api list-buckets --no-verify-ssl'.split())
        self.assertFalse(self.recorded_args.verify_ssl)

    def test_verify_argument_is_none_by_default(self):
        self.assert_params_for_cmd('s3api list-buckets'.split())
        self.assertIsNone(self.recorded_args.verify_ssl)


class TestFormatter(BaseAWSCommandParamsTest):
    def test_bad_output(self):
        with self.assertRaises(ValueError):
            formatter.get_formatter('bad-type', None)


class TestCLICommand(unittest.TestCase):
    def setUp(self):
        self.cmd = CLICommand()

    def test_name(self):
        with self.assertRaises(NotImplementedError):
            self.cmd.name
        with self.assertRaises(NotImplementedError):
            self.cmd.name = 'foo'

    def test_lineage(self):
        self.assertEqual(self.cmd.lineage, [self.cmd])

    def test_lineage_names(self):
        with self.assertRaises(NotImplementedError):
            self.cmd.lineage_names

    def test_arg_table(self):
        self.assertEqual(self.cmd.arg_table, {})


class TestServiceCommand(unittest.TestCase):
    def setUp(self):
        self.name = 'foo'
        self.session = FakeSession()
        self.cmd = ServiceCommand(self.name, self.session)

    def test_can_access_subcommand_table(self):
        table = self.cmd.subcommand_table
        expected = [
            xform_name(op, '-') for op in
            self.session.get_service_model(self.name).operation_names
        ]
        self.assertEqual(set(table), set(expected))

    def test_can_access_arg_table(self):
        self.assertEqual(self.cmd.arg_table, {})

    def test_name(self):
        self.assertEqual(self.cmd.name, self.name)
        self.cmd.name = 'bar'
        self.assertEqual(self.cmd.name, 'bar')

    def test_lineage(self):
        cmd = CLICommand()
        self.assertEqual(self.cmd.lineage, [self.cmd])
        self.cmd.lineage = [cmd]
        self.assertEqual(self.cmd.lineage, [cmd])

    def test_lineage_names(self):
        self.assertEqual(self.cmd.lineage_names, ['foo'])

    def test_pass_lineage_to_child(self):
        # In order to introspect the service command's subcommands
        # we introspect the subcommand via the help command since
        # a service command's command table is not public.
        help_command = self.cmd.create_help_command()
        child_cmd = help_command.command_table['list-objects']
        self.assertEqual(child_cmd.lineage,
                         [self.cmd, child_cmd])
        self.assertEqual(child_cmd.lineage_names, ['foo', 'list-objects'])

    def test_help_event_class(self):
        # Ensures it sends the right event name to the help command
        help_command = self.cmd.create_help_command()
        self.assertEqual(help_command.event_class, 'foo')
        child_cmd = help_command.command_table['list-objects']
        # Check the ``ServiceOperation`` class help command as well
        child_help_cmd = child_cmd.create_help_command()
        self.assertEqual(child_help_cmd.event_class, 'foo.list-objects')


class TestServiceOperation(unittest.TestCase):
    def setUp(self):
        self.name = 'list-objects'
        self.session = FakeSession()
        operation = self.session.get_service_model(
            's3').operation_model('ListObjects')
        self.mock_operation = operation
        self.cmd = ServiceOperation(self.name, None, None, operation,
                                    self.session)

    def test_can_access_subcommand_table(self):
        self.assertEqual(self.cmd.subcommand_table, {})

    def test_can_access_arg_table(self):
        self.assertEqual(set(self.cmd.arg_table),
                         set(['bucket', 'marker', 'max-keys']))

    def test_name(self):
        self.assertEqual(self.cmd.name, self.name)
        self.cmd.name = 'bar'
        self.assertEqual(self.cmd.name, 'bar')

    def test_lineage(self):
        cmd = CLICommand()
        self.assertEqual(self.cmd.lineage, [self.cmd])
        self.cmd.lineage = [cmd]
        self.assertEqual(self.cmd.lineage, [cmd])

    def test_lineage_names(self):
        self.assertEqual(self.cmd.lineage_names, ['list-objects'])

    def test_deprecated_operation(self):
        self.mock_operation.deprecated = True
        cmd = ServiceOperation(self.name, None, None, self.mock_operation,
                               None)
        self.assertTrue(getattr(cmd, '_UNDOCUMENTED'))

    def test_idempotency_token_is_not_required(self):
        session = FakeSession()
        name = 'IdempotentOperation'
        service_model = session.get_service_model('s3')
        operation_model = service_model.operation_model(name)
        cmd = ServiceOperation(name, None, None, operation_model, session)
        arg_table = cmd.arg_table
        token_argument = arg_table.get('token')
        self.assertFalse(token_argument.required,
                         'Idempotency tokens should not be required')


class TestAWSCLIEntryPoint(unittest.TestCase):

    def setUp(self):
        self.driver = mock.Mock()

        def _create_fake_cli_driver(*args):
            self.driver.session.user_agent_extra = ''
            return self.driver

        self.prompt_patch = mock.patch('awscli.clidriver.AutoPromptDriver')
        self.crete_driver_patch = mock.patch(
            'awscli.clidriver.create_clidriver')
        prompt_driver_class = self.prompt_patch.start()
        self.create_clidriver = self.crete_driver_patch.start()
        self.create_clidriver.side_effect = _create_fake_cli_driver
        self.prompt_driver = mock.Mock()
        prompt_driver_class.return_value = self.prompt_driver

    def tearDown(self):
        self.prompt_patch.stop()
        self.crete_driver_patch.stop()

    def test_recreate_driver_in_partial_mode_on_param_err(self):
        self.prompt_driver.resolve_mode.return_value = 'on-partial'
        self.driver.main.return_value = 252
        entry_point = awscli.clidriver.AWSCLIEntryPoint()
        rc = entry_point.main([])
        self.assertEqual(self.create_clidriver.call_count, 2)
        self.assertEqual(rc, 252)

    def test_not_recreate_driver_in_partial_mode_on_success(self):
        self.prompt_driver.resolve_mode.return_value = 'on-partial'
        self.driver.main.return_value = 0
        entry_point = awscli.clidriver.AWSCLIEntryPoint()
        rc = entry_point.main([])
        self.assertEqual(self.create_clidriver.call_count, 1)
        self.assertEqual(rc, 0)

    def test_not_recreate_driver_in_on_mode(self):
        self.prompt_driver.resolve_mode.return_value = 'on'
        self.driver.main.return_value = 252
        entry_point = awscli.clidriver.AWSCLIEntryPoint()
        rc = entry_point.main([])
        self.assertEqual(self.create_clidriver.call_count, 1)
        self.assertEqual(rc, 252)

    def test_not_recreate_driver_in_off_mode(self):
        self.prompt_driver.resolve_mode.return_value = 'off'
        self.driver.main.return_value = 252
        entry_point = awscli.clidriver.AWSCLIEntryPoint()
        rc = entry_point.main([])
        self.assertEqual(self.create_clidriver.call_count, 1)
        self.assertEqual(rc, 252)

    def test_handle_exception_in_main(self):
        self.prompt_driver.resolve_mode.return_value = 'on'
        self.prompt_driver.prompt_for_args.side_effect = Exception('error')
        entry_point = awscli.clidriver.AWSCLIEntryPoint()
        fake_stderr = io.StringIO()
        with contextlib.redirect_stderr(fake_stderr):
            rc = entry_point.main([])
        self.assertEqual(rc, 255)
        self.assertIn('error', fake_stderr.getvalue())

    def test_update_user_agent_in_on_mode(self):
        self.prompt_driver.resolve_mode.return_value = 'on'
        self.driver.main.return_value = 252
        entry_point = awscli.clidriver.AWSCLIEntryPoint()
        entry_point.main([])
        self.assertEqual(self.driver.session.user_agent_extra, 'md/prompt#on')

    def test_not_update_user_agent_in_off_mode(self):
        self.prompt_driver.resolve_mode.return_value = 'off'
        self.driver.main.return_value = 252
        entry_point = awscli.clidriver.AWSCLIEntryPoint()
        entry_point.main([])
        self.assertEqual(self.driver.session.user_agent_extra, 'md/prompt#off')

    def test_update_user_agent_in_partial_mode_on_param_err(self):
        self.prompt_driver.resolve_mode.return_value = 'on-partial'
        self.driver.main.return_value = 252
        entry_point = awscli.clidriver.AWSCLIEntryPoint()
        entry_point.main([])
        self.assertEqual(self.driver.session.user_agent_extra,
                         'md/prompt#partial')

    def test_not_update_user_agent_in_partial_mode_on_success(self):
        self.prompt_driver.resolve_mode.return_value = 'on-partial'
        self.driver.main.return_value = 0
        entry_point = awscli.clidriver.AWSCLIEntryPoint()
        entry_point.main([])
        self.assertEqual(self.driver.session.user_agent_extra, 'md/prompt#off')


class TextCreateCLIDriver(unittest.TestCase):
    def test_create_cli_driver_parse_args(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            driver = create_clidriver(['--debug'])
        self.assertIn('CLI version', stderr.getvalue())

    def test_create_cli_driver_wo_args(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            driver = create_clidriver()
        self.assertIn('', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
