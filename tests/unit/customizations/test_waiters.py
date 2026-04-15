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
from botocore.exceptions import DataNotFoundError
from botocore.waiter import WaiterModel

from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.waiters import (
    WaitCommand,
    WaiterArgument,
    WaiterCaller,
    WaiterStateCommand,
    WaiterStateCommandBuilder,
    WaiterStateDocBuilder,
    add_waiters,
    get_waiter_model_from_service_model,
)
from awscli.testutils import (
    BaseAWSCommandParamsTest,
    BaseAWSHelpOutputTest,
    mock,
    unittest,
)


class TestAddWaiters(unittest.TestCase):
    def setUp(self):
        self.service_model = mock.Mock()
        self.session = mock.Mock()

        self.command_object = mock.Mock()
        self.command_object.service_model = self.service_model

        # Set up the mock session.
        self.session.get_waiter_model.return_value = WaiterModel(
            {
                'version': 2,
                'waiters': {
                    'FooExists': {},
                },
            }
        )

    def test_add_waiters(self):
        command_table = {}
        add_waiters(command_table, self.session, self.command_object)
        # Make sure a wait command was added.
        self.assertIn('wait', command_table)
        self.assertIsInstance(command_table['wait'], WaitCommand)

    def test_add_waiters_no_waiter_names(self):
        self.session.get_waiter_model.return_value = WaiterModel(
            {
                'version': 2,
                # No waiters are specified.
                'waiters': {},
            }
        )
        command_table = {}
        add_waiters(command_table, self.session, self.command_object)
        # Make sure that no wait command was added since the service object
        # has no waiters.
        self.assertEqual(command_table, {})

    def test_add_waiters_no_service_object(self):
        command_table = {}
        self.command_object.service_model = None
        add_waiters(command_table, self.session, self.command_object)
        # Make sure that no wait command was added since no service object
        # was passed in.
        self.assertEqual(command_table, {})

    def test_add_waiter_no_waiter_config(self):
        self.session.get_waiter_model.side_effect = DataNotFoundError(
            data_path='foo'
        )
        command_table = {}
        add_waiters(command_table, self.session, self.command_object)
        self.assertEqual(command_table, {})


class TestServicetoWaiterModel(unittest.TestCase):
    def test_service_object_to_waiter_model(self):
        service_model = mock.Mock()
        session = mock.Mock()
        service_model.service_name = 'service'
        service_model.api_version = '2014-01-01'
        get_waiter_model_from_service_model(session, service_model)
        session.get_waiter_model.assert_called_with('service')

    def test_can_handle_data_errors(self):
        service_model = mock.Mock()
        session = mock.Mock()
        service_model.service_name = 'service'
        service_model.api_version = '2014-01-01'
        session.get_waiter_model.side_effect = DataNotFoundError(
            data_path='foo'
        )
        self.assertIsNone(
            get_waiter_model_from_service_model(session, service_model)
        )


class TestWaitCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.model = WaiterModel(
            {
                'version': 2,
                'waiters': {
                    'Foo': {
                        'operation': 'foo',
                        'maxAttempts': 1,
                        'delay': 1,
                        'acceptors': [],
                    }
                },
            }
        )
        self.service_model = mock.Mock()
        self.cmd = WaitCommand(self.session, self.model, self.service_model)

    def test_passes_on_lineage(self):
        child_cmd = self.cmd.subcommand_table['foo']
        self.assertEqual(len(child_cmd.lineage), 2)
        self.assertEqual(child_cmd.lineage[0], self.cmd)
        self.assertIsInstance(child_cmd.lineage[1], WaiterStateCommand)

    def test_run_main_error(self):
        self.parsed_args = mock.Mock()
        self.parsed_args.subcommand = None
        with self.assertRaises(ParamValidationError):
            self.cmd._run_main(self.parsed_args, None)


class TestWaitHelpOutput(BaseAWSHelpOutputTest):
    def test_wait_command_is_in_list(self):
        self.driver.main(['ec2', 'help'])
        self.assert_contains('* wait')

    def test_wait_help_command(self):
        self.driver.main(['ec2', 'wait', 'help'])
        self.assert_contains('.. _cli:aws ec2 wait:')
        self.assert_contains('Wait until a particular condition is satisfied.')
        self.assert_contains('* instance-running')
        self.assert_contains('* vpc-available')

    def test_wait_state_help_command(self):
        self.driver.main(['ec2', 'wait', 'instance-running', 'help'])
        self.assert_contains('.. _cli:aws ec2 wait instance-running:')
        self.assert_contains(
            'Wait until JMESPath query Reservations[].Instances[].State.Name'
        )
        self.assert_contains('poll every')
        self.assert_contains('This will exit with a return code of 255 after')
        self.assert_contains('``describe-instances``')
        self.assert_contains('[--filters <value>]')
        self.assert_contains('``--filters`` (list)')
        self.assert_contains('======\nOutput\n======\n\nNone')

    def test_wait_state_help_shows_waiter_params(self):
        self.driver.main(['ec2', 'wait', 'instance-running', 'help'])
        self.assert_contains('[--delay <value>]')
        self.assert_contains('[--max-attempts <value>]')
        self.assert_contains('``--delay``')
        self.assert_contains('``--max-attempts``')


class TestWait(BaseAWSCommandParamsTest):
    """This is merely a smoke test.

    Its purpose is to test that the wait command can be run properly for
    various services. It is by no means exhaustive.
    """

    def test_ec2_instance_running(self):
        cmdline = 'ec2 wait instance-running'
        cmdline += ' --instance-ids i-12345678 i-87654321'
        cmdline += """ --filters {"Name":"group-name","Values":["foobar"]}"""
        result = {
            'Filters': [{'Name': 'group-name', 'Values': ['foobar']}],
            'InstanceIds': ['i-12345678', 'i-87654321'],
        }
        self.parsed_response = {
            'Reservations': [{'Instances': [{'State': {'Name': 'running'}}]}]
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_dynamodb_table_exists(self):
        cmdline = 'dynamodb wait table-exists'
        cmdline += ' --table-name mytable'
        result = {"TableName": "mytable"}
        self.parsed_response = {'Table': {'TableStatus': 'ACTIVE'}}
        self.assert_params_for_cmd(cmdline, result)

    def test_rds_jobs_complete(self):
        cmdline = 'rds wait db-instance-available'
        cmdline += ' --db-instance-identifier abc'
        result = {'DBInstanceIdentifier': 'abc'}
        self.parsed_response = {
            'DBInstances': [{'DBInstanceStatus': 'available'}]
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_ec2_wait_with_delay_and_max_attempts(self):
        cmdline = 'ec2 wait instance-running'
        cmdline += ' --instance-ids i-12345678'
        cmdline += ' --delay 10 --max-attempts 100'
        # WaiterConfig is popped by botocore's Waiter.wait() before
        # the API call, so only API params appear in last_kwargs.
        result = {'InstanceIds': ['i-12345678']}
        self.parsed_response = {
            'Reservations': [{'Instances': [{'State': {'Name': 'running'}}]}]
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_ec2_wait_forwards_waiter_config_end_to_end(self):
        # End-to-end check: --delay and --max-attempts must flow from the
        # command line all the way into waiter.wait() as WaiterConfig,
        # alongside the regular API parameters.
        with mock.patch(
            'botocore.client.BaseClient.get_waiter'
        ) as mock_get_waiter:
            mock_waiter = mock.Mock()
            mock_get_waiter.return_value = mock_waiter
            cmdline = (
                'ec2 wait instance-running '
                '--instance-ids i-12345678 '
                '--delay 10 --max-attempts 100'
            )
            self.run_cmd(cmdline, expected_rc=0)
            mock_get_waiter.assert_called_with('instance_running')
            mock_waiter.wait.assert_called_once_with(
                InstanceIds=['i-12345678'],
                WaiterConfig={'Delay': 10, 'MaxAttempts': 100},
            )

    def test_ec2_wait_without_waiter_flags_omits_waiter_config(self):
        # When neither --delay nor --max-attempts are supplied, no
        # WaiterConfig kwarg should be passed to waiter.wait().
        with mock.patch(
            'botocore.client.BaseClient.get_waiter'
        ) as mock_get_waiter:
            mock_waiter = mock.Mock()
            mock_get_waiter.return_value = mock_waiter
            cmdline = 'ec2 wait instance-running --instance-ids i-12345678'
            self.run_cmd(cmdline, expected_rc=0)
            mock_waiter.wait.assert_called_once_with(
                InstanceIds=['i-12345678']
            )


class TestWaiterStateCommandBuilder(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.service_model = mock.Mock()

        # Create some waiters.
        self.model = WaiterModel(
            {
                'version': 2,
                'waiters': {
                    'InstanceRunning': {
                        'description': 'My waiter description.',
                        'delay': 1,
                        'maxAttempts': 10,
                        'operation': 'MyOperation',
                    },
                    'BucketExists': {
                        'description': 'My waiter description.',
                        'operation': 'MyOperation',
                        'delay': 1,
                        'maxAttempts': 10,
                    },
                },
            }
        )

        self.waiter_builder = WaiterStateCommandBuilder(
            self.session, self.model, self.service_model
        )

    def test_build_waiter_state_cmds(self):
        subcommand_table = {}
        self.waiter_builder.build_all_waiter_state_cmds(subcommand_table)
        # Check the commands are in the command table
        self.assertEqual(len(subcommand_table), 2)
        self.assertIn('instance-running', subcommand_table)
        self.assertIn('bucket-exists', subcommand_table)

        # Make sure that the correct operation object was used.
        self.service_model.operation_model.assert_called_with('MyOperation')

        # Introspect the commands in the command table
        instance_running_cmd = subcommand_table['instance-running']
        bucket_exists_cmd = subcommand_table['bucket-exists']

        # Check that the instance type is correct.
        self.assertIsInstance(instance_running_cmd, WaiterStateCommand)
        self.assertIsInstance(bucket_exists_cmd, WaiterStateCommand)

        # Check the descriptions are set correctly.
        self.assertEqual(
            instance_running_cmd.DESCRIPTION,
            'My waiter description. It will poll every 1 seconds until '
            'a successful state has been reached. This will exit with a '
            'return code of 255 after 10 failed checks. You can override '
            'the default polling behavior with ``--delay`` and '
            '``--max-attempts``.',
        )
        self.assertEqual(
            bucket_exists_cmd.DESCRIPTION,
            'My waiter description. It will poll every 1 seconds until '
            'a successful state has been reached. This will exit with a '
            'return code of 255 after 10 failed checks. You can override '
            'the default polling behavior with ``--delay`` and '
            '``--max-attempts``.',
        )


class TestWaiterStateDocBuilder(unittest.TestCase):
    def setUp(self):
        self.waiter_config = mock.Mock()
        self.waiter_config.description = ''
        self.waiter_config.operation = 'MyOperation'
        self.waiter_config.delay = 5
        self.waiter_config.max_attempts = 20

        # Set up the acceptors.
        self.success_acceptor = mock.Mock()
        self.success_acceptor.state = 'success'
        self.fail_acceptor = mock.Mock()
        self.fail_acceptor.state = 'failure'
        self.error_acceptor = mock.Mock()
        self.error_acceptor.state = 'error'
        self.waiter_config.acceptors = [
            self.fail_acceptor,
            self.success_acceptor,
            self.error_acceptor,
        ]

        self.doc_builder = WaiterStateDocBuilder(self.waiter_config)

    def test_config_provided_description(self):
        # Description is provided by the config file
        self.waiter_config.description = 'My description.'
        description = self.doc_builder.build_waiter_state_description()
        self.assertEqual(
            description,
            'My description. It will poll every 5 seconds until a '
            'successful state has been reached. This will exit with a '
            'return code of 255 after 20 failed checks. You can override '
            'the default polling behavior with ``--delay`` and '
            '``--max-attempts``.',
        )

    def test_error_acceptor(self):
        self.success_acceptor.matcher = 'error'
        self.success_acceptor.expected = 'MyException'
        description = self.doc_builder.build_waiter_state_description()
        self.assertEqual(
            description,
            'Wait until MyException is thrown when polling with '
            '``my-operation``. It will poll every 5 seconds until a '
            'successful state has been reached. This will exit with a '
            'return code of 255 after 20 failed checks. You can override '
            'the default polling behavior with ``--delay`` and '
            '``--max-attempts``.',
        )

    def test_status_acceptor(self):
        self.success_acceptor.matcher = 'status'
        self.success_acceptor.expected = 200
        description = self.doc_builder.build_waiter_state_description()
        self.assertEqual(
            description,
            'Wait until 200 response is received when polling with '
            '``my-operation``. It will poll every 5 seconds until a '
            'successful state has been reached. This will exit with a '
            'return code of 255 after 20 failed checks. You can override '
            'the default polling behavior with ``--delay`` and '
            '``--max-attempts``.',
        )

    def test_path_acceptor(self):
        self.success_acceptor.matcher = 'path'
        self.success_acceptor.argument = 'MyResource.name'
        self.success_acceptor.expected = 'running'
        description = self.doc_builder.build_waiter_state_description()
        self.assertEqual(
            description,
            'Wait until JMESPath query MyResource.name returns running when '
            'polling with ``my-operation``. It will poll every 5 seconds '
            'until a successful state has been reached. This will exit with '
            'a return code of 255 after 20 failed checks. You can override '
            'the default polling behavior with ``--delay`` and '
            '``--max-attempts``.',
        )

    def test_path_all_acceptor(self):
        self.success_acceptor.matcher = 'pathAll'
        self.success_acceptor.argument = 'MyResource[].name'
        self.success_acceptor.expected = 'running'
        description = self.doc_builder.build_waiter_state_description()
        self.assertEqual(
            description,
            'Wait until JMESPath query MyResource[].name returns running for '
            'all elements when polling with ``my-operation``. It will poll '
            'every 5 seconds until a successful state has been reached. '
            'This will exit with a return code of 255 after 20 failed checks. '
            'You can override the default polling behavior with ``--delay`` '
            'and ``--max-attempts``.',
        )

    def test_path_any_acceptor(self):
        self.success_acceptor.matcher = 'pathAny'
        self.success_acceptor.argument = 'MyResource[].name'
        self.success_acceptor.expected = 'running'
        description = self.doc_builder.build_waiter_state_description()
        self.assertEqual(
            description,
            'Wait until JMESPath query MyResource[].name returns running for '
            'any element when polling with ``my-operation``. It will poll '
            'every 5 seconds until a successful state has been reached. '
            'This will exit with a return code of 255 after 20 failed checks. '
            'You can override the default polling behavior with ``--delay`` '
            'and ``--max-attempts``.',
        )


class TestWaiterCaller(unittest.TestCase):
    def test_invoke(self):
        waiter = mock.Mock()
        waiter_name = 'my_waiter'
        session = mock.Mock()
        session.create_client.return_value.get_waiter.return_value = waiter

        parameters = {'Foo': 'bar', 'Baz': 'biz'}
        parsed_globals = mock.Mock()
        parsed_globals.region = 'us-east-1'
        parsed_globals.endpoint_url = 'myurl'
        parsed_globals.verify_ssl = True

        waiter_caller = WaiterCaller(session, waiter_name)
        waiter_caller.invoke(
            'myservice', 'MyWaiter', parameters, parsed_globals
        )

        # Make sure the client was created properly.
        session.create_client.assert_called_with(
            'myservice',
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl,
        )

        # Make sure we got the correct waiter.
        session.create_client.return_value.get_waiter.assert_called_with(
            waiter_name
        )

        # Ensure the wait command was called properly.
        waiter.wait.assert_called_with(Foo='bar', Baz='biz')

    def test_invoke_with_set_waiter_config(self):
        waiter = mock.Mock()
        waiter_name = 'my_waiter'
        session = mock.Mock()
        session.create_client.return_value.get_waiter.return_value = waiter

        parameters = {'Foo': 'bar'}
        parsed_globals = mock.Mock()
        parsed_globals.region = 'us-east-1'
        parsed_globals.endpoint_url = 'myurl'
        parsed_globals.verify_ssl = True

        waiter_caller = WaiterCaller(session, waiter_name)
        waiter_caller.set_waiter_config({'Delay': 10, 'MaxAttempts': 50})
        waiter_caller.invoke(
            'myservice', 'MyWaiter', parameters, parsed_globals
        )

        waiter.wait.assert_called_with(
            Foo='bar',
            WaiterConfig={'Delay': 10, 'MaxAttempts': 50},
        )

    def test_invoke_without_waiter_config(self):
        waiter = mock.Mock()
        waiter_name = 'my_waiter'
        session = mock.Mock()
        session.create_client.return_value.get_waiter.return_value = waiter

        parameters = {'Foo': 'bar'}
        parsed_globals = mock.Mock()
        parsed_globals.region = 'us-east-1'
        parsed_globals.endpoint_url = 'myurl'
        parsed_globals.verify_ssl = True

        waiter_caller = WaiterCaller(session, waiter_name)
        waiter_caller.invoke(
            'myservice', 'MyWaiter', parameters, parsed_globals
        )

        # Without set_waiter_config, no WaiterConfig should be passed.
        waiter.wait.assert_called_with(Foo='bar')


class TestWaiterArgument(unittest.TestCase):
    def test_add_delay_to_params(self):
        arg = WaiterArgument('delay', 'help text', 'Delay')
        params = {}
        arg.add_to_params(params, 10)
        self.assertEqual(params, {'WaiterConfig': {'Delay': 10}})

    def test_add_max_attempts_to_params(self):
        arg = WaiterArgument('max-attempts', 'help text', 'MaxAttempts')
        params = {}
        arg.add_to_params(params, 50)
        self.assertEqual(params, {'WaiterConfig': {'MaxAttempts': 50}})

    def test_both_params_together(self):
        delay_arg = WaiterArgument('delay', 'help text', 'Delay')
        max_arg = WaiterArgument('max-attempts', 'help text', 'MaxAttempts')
        params = {}
        delay_arg.add_to_params(params, 10)
        max_arg.add_to_params(params, 50)
        self.assertEqual(
            params,
            {'WaiterConfig': {'Delay': 10, 'MaxAttempts': 50}},
        )

    def test_none_value_not_added(self):
        arg = WaiterArgument('delay', 'help text', 'Delay')
        params = {}
        arg.add_to_params(params, None)
        self.assertEqual(params, {})

    def test_cli_name(self):
        arg = WaiterArgument('delay', 'help text', 'Delay')
        self.assertEqual(arg.cli_name, '--delay')

    def test_cli_type_name(self):
        arg = WaiterArgument('delay', 'help text', 'Delay')
        self.assertEqual(arg.cli_type_name, 'integer')

    def test_required_defaults_to_false(self):
        arg = WaiterArgument('delay', 'help text', 'Delay')
        self.assertFalse(arg.required)
