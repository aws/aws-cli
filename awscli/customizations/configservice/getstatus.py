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
import sys

from awscli.customizations.commands import BasicCommand


def register_get_status(cli):
    cli.register('building-command-table.configservice', add_get_status)


def add_get_status(command_table, session, **kwargs):
    command_table['get-status'] = GetStatusCommand(session)


class GetStatusCommand(BasicCommand):
    NAME = 'get-status'
    DESCRIPTION = ('Reports the status of all of configuration '
                   'recorders and delivery channels.')

    def __init__(self, session):
        self._config_client = None
        super(GetStatusCommand, self).__init__(session)

    def _run_main(self, parsed_args, parsed_globals):
        self._setup_client(parsed_globals)
        self._check_configuration_recorders()
        self._check_delivery_channels()
        return 0

    def _setup_client(self, parsed_globals):
        client_args = {
            'verify': parsed_globals.verify_ssl,
            'region_name': parsed_globals.region,
            'endpoint_url': parsed_globals.endpoint_url
        }
        self._config_client = self._session.create_client('config',
                                                          **client_args)

    def _check_configuration_recorders(self):
        status = self._config_client.describe_configuration_recorder_status()
        sys.stdout.write('Configuration Recorders:\n\n')
        for configuration_recorder in status['ConfigurationRecordersStatus']:
            self._check_configure_recorder_status(configuration_recorder)
            sys.stdout.write('\n')

    def _check_configure_recorder_status(self, configuration_recorder):
        # Get the name of the recorder and print it out.
        name = configuration_recorder['name']
        sys.stdout.write('name: %s\n' % name)

        # Get the recording status and print it out.
        recording = configuration_recorder['recording']
        recording_map = {False: 'OFF', True: 'ON'}
        sys.stdout.write('recorder: %s\n' % recording_map[recording])

        # If the recorder is on, get the last status and print it out.
        if recording:
            self._check_last_status(configuration_recorder)

    def _check_delivery_channels(self):
        status = self._config_client.describe_delivery_channel_status()
        sys.stdout.write('Delivery Channels:\n\n')
        for delivery_channel in status['DeliveryChannelsStatus']:
            self._check_delivery_channel_status(delivery_channel)
            sys.stdout.write('\n')

    def _check_delivery_channel_status(self, delivery_channel):
        # Get the name of the delivery channel and print it out.
        name = delivery_channel['name']
        sys.stdout.write('name: %s\n' % name)

        # Obtain the various delivery statuses.
        stream_delivery = delivery_channel['configStreamDeliveryInfo']
        history_delivery = delivery_channel['configHistoryDeliveryInfo']
        snapshot_delivery = delivery_channel['configSnapshotDeliveryInfo']

        # Print the statuses out if they exist.
        if stream_delivery:
            self._check_last_status(stream_delivery, 'stream delivery ')
        if history_delivery:
            self._check_last_status(history_delivery, 'history delivery ')
        if snapshot_delivery:
            self._check_last_status(snapshot_delivery, 'snapshot delivery ')

    def _check_last_status(self, status, status_name=''):
        last_status = status['lastStatus']
        sys.stdout.write('last %sstatus: %s\n' % (status_name, last_status))
        if last_status == "FAILURE":
            sys.stdout.write('error code: %s\n' % status['lastErrorCode'])
            sys.stdout.write('message: %s\n' % status['lastErrorMessage'])
