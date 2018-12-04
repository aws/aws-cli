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

from awscli.customizations.emr import constants
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import hbaseutils
from awscli.customizations.emr import helptext
from awscli.customizations.emr.command import Command


class RestoreFromHBaseBackup(Command):
    NAME = 'restore-from-hbase-backup'
    DESCRIPTION = ('Restores HBase from S3. ' +
                   helptext.AVAILABLE_ONLY_FOR_AMI_VERSIONS)
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID},
        {'name': 'dir', 'required': True,
         'help_text': helptext.HBASE_BACKUP_DIR},
        {'name': 'backup-version',
         'help_text': helptext.HBASE_BACKUP_VERSION}
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        steps = []
        args = hbaseutils.build_hbase_restore_from_backup_args(
            parsed_args.dir, parsed_args.backup_version)

        step_config = emrutils.build_step(
            jar=constants.HBASE_JAR_PATH,
            name=constants.HBASE_RESTORE_STEP_NAME,
            action_on_failure=constants.CANCEL_AND_WAIT,
            args=args)

        steps.append(step_config)
        parameters = {'JobFlowId': parsed_args.cluster_id,
                      'Steps': steps}
        emrutils.call_and_display_response(self._session, 'AddJobFlowSteps',
                                           parameters, parsed_globals)
        return 0


class ScheduleHBaseBackup(Command):
    NAME = 'schedule-hbase-backup'
    DESCRIPTION = ('Adds a step to schedule automated HBase backup. ' +
                   helptext.AVAILABLE_ONLY_FOR_AMI_VERSIONS)
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID},
        {'name': 'type', 'required': True,
         'help_text': "<p>Backup type. You can specify 'incremental' or "
                      "'full'.</p>"},
        {'name': 'dir', 'required': True,
         'help_text': helptext.HBASE_BACKUP_DIR},
        {'name': 'interval', 'required': True,
         'help_text': '<p>The time between backups.</p>'},
        {'name': 'unit', 'required': True,
         'help_text': "<p>The time unit for backup's time-interval. "
                      "You can specify one of the following values:"
                      " 'minutes', 'hours', or 'days'.</p>"},
        {'name': 'start-time',
         'help_text': '<p>The time of the first backup in ISO format.</p>'
         ' e.g. 2014-04-21T05:26:10Z. Default is now.'},
        {'name': 'consistent', 'action': 'store_true',
         'help_text': '<p>Performs a consistent backup.'
                      ' Pauses all write operations to the HBase cluster'
                      ' during the backup process.</p>'}
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        steps = []
        self._check_type(parsed_args.type)
        self._check_unit(parsed_args.unit)
        args = self._build_hbase_schedule_backup_args(parsed_args)

        step_config = emrutils.build_step(
            jar=constants.HBASE_JAR_PATH,
            name=constants.HBASE_SCHEDULE_BACKUP_STEP_NAME,
            action_on_failure=constants.CANCEL_AND_WAIT,
            args=args)

        steps.append(step_config)
        parameters = {'JobFlowId': parsed_args.cluster_id,
                      'Steps': steps}
        emrutils.call_and_display_response(self._session, 'AddJobFlowSteps',
                                           parameters, parsed_globals)
        return 0

    def _check_type(self, type):
        type = type.lower()
        if type != constants.FULL and type != constants.INCREMENTAL:
            raise ValueError('aws: error: invalid type. '
                             'type should be either ' +
                             constants.FULL + ' or ' + constants.INCREMENTAL +
                             '.')

    def _check_unit(self, unit):
        unit = unit.lower()
        if (unit != constants.MINUTES and
                unit != constants.HOURS and
                unit != constants.DAYS):
            raise ValueError('aws: error: invalid unit. unit should be one of'
                             ' the following values: ' + constants.MINUTES +
                             ', ' + constants.HOURS + ' or ' + constants.DAYS +
                             '.')

    def _build_hbase_schedule_backup_args(self, parsed_args):
        args = [constants.HBASE_MAIN, constants.HBASE_SCHEDULED_BACKUP,
                constants.TRUE, constants.HBASE_BACKUP_DIR, parsed_args.dir]

        type = parsed_args.type.lower()
        unit = parsed_args.unit.lower()

        if parsed_args.consistent is True:
            args.append(constants.HBASE_BACKUP_CONSISTENT)

        if type == constants.FULL:
            args.append(constants.HBASE_FULL_BACKUP_INTERVAL)
        else:
            args.append(constants.HBASE_INCREMENTAL_BACKUP_INTERVAL)

        args.append(parsed_args.interval)

        if type == constants.FULL:
            args.append(constants.HBASE_FULL_BACKUP_INTERVAL_UNIT)
        else:
            args.append(constants.HBASE_INCREMENTAL_BACKUP_INTERVAL_UNIT)

        args.append(unit)
        args.append(constants.HBASE_BACKUP_STARTTIME)

        if parsed_args.start_time is not None:
            args.append(parsed_args.start_time)
        else:
            args.append(constants.NOW)

        return args


class CreateHBaseBackup(Command):
    NAME = 'create-hbase-backup'
    DESCRIPTION = ('Creates a HBase backup in S3. ' +
                   helptext.AVAILABLE_ONLY_FOR_AMI_VERSIONS)
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID},
        {'name': 'dir', 'required': True,
         'help_text': helptext.HBASE_BACKUP_DIR},
        {'name': 'consistent', 'action': 'store_true',
         'help_text': '<p>Performs a consistent backup. Pauses all write'
                      ' operations to the HBase cluster during the backup'
                      ' process.</p>'}
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        steps = []
        args = self._build_hbase_backup_args(parsed_args)

        step_config = emrutils.build_step(
            jar=constants.HBASE_JAR_PATH,
            name=constants.HBASE_BACKUP_STEP_NAME,
            action_on_failure=constants.CANCEL_AND_WAIT,
            args=args)

        steps.append(step_config)
        parameters = {'JobFlowId': parsed_args.cluster_id,
                      'Steps': steps}
        emrutils.call_and_display_response(self._session, 'AddJobFlowSteps',
                                           parameters, parsed_globals)
        return 0

    def _build_hbase_backup_args(self, parsed_args):
        args = [constants.HBASE_MAIN,
                constants.HBASE_BACKUP,
                constants.HBASE_BACKUP_DIR, parsed_args.dir]

        if parsed_args.consistent is True:
            args.append(constants.HBASE_BACKUP_CONSISTENT)

        return args


class DisableHBaseBackups(Command):
    NAME = 'disable-hbase-backups'
    DESCRIPTION = ('Add a step to disable automated HBase backups. ' +
                   helptext.AVAILABLE_ONLY_FOR_AMI_VERSIONS)
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': helptext.CLUSTER_ID},
        {'name': 'full', 'action': 'store_true',
         'help_text': 'Disables full backup.'},
        {'name': 'incremental', 'action': 'store_true',
         'help_text': 'Disables incremental backup.'}
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        steps = []

        args = self._build_hbase_disable_backups_args(parsed_args)

        step_config = emrutils.build_step(
            constants.HBASE_JAR_PATH,
            constants.HBASE_SCHEDULE_BACKUP_STEP_NAME,
            constants.CANCEL_AND_WAIT,
            args)

        steps.append(step_config)
        parameters = {'JobFlowId': parsed_args.cluster_id,
                      'Steps': steps}
        emrutils.call_and_display_response(self._session, 'AddJobFlowSteps',
                                           parameters, parsed_globals)
        return 0

    def _build_hbase_disable_backups_args(self, parsed_args):
        args = [constants.HBASE_MAIN, constants.HBASE_SCHEDULED_BACKUP,
                constants.FALSE]
        if parsed_args.full is False and parsed_args.incremental is False:
            error_message = 'Should specify at least one of --' +\
                            constants.FULL + ' and --' +\
                            constants.INCREMENTAL + '.'
            raise ValueError(error_message)
        if parsed_args.full is True:
            args.append(constants.HBASE_DISABLE_FULL_BACKUP)
        if parsed_args.incremental is True:
            args.append(constants.HBASE_DISABLE_INCREMENTAL_BACKUP)

        return args
