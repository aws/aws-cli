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

from unittest.mock import Mock

from awscli.customizations.ecs.monitormutatinggatewayservice import (
    MUTATION_HANDLERS,
    MonitoringResourcesArgument,
    MonitorMutatingGatewayService,
    register_monitor_mutating_gateway_service,
)


class TestMonitoringResourcesArgument:
    def test_add_to_parser(self):
        parser = Mock()
        arg = MonitoringResourcesArgument('monitor-resources')
        arg.add_to_parser(parser)

        parser.add_argument.assert_called_once()


class TestMonitorMutatingGatewayService:
    def setup_method(self):
        self.mock_watcher_class = Mock()
        self.mock_watcher_class.is_monitoring_available.return_value = True
        self.handler = MonitorMutatingGatewayService(
            'create-gateway-service',
            'DEPLOYMENT',
            watcher_class=self.mock_watcher_class,
        )

    def test_init(self):
        assert self.handler.api == 'create-gateway-service'
        assert self.handler.default_resource_view == 'DEPLOYMENT'
        assert self.handler.api_pascal_case == 'CreateGatewayService'
        assert self.handler.session is None
        assert self.handler.parsed_globals is None

    def test_pascal_case_conversion(self):
        handler = MonitorMutatingGatewayService(
            'update-gateway-service', 'DEPLOYMENT'
        )
        assert handler.api_pascal_case == 'UpdateGatewayService'

        handler = MonitorMutatingGatewayService(
            'delete-gateway-service', 'RESOURCE'
        )
        assert handler.api_pascal_case == 'DeleteGatewayService'

    def test_before_building_argument_table_parser(self):
        session = Mock()

        self.handler.before_building_argument_table_parser(session)

        assert self.handler.session == session

    def test_building_argument_table(self):
        argument_table = {}
        session = Mock()

        self.handler.building_argument_table(argument_table, session)

        assert 'monitor-resources' in argument_table
        assert isinstance(
            argument_table['monitor-resources'], MonitoringResourcesArgument
        )

    def test_operation_args_parsed_with_monitor_resources_true(self):
        parsed_args = Mock()
        parsed_args.monitor_resources = True
        parsed_globals = Mock()

        self.handler.operation_args_parsed(parsed_args, parsed_globals)

        assert self.handler.effective_resource_view

    def test_operation_args_parsed_with_monitor_resources_false(self):
        parsed_args = Mock()
        parsed_args.monitor_resources = False
        parsed_globals = Mock()

        self.handler.operation_args_parsed(parsed_args, parsed_globals)

        assert not self.handler.effective_resource_view

    def test_operation_args_parsed_no_monitor_resources_attr(self):
        parsed_args = Mock()
        # Remove the attribute
        del parsed_args.monitor_resources
        parsed_globals = Mock()

        self.handler.operation_args_parsed(parsed_args, parsed_globals)

        assert not self.handler.effective_resource_view

    def test_after_call_with_monitoring_enabled(self):
        # Setup
        mock_watcher_class = Mock()
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        handler = MonitorMutatingGatewayService(
            'create-express-gateway-service',
            'DEPLOYMENT',
            watcher_class=mock_watcher_class,
        )

        mock_session = Mock()
        mock_parsed_globals = Mock()
        mock_parsed_globals.region = 'us-west-2'
        mock_parsed_globals.endpoint_url = (
            'https://ecs.us-west-2.amazonaws.com'
        )
        mock_parsed_globals.verify_ssl = True

        mock_ecs_client = Mock()
        mock_session.create_client.return_value = mock_ecs_client

        handler.session = mock_session
        handler.parsed_globals = mock_parsed_globals
        handler.effective_resource_view = 'DEPLOYMENT'
        handler.effective_resource_view = 'DEPLOYMENT'

        parsed = {
            'service': {
                'serviceArn': 'arn:aws:ecs:us-west-2:123456789:service/test-service'
            }
        }
        context = {}
        http_response = Mock()
        http_response.status_code = 200

        # Execute
        handler.after_call(parsed, context, http_response)

        # Verify monitoring was initiated
        mock_watcher_class.assert_called_once()
        mock_watcher.exec.assert_called_once()

    def test_after_call_with_monitoring_disabled(self):
        # Setup
        mock_watcher_class = Mock()
        handler = MonitorMutatingGatewayService(
            'create-gateway-service',
            'DEPLOYMENT',
            watcher_class=mock_watcher_class,
        )

        mock_session = Mock()
        mock_parsed_globals = Mock()
        handler.session = mock_session
        handler.parsed_globals = mock_parsed_globals
        handler.effective_resource_view = None

        parsed = {
            'service': {
                'serviceArn': 'arn:aws:ecs:us-west-2:123456789:service/test-service'
            }
        }
        context = {}
        http_response = Mock()
        http_response.status_code = 200

        # Execute
        handler.after_call(parsed, context, http_response)

        # Verify monitoring was skipped
        mock_watcher_class.assert_not_called()

    def test_after_call_no_session(self):
        # Setup
        mock_watcher_class = Mock()
        handler = MonitorMutatingGatewayService(
            'create-gateway-service',
            'DEPLOYMENT',
            watcher_class=mock_watcher_class,
        )

        handler.session = None
        handler.parsed_globals = None
        handler.effective_resource_view = 'DEPLOYMENT'

        parsed = {
            'service': {
                'serviceArn': 'arn:aws:ecs:us-west-2:123456789:service/test-service'
            }
        }
        context = {}
        http_response = Mock()
        http_response.status_code = 200

        # Execute
        handler.after_call(parsed, context, http_response)

        # Verify monitoring was skipped due to missing session
        mock_watcher_class.assert_not_called()

    def test_events(self):
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
    def test_mutation_handlers_configuration(self):
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


class TestRegisterFunction:
    def test_register_monitor_mutating_gateway_service(self):
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
            'after-call.ecs.CreateExpressGatewayService' in registered_events
        )
