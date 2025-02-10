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
from awscli.compat import StringIO
from awscli.testutils import mock, unittest
from awscli.customizations.configservice.getstatus import GetStatusCommand


class TestGetStatusCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()

        # Setup the config client mock.
        self.config_client = mock.Mock()
        self.session.create_client.return_value = self.config_client

        # Create some handles to control the description outputs.
        self.recorder_status = []
        self.channel_status = []

        # Set the output handles to the client.
        self.config_client.describe_configuration_recorder_status.\
            return_value = {'ConfigurationRecordersStatus':
                            self.recorder_status}
        self.config_client.describe_delivery_channel_status.\
            return_value = {'DeliveryChannelsStatus': self.channel_status}

        self.parsed_args = mock.Mock()
        self.parsed_globals = mock.Mock()
        self.cmd = GetStatusCommand(self.session)

    def _make_delivery_channel_status(self, name, stream_delivery_status,
                                      history_delivery_status,
                                      snapshot_delivery_status):
        status = {
            'name': 'default',
            'configStreamDeliveryInfo': stream_delivery_status,
            'configHistoryDeliveryInfo': history_delivery_status,
            'configSnapshotDeliveryInfo': snapshot_delivery_status
        }
        return status

    def test_create_client(self):
        # Set values for the parsed globals.
        self.parsed_globals.verify_ssl = True
        self.parsed_globals.region = 'us-east-1'
        self.parsed_globals.endpoint_url = 'https://foo.com'

        # Ensure that the client was built with the proper arguments.
        self.cmd._run_main(self.parsed_args, self.parsed_globals)
        self.session.create_client.assert_called_with(
            'config',
            verify=self.parsed_globals.verify_ssl,
            region_name=self.parsed_globals.region,
            endpoint_url=self.parsed_globals.endpoint_url
        )

    def test_configuration_recorder_success(self):
        status = {'name': 'default', 'recording': True,
                  'lastStatus': 'SUCCESS'}
        self.recorder_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'name: default\n'
            'recorder: ON\n'
            'last status: SUCCESS\n\n'
            'Delivery Channels:\n\n'
        )

        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())

    def test_configuration_recorder_fail(self):
        status = {'name': 'default', 'recording': True,
                  'lastStatus': 'FAILURE', 'lastErrorCode': '500',
                  'lastErrorMessage': 'This is the error'}
        self.recorder_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'name: default\n'
            'recorder: ON\n'
            'last status: FAILURE\n'
            'error code: 500\n'
            'message: This is the error\n\n'
            'Delivery Channels:\n\n'
        )

        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())

    def test_configuration_recorder_off(self):
        status = {'name': 'default', 'recording': False}
        self.recorder_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'name: default\n'
            'recorder: OFF\n\n'
            'Delivery Channels:\n\n'
        )

        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())

    def test_multiple_configuration_recorders(self):
        status = {'name': 'default', 'recording': True,
                  'lastStatus': 'SUCCESS'}
        self.recorder_status.append(status)

        status = {'name': 'default', 'recording': True,
                  'lastStatus': 'FAILURE', 'lastErrorCode': '500',
                  'lastErrorMessage': 'This is the error'}
        self.recorder_status.append(status)

        status = {'name': 'default', 'recording': False}
        self.recorder_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'name: default\n'
            'recorder: ON\n'
            'last status: SUCCESS\n\n'
            'name: default\n'
            'recorder: ON\n'
            'last status: FAILURE\n'
            'error code: 500\n'
            'message: This is the error\n\n'
            'name: default\n'
            'recorder: OFF\n\n'
            'Delivery Channels:\n\n'
        )
        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())

    def test_delivery_channel_success_single_delivery_info(self):
        name = 'default'
        success = {'lastStatus': 'SUCCESS'}

        stream_delivery_status = success
        history_delivery_status = {}
        snapshot_delivery_status = {}

        status = self._make_delivery_channel_status(
            name, stream_delivery_status=stream_delivery_status,
            history_delivery_status=history_delivery_status,
            snapshot_delivery_status=snapshot_delivery_status
        )
        self.channel_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'Delivery Channels:\n\n'
            'name: default\n'
            'last stream delivery status: SUCCESS\n\n'
        )

        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())

    def test_delivery_channel_success_multiple_delivery_info(self):
        name = 'default'
        success = {'lastStatus': 'SUCCESS'}

        stream_delivery_status = success
        history_delivery_status = success
        snapshot_delivery_status = success

        status = self._make_delivery_channel_status(
            name, stream_delivery_status=stream_delivery_status,
            history_delivery_status=history_delivery_status,
            snapshot_delivery_status=snapshot_delivery_status
        )
        self.channel_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'Delivery Channels:\n\n'
            'name: default\n'
            'last stream delivery status: SUCCESS\n'
            'last history delivery status: SUCCESS\n'
            'last snapshot delivery status: SUCCESS\n\n'
        )

        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())

    def test_delivery_channel_fail_single_delivery_info(self):
        name = 'default'
        failure = {'lastStatus': 'FAILURE', 'lastErrorCode': '500',
                   'lastErrorMessage': 'This is the error'}

        stream_delivery_status = failure
        history_delivery_status = {}
        snapshot_delivery_status = {}

        status = self._make_delivery_channel_status(
            name, stream_delivery_status=stream_delivery_status,
            history_delivery_status=history_delivery_status,
            snapshot_delivery_status=snapshot_delivery_status
        )
        self.channel_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'Delivery Channels:\n\n'
            'name: default\n'
            'last stream delivery status: FAILURE\n'
            'error code: 500\n'
            'message: This is the error\n\n'
        )

        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())

    def test_delivery_channel_mixed_multiple_delivery_info(self):
        name = 'default'
        success = {'lastStatus': 'SUCCESS'}
        failure = {'lastStatus': 'FAILURE', 'lastErrorCode': '500',
                   'lastErrorMessage': 'This is the error'}

        stream_delivery_status = failure
        history_delivery_status = success
        snapshot_delivery_status = success

        status = self._make_delivery_channel_status(
            name, stream_delivery_status=stream_delivery_status,
            history_delivery_status=history_delivery_status,
            snapshot_delivery_status=snapshot_delivery_status
        )
        self.channel_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'Delivery Channels:\n\n'
            'name: default\n'
            'last stream delivery status: FAILURE\n'
            'error code: 500\n'
            'message: This is the error\n'
            'last history delivery status: SUCCESS\n'
            'last snapshot delivery status: SUCCESS\n\n'
        )

        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())

    def test_multiple_delivery_channels(self):
        name = 'default'
        success = {'lastStatus': 'SUCCESS'}
        failure = {'lastStatus': 'FAILURE', 'lastErrorCode': '500',
                   'lastErrorMessage': 'This is the error'}

        stream_delivery_status = failure
        history_delivery_status = success
        snapshot_delivery_status = success

        status = self._make_delivery_channel_status(
            name, stream_delivery_status=stream_delivery_status,
            history_delivery_status=history_delivery_status,
            snapshot_delivery_status=snapshot_delivery_status
        )
        self.channel_status.append(status)
        self.channel_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'Delivery Channels:\n\n'
            'name: default\n'
            'last stream delivery status: FAILURE\n'
            'error code: 500\n'
            'message: This is the error\n'
            'last history delivery status: SUCCESS\n'
            'last snapshot delivery status: SUCCESS\n\n'
            'name: default\n'
            'last stream delivery status: FAILURE\n'
            'error code: 500\n'
            'message: This is the error\n'
            'last history delivery status: SUCCESS\n'
            'last snapshot delivery status: SUCCESS\n\n'
        )

        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())

    def test_full_get_status(self):
        # Create the configuration recorder statuses.
        status = {'name': 'default', 'recording': True,
                  'lastStatus': 'SUCCESS'}
        self.recorder_status.append(status)

        status = {'name': 'default', 'recording': True,
                  'lastStatus': 'FAILURE', 'lastErrorCode': '500',
                  'lastErrorMessage': 'This is the error'}
        self.recorder_status.append(status)

        status = {'name': 'default', 'recording': False}
        self.recorder_status.append(status)

        # Create the delivery channel statuses.
        name = 'default'
        success = {'lastStatus': 'SUCCESS'}
        failure = {'lastStatus': 'FAILURE', 'lastErrorCode': '500',
                   'lastErrorMessage': 'This is the error'}

        stream_delivery_status = failure
        history_delivery_status = success
        snapshot_delivery_status = success

        status = self._make_delivery_channel_status(
            name, stream_delivery_status=stream_delivery_status,
            history_delivery_status=history_delivery_status,
            snapshot_delivery_status=snapshot_delivery_status
        )
        self.channel_status.append(status)
        self.channel_status.append(status)

        expected_output = (
            'Configuration Recorders:\n\n'
            'name: default\n'
            'recorder: ON\n'
            'last status: SUCCESS\n\n'
            'name: default\n'
            'recorder: ON\n'
            'last status: FAILURE\n'
            'error code: 500\n'
            'message: This is the error\n\n'
            'name: default\n'
            'recorder: OFF\n\n'
            'Delivery Channels:\n\n'
            'name: default\n'
            'last stream delivery status: FAILURE\n'
            'error code: 500\n'
            'message: This is the error\n'
            'last history delivery status: SUCCESS\n'
            'last snapshot delivery status: SUCCESS\n\n'
            'name: default\n'
            'last stream delivery status: FAILURE\n'
            'error code: 500\n'
            'message: This is the error\n'
            'last history delivery status: SUCCESS\n'
            'last snapshot delivery status: SUCCESS\n\n'
        )

        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.cmd._run_main(self.parsed_args, self.parsed_globals)
            self.assertEqual(expected_output, mock_stdout.getvalue())
