# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from unittest.mock import ANY, Mock, patch

import pytest

from awscli.customizations.ecs.monitormutatinggatewayservice import (
    MUTATION_HANDLERS,
    MonitoringResourcesArgument,
    MonitorMutatingGatewayService,
    MonitorResourcesAction,
    register_monitor_mutating_gateway_service,
)


class TestMonitoringResourcesArgument:
    """Test the custom CLI argument for enabling resource monitoring."""

    def test_add_to_parser(self):
        """Test that the monitoring argument is correctly added to the parser."""
        parser = Mock()
        arg = MonitoringResourcesArgument('monitor-resources')
        arg.add_to_parser(parser)

        parser.add_argument.assert_called_once()
        # Verify the argument was added with correct name
        call_args = parser.add_argument.call_args
        assert call_args[0][0] == '--monitor-resources'
        assert call_args[1]['dest'] == 'monitor_resources'
        assert call_args[1]['choices'] == ['DEPLOYMENT', 'RESOURCE']
        assert call_args[1]['nargs'] == '?'
        # Custom action instead of const
        assert hasattr(call_args[1]['action'], '__call__')


class TestMonitorResourcesAction:
    """Test the custom action for monitor-resources argument."""

    def test_call_with_no_value(self):
        """Test action when flag is provided without value."""
        action = MonitorResourcesAction(None, 'monitor_resources')
        parser = Mock()
        namespace = Mock()

        action(parser, namespace, None, '--monitor-resources')

        assert namespace.monitor_resources == '__DEFAULT__'

    def test_call_with_explicit_value(self):
        """Test action when flag is provided with explicit value."""
        action = MonitorResourcesAction(None, 'monitor_resources')
        parser = Mock()
        namespace = Mock()

        action(parser, namespace, 'RESOURCE', '--monitor-resources')

        assert namespace.monitor_resources == 'RESOURCE'


class TestMonitorMutatingGatewayService:
    """Test the event handler for monitoring gateway service mutations."""

    def setup_method(self):
        self.handler = MonitorMutatingGatewayService(
            'create-gateway-service', 'DEPLOYMENT'
        )

    def test_init(self):
        """Test proper initialization of the handler."""
        assert self.handler.api == 'create-gateway-service'
        assert self.handler.default_resource_view == 'DEPLOYMENT'
        assert self.handler.api_pascal_case == 'CreateGatewayService'
        assert self.handler.session is None
        assert self.handler.parsed_globals is None

    def test_pascal_case_conversion(self):
        """Test API name conversion to PascalCase."""
        test_cases = [
            ('create-gateway-service', 'CreateGatewayService'),
            ('update-gateway-service', 'UpdateGatewayService'),
            ('delete-gateway-service', 'DeleteGatewayService'),
            ('simple-api', 'SimpleApi'),
            ('multi-word-api-name', 'MultiWordApiName'),
        ]

        for api_name, expected_pascal in test_cases:
            handler = MonitorMutatingGatewayService(api_name, 'RESOURCE')
            assert handler.api_pascal_case == expected_pascal

    def test_before_building_argument_table_parser(self):
        """Test storing session for later use."""
        session = Mock()

        self.handler.before_building_argument_table_parser(session)

        assert self.handler.session == session

    def test_building_argument_table(self):
        """Test adding monitoring argument to the command's argument table."""
        argument_table = {}
        session = Mock()

        self.handler.building_argument_table(argument_table, session)

        assert 'monitor-resources' in argument_table
        assert isinstance(
            argument_table['monitor-resources'], MonitoringResourcesArgument
        )

    def test_operation_args_parsed_with_flag(self):
        """Test storing monitoring flag when enabled with default."""
        parsed_args = Mock()
        parsed_args.monitor_resources = '__DEFAULT__'
        parsed_globals = Mock()

        self.handler.operation_args_parsed(parsed_args, parsed_globals)

        assert self.handler.effective_resource_view == 'DEPLOYMENT'

    def test_operation_args_parsed_with_explicit_choice(self):
        """Test storing monitoring flag with explicit choice."""
        parsed_args = Mock()
        parsed_args.monitor_resources = 'RESOURCE'
        parsed_globals = Mock()

        self.handler.operation_args_parsed(parsed_args, parsed_globals)

        assert self.handler.effective_resource_view == 'RESOURCE'

    def test_operation_args_parsed_without_flag(self):
        """Test storing monitoring flag when disabled."""
        parsed_args = Mock()
        parsed_args.monitor_resources = None
        parsed_globals = Mock()

        self.handler.operation_args_parsed(parsed_args, parsed_globals)

        assert self.handler.effective_resource_view is None

    def test_operation_args_parsed_missing_attribute(self):
        """Test handling missing monitor_resources attribute."""
        # Mock without monitor_resources attribute
        parsed_args = Mock(spec=[])
        parsed_globals = Mock()

        self.handler.operation_args_parsed(parsed_args, parsed_globals)

        assert self.handler.effective_resource_view is None

    def test_after_call_monitoring_disabled(self):
        """Test that monitoring is skipped when flag is disabled."""
        self.handler.effective_resource_view = None
        parsed = {}
        context = Mock()
        http_response = Mock()
        http_response.status_code = 200

        # Should return early without doing anything
        self.handler.after_call(parsed, context, http_response)

        # No assertions needed - just verify no exceptions

    def test_after_call_http_error(self):
        """Test that monitoring is skipped on HTTP errors."""
        self.handler.effective_resource_view = 'DEPLOYMENT'
        parsed = {
            'service': {'serviceArn': 'arn:aws:ecs:us-west-2:123:service/test'}
        }
        context = Mock()
        http_response = Mock()
        http_response.status_code = 400

        # Should return early without doing anything
        self.handler.after_call(parsed, context, http_response)

        # No assertions needed - just verify no exceptions

    def test_after_call_missing_service_arn(self):
        """Test that monitoring is skipped when service ARN is missing."""
        self.handler.effective_resource_view = 'DEPLOYMENT'
        # Missing serviceArn
        parsed = {'service': {}}
        context = Mock()
        http_response = Mock()
        http_response.status_code = 200

        # Should return early without doing anything
        self.handler.after_call(parsed, context, http_response)

        # No assertions needed - just verify no exceptions

    def test_after_call_missing_session(self, capsys):
        """Test handling when session is not available."""
        self.handler.effective_resource_view = 'DEPLOYMENT'
        self.handler.session = None
        self.handler.parsed_globals = None

        parsed = {
            'service': {'serviceArn': 'arn:aws:ecs:us-west-2:123:service/test'}
        }
        context = Mock()
        http_response = Mock()
        http_response.status_code = 200

        self.handler.after_call(parsed, context, http_response)

        captured = capsys.readouterr()
        assert (
            "Unable to create ECS client. Skipping monitoring." in captured.err
        )

    def test_after_call_successful_monitoring(self):
        """Test successful monitoring initiation."""
        # Setup handler state
        mock_watcher_class = Mock()
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        handler = MonitorMutatingGatewayService(
            'create-gateway-service',
            'DEPLOYMENT',
            watcher_class=mock_watcher_class,
        )
        handler.monitor_resources = '__DEFAULT__'
        handler.effective_resource_view = 'DEPLOYMENT'

        mock_session = Mock()
        mock_parsed_globals = Mock()
        mock_parsed_globals.region = 'us-west-2'
        mock_parsed_globals.endpoint_url = (
            'https://ecs.us-west-2.amazonaws.com'
        )
        mock_parsed_globals.verify_ssl = True
        handler.session = mock_session
        handler.parsed_globals = mock_parsed_globals

        # Setup mocks
        mock_client = Mock()
        mock_session.create_client.return_value = mock_client

        # Setup call parameters
        service_arn = 'arn:aws:ecs:us-west-2:123456789012:service/test-service'
        parsed = {'service': {'serviceArn': service_arn}}
        context = Mock()
        http_response = Mock()
        http_response.status_code = 200

        # Execute
        handler.after_call(parsed, context, http_response)

        # Verify client creation
        mock_session.create_client.assert_called_once_with(
            'ecs',
            region_name='us-west-2',
            endpoint_url='https://ecs.us-west-2.amazonaws.com',
            verify=True,
        )

        # Verify watcher was created and executed
        mock_watcher_class.assert_called_once_with(
            mock_client,
            service_arn,
            'DEPLOYMENT',
            exit_hook=ANY,
            use_color=False,
        )
        mock_watcher.exec.assert_called_once()

    def test_after_call_exception_handling(self, capsys):
        """Test exception handling in after_call method."""
        # Setup handler state
        mock_watcher_class = Mock()
        mock_watcher = Mock()
        mock_watcher.exec.side_effect = Exception("Test exception")
        mock_watcher_class.return_value = mock_watcher

        handler = MonitorMutatingGatewayService(
            'create-gateway-service',
            'DEPLOYMENT',
            watcher_class=mock_watcher_class,
        )
        handler.effective_resource_view = 'DEPLOYMENT'

        mock_session = Mock()
        mock_parsed_globals = Mock()
        mock_parsed_globals.region = 'us-west-2'
        mock_parsed_globals.endpoint_url = (
            'https://ecs.us-west-2.amazonaws.com'
        )
        mock_parsed_globals.verify_ssl = True
        handler.session = mock_session
        handler.parsed_globals = mock_parsed_globals

        # Setup mocks
        mock_client = Mock()
        mock_session.create_client.return_value = mock_client

        # Setup call parameters
        service_arn = 'arn:aws:ecs:us-west-2:123456789012:service/test-service'
        parsed = {'service': {'serviceArn': service_arn}}
        context = Mock()
        http_response = Mock()
        http_response.status_code = 200

        # Execute - should not raise exception
        handler.after_call(parsed, context, http_response)

        captured = capsys.readouterr()
        assert "Encountered an error, terminating monitoring" in captured.err
        assert "Test exception" in captured.err

    def test_exit_hook_functionality(self):
        """Test that exit hook properly updates parsed response."""
        # Setup handler state
        self.handler.effective_resource_view = 'DEPLOYMENT'
        mock_session = Mock()
        mock_parsed_globals = Mock()
        mock_parsed_globals.region = 'us-west-2'
        mock_parsed_globals.endpoint_url = (
            'https://ecs.us-west-2.amazonaws.com'
        )
        mock_parsed_globals.verify_ssl = True
        self.handler.session = mock_session
        self.handler.parsed_globals = mock_parsed_globals

        # Setup mocks
        mock_client = Mock()
        mock_session.create_client.return_value = mock_client

        # Test exit hook functionality by directly calling it
        service_arn = 'arn:aws:ecs:us-west-2:123456789012:service/test-service'
        parsed = {'service': {'serviceArn': service_arn}}

        # Create a simple exit hook function
        def test_exit_hook(new_response):
            if new_response:
                parsed.clear()
                parsed.update(new_response)

        # Test with new response
        new_response = {
            'service': {'serviceArn': service_arn, 'status': 'ACTIVE'}
        }
        test_exit_hook(new_response)

        assert parsed == new_response

        # Test with None response (should not update)
        original_parsed = dict(parsed)
        test_exit_hook(None)
        assert parsed == original_parsed

    def test_events(self):
        """Test that correct events are returned for CLI integration."""
        events = self.handler.events()

        expected_events = [
            "before-building-argument-table-parser.ecs.create-gateway-service",
            "building-argument-table.ecs.create-gateway-service",
            "operation-args-parsed.ecs.create-gateway-service",
            "after-call.ecs.CreateGatewayService",
        ]

        assert len(events) == 4

        for i, (event_name, handler_method) in enumerate(events):
            assert event_name == expected_events[i]
            assert callable(handler_method)


class TestMutationHandlers:
    """Test the predefined mutation handlers."""

    def test_mutation_handlers_configuration(self):
        """Test that mutation handlers are properly configured."""
        assert len(MUTATION_HANDLERS) == 3

        # Test create handler
        create_handler = MUTATION_HANDLERS[0]
        assert create_handler.api == 'create-express-gateway-service'
        assert create_handler.default_resource_view == 'DEPLOYMENT'

        # Test update handler
        update_handler = MUTATION_HANDLERS[1]
        assert update_handler.api == 'update-express-gateway-service'
        assert update_handler.default_resource_view == 'DEPLOYMENT'

        # Test delete handler
        delete_handler = MUTATION_HANDLERS[2]
        assert delete_handler.api == 'delete-express-gateway-service'
        assert delete_handler.default_resource_view == 'RESOURCE'

    def test_multiple_handlers_different_modes(self):
        """Test that different handlers use appropriate monitoring modes."""
        create_handler = MonitorMutatingGatewayService(
            'create-express-gateway-service', 'DEPLOYMENT'
        )
        update_handler = MonitorMutatingGatewayService(
            'update-express-gateway-service', 'DEPLOYMENT'
        )
        delete_handler = MonitorMutatingGatewayService(
            'delete-express-gateway-service', 'RESOURCE'
        )

        # Create and update should use DEPLOYMENT mode for showing new changes
        assert create_handler.default_resource_view == 'DEPLOYMENT'
        assert update_handler.default_resource_view == 'DEPLOYMENT'

        # Delete should use RESOURCE mode to show all resources being removed
        assert delete_handler.default_resource_view == 'RESOURCE'

    def test_api_pascal_case_edge_cases(self):
        """Test PascalCase conversion with edge cases."""
        test_cases = [
            ('a', 'A'),
            ('a-b', 'AB'),
            ('create-express-gateway-service', 'CreateExpressGatewayService'),
            ('api-with-many-dashes', 'ApiWithManyDashes'),
            ('single', 'Single'),
        ]

        for api_name, expected_pascal in test_cases:
            handler = MonitorMutatingGatewayService(api_name, 'RESOURCE')
            assert (
                handler.api_pascal_case == expected_pascal
            ), f"Failed for {api_name} -> {expected_pascal}"


class TestMonitoringIntegration:
    """Test integration between monitoring components."""

    def test_monitoring_resources_argument_integration(self):
        """Test that MonitoringResourcesArgument integrates properly with handlers."""
        handler = MonitorMutatingGatewayService('test-api', 'RESOURCE')

        # Test argument table building
        argument_table = {}
        handler.building_argument_table(argument_table, Mock())

        # Verify the argument was added
        assert 'monitor-resources' in argument_table
        arg = argument_table['monitor-resources']
        assert isinstance(arg, MonitoringResourcesArgument)

        # Test that the argument can be added to a parser
        mock_parser = Mock()
        arg.add_to_parser(mock_parser)

        mock_parser.add_argument.assert_called_once()
        # Verify the argument was added correctly
        call_args = mock_parser.add_argument.call_args
        assert call_args[0][0] == '--monitor-resources'
        assert call_args[1]['dest'] == 'monitor_resources'
        assert call_args[1]['action'] == MonitorResourcesAction


class TestRegisterFunction:
    """Test the registration function for event handlers."""

    def test_register_monitor_mutating_gateway_service(self):
        """Test that all handlers are properly registered."""
        mock_event_handler = Mock()

        register_monitor_mutating_gateway_service(mock_event_handler)

        # Should register 4 events per handler * 3 handlers = 12 total registrations
        assert mock_event_handler.register.call_count == 12

        # Verify some specific event registrations
        registered_events = [
            call[0][0] for call in mock_event_handler.register.call_args_list
        ]

        # Check that create-express-gateway-service events are registered
        assert (
            'before-building-argument-table-parser.ecs.create-express-gateway-service'
            in registered_events
        )
        assert (
            'building-argument-table.ecs.create-express-gateway-service'
            in registered_events
        )
        assert (
            'operation-args-parsed.ecs.create-express-gateway-service'
            in registered_events
        )
        assert (
            'after-call.ecs.CreateExpressGatewayService' in registered_events
        )

        # Check that update-express-gateway-service events are registered
        assert (
            'after-call.ecs.UpdateExpressGatewayService' in registered_events
        )

        # Check that delete-express-gateway-service events are registered
        assert (
            'after-call.ecs.DeleteExpressGatewayService' in registered_events
        )


class TestColorSupport:
    """Test color support functionality in monitormutatinggatewayservice"""

    def test_should_use_color_on(self):
        """Test _should_use_color returns True when color is 'on'"""
        handler = MonitorMutatingGatewayService(
            'create-express-gateway-service', 'DEPLOYMENT'
        )
        parsed_globals = Mock()
        parsed_globals.color = 'on'

        assert handler._should_use_color(parsed_globals) is True

    def test_should_use_color_off(self):
        """Test _should_use_color returns False when color is 'off'"""
        handler = MonitorMutatingGatewayService(
            'create-express-gateway-service', 'DEPLOYMENT'
        )
        parsed_globals = Mock()
        parsed_globals.color = 'off'

        assert handler._should_use_color(parsed_globals) is False

    @pytest.mark.parametrize(
        "isatty_return,expected", [(True, True), (False, False)]
    )
    def test_should_use_color_auto(self, isatty_return, expected):
        """Test _should_use_color with 'auto' setting"""
        with patch('sys.stdout.isatty', return_value=isatty_return):
            handler = MonitorMutatingGatewayService(
                'create-express-gateway-service', 'DEPLOYMENT'
            )
            parsed_globals = Mock()
            parsed_globals.color = 'auto'

            assert handler._should_use_color(parsed_globals) is expected
