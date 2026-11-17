# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/

from unittest.mock import ANY, Mock, patch

import pytest

from awscli.customizations.ecs import inject_commands
from awscli.customizations.ecs.monitorexpressgatewayservice import (
    ECSMonitorExpressGatewayService,
)


@pytest.fixture
def mock_watcher_class():
    """Fixture that provides a mock watcher class."""
    return Mock()


@pytest.fixture
def mock_session():
    """Fixture that provides a mock session."""
    return Mock()


@pytest.fixture
def command(mock_session, mock_watcher_class):
    """Fixture that provides an ECSMonitorExpressGatewayService command."""
    return ECSMonitorExpressGatewayService(
        mock_session, watcher_class=mock_watcher_class
    )


@pytest.fixture
def command_with_mock_session(mock_session, mock_watcher_class):
    """Fixture that provides command with mock session and client configured."""
    client = Mock()
    mock_session.create_client.return_value = client
    command = ECSMonitorExpressGatewayService(
        mock_session, watcher_class=mock_watcher_class
    )
    return command


class TestECSMonitorExpressGatewayService:
    def test_init(self, command):
        assert command.name == 'monitor-express-gateway-service'
        assert command.DESCRIPTION.startswith('Monitors the progress')

    def test_add_arguments(self, command):
        command._build_arg_table()
        arg_table = command.arg_table

        assert 'service-arn' in arg_table
        assert 'resource-view' in arg_table
        assert 'timeout' in arg_table
        assert 'mode' in arg_table

        # Verify resource-view argument has correct choices
        resource_view_arg = arg_table['resource-view']
        assert resource_view_arg.choices == ['RESOURCE', 'DEPLOYMENT']

        # Verify mode argument has correct choices
        mode_arg = arg_table['mode']
        assert mode_arg.choices == ['INTERACTIVE', 'TEXT-ONLY']

    @patch('sys.stdout.isatty', return_value=False)
    def test_run_main_with_text_only_mode(
        self, mock_isatty, command_with_mock_session, mock_watcher_class
    ):
        command = command_with_mock_session
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        parsed_args = Mock(
            service_arn='arn:aws:ecs:us-west-2:123456789012:service/cluster/service',
            resource_view='RESOURCE',
            timeout=30,
            mode='TEXT-ONLY',
        )
        parsed_globals = Mock(
            region='us-west-2',
            endpoint_url=None,
            verify_ssl=True,
            color='off',
        )

        command._run_main(parsed_args, parsed_globals)

        # Verify watcher was created with correct parameters (positional)
        mock_watcher_class.assert_called_once_with(
            ANY,
            parsed_args.service_arn,
            'RESOURCE',
            'TEXT-ONLY',
            timeout_minutes=30,
            use_color=False,
        )

        # Verify watcher was executed
        mock_watcher.exec.assert_called_once()

    @patch('sys.stdout.isatty', return_value=True)
    def test_run_main_with_interactive_mode(
        self, mock_isatty, command_with_mock_session, mock_watcher_class
    ):
        command = command_with_mock_session
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        parsed_args = Mock(
            service_arn='arn:aws:ecs:us-west-2:123456789012:service/cluster/service',
            resource_view='DEPLOYMENT',
            timeout=60,
            mode='INTERACTIVE',
        )
        parsed_globals = Mock(
            region='us-west-2',
            endpoint_url=None,
            verify_ssl=True,
            color='auto',
        )

        command._run_main(parsed_args, parsed_globals)

        # Verify watcher was created with correct mode
        mock_watcher_class.assert_called_once_with(
            ANY,
            parsed_args.service_arn,
            'DEPLOYMENT',
            'INTERACTIVE',
            timeout_minutes=60,
            use_color=True,
        )

    @patch('sys.stdout.isatty', return_value=True)
    def test_run_main_auto_mode_with_tty(
        self, mock_isatty, command_with_mock_session, mock_watcher_class
    ):
        command = command_with_mock_session
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        parsed_args = Mock(
            service_arn='arn:aws:ecs:us-west-2:123456789012:service/cluster/service',
            resource_view='RESOURCE',
            timeout=30,
            mode=None,  # Auto mode
        )
        parsed_globals = Mock(
            region='us-west-2',
            endpoint_url=None,
            verify_ssl=True,
            color='auto',
        )

        command._run_main(parsed_args, parsed_globals)

        # When mode is None and TTY is available, should use INTERACTIVE
        args = mock_watcher_class.call_args[0]
        assert args[3] == 'INTERACTIVE'

    @patch('sys.stdout.isatty', return_value=False)
    def test_run_main_auto_mode_without_tty(
        self, mock_isatty, command_with_mock_session, mock_watcher_class
    ):
        command = command_with_mock_session
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        parsed_args = Mock(
            service_arn='arn:aws:ecs:us-west-2:123456789012:service/cluster/service',
            resource_view='RESOURCE',
            timeout=30,
            mode=None,  # Auto mode
        )
        parsed_globals = Mock(
            region='us-west-2',
            endpoint_url=None,
            verify_ssl=True,
            color='auto',
        )

        command._run_main(parsed_args, parsed_globals)

        # When mode is None and TTY is not available, should use TEXT-ONLY
        args = mock_watcher_class.call_args[0]
        assert args[3] == 'TEXT-ONLY'

    @patch('sys.stdout.isatty', return_value=False)
    def test_run_main_with_color_on(
        self, mock_isatty, command_with_mock_session, mock_watcher_class
    ):
        command = command_with_mock_session
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        parsed_args = Mock(
            service_arn='arn:aws:ecs:us-west-2:123456789012:service/cluster/service',
            resource_view='RESOURCE',
            timeout=30,
            mode='TEXT-ONLY',
        )
        parsed_globals = Mock(
            region='us-west-2',
            endpoint_url=None,
            verify_ssl=True,
            color='on',
        )

        command._run_main(parsed_args, parsed_globals)

        # Verify color setting is True when color='on'
        call_kwargs = mock_watcher_class.call_args[1]
        assert call_kwargs['use_color'] is True

    @patch('sys.stdout.isatty', return_value=False)
    def test_run_main_creates_ecs_client(
        self,
        mock_isatty,
        mock_session,
        command_with_mock_session,
        mock_watcher_class,
    ):
        command = command_with_mock_session
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        parsed_args = Mock(
            service_arn='arn:aws:ecs:us-west-2:123456789012:service/cluster/service',
            resource_view='RESOURCE',
            timeout=30,
            mode='TEXT-ONLY',
        )
        parsed_globals = Mock(
            region='us-west-2',
            endpoint_url=None,
            verify_ssl=True,
            color='off',
        )

        command._run_main(parsed_args, parsed_globals)

        # Verify ECS client was created with correct parameters
        mock_session.create_client.assert_called_once_with(
            'ecs',
            region_name='us-west-2',
            endpoint_url=None,
            verify=True,
        )

        # Verify client was passed to watcher
        args = mock_watcher_class.call_args[0]
        assert args[0] is not None  # Client was created and passed

    @patch('sys.stdout.isatty', return_value=False)
    def test_run_main_with_default_resource_view(
        self, mock_isatty, command_with_mock_session, mock_watcher_class
    ):
        command = command_with_mock_session
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        parsed_args = Mock(
            service_arn='arn:aws:ecs:us-west-2:123456789012:service/cluster/service',
            resource_view=None,  # Not specified, should use default
            timeout=30,
            mode='TEXT-ONLY',
        )
        parsed_globals = Mock(
            region='us-west-2',
            endpoint_url=None,
            verify_ssl=True,
            color='off',
        )

        command._run_main(parsed_args, parsed_globals)

        # Verify default resource view is passed
        args = mock_watcher_class.call_args[0]
        assert args[2] is None  # Resource view is passed as-is


class TestCommandRegistration:
    def test_inject_commands_registers_monitor_command(self, mock_session):
        command_table = {}

        inject_commands(command_table, mock_session)

        # Verify monitor command is registered
        assert 'monitor-express-gateway-service' in command_table
        command = command_table['monitor-express-gateway-service']
        assert isinstance(command, ECSMonitorExpressGatewayService)
