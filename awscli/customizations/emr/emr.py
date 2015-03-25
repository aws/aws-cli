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

from awscli.customizations.emr import hbase
from awscli.customizations.emr import ssh
from awscli.customizations.emr.addsteps import AddSteps
from awscli.customizations.emr.createcluster import CreateCluster
from awscli.customizations.emr.addinstancegroups import AddInstanceGroups
from awscli.customizations.emr.createdefaultroles import CreateDefaultRoles
from awscli.customizations.emr.modifyclusterattributes import ModifyClusterAttr
from awscli.customizations.emr.installapplications import InstallApplications
from awscli.customizations.emr.describecluster import DescribeCluster
from awscli.customizations.emr.terminateclusters import TerminateClusters
from awscli.customizations.emr.addtags import modify_tags_argument
from awscli.customizations.emr.listclusters \
    import modify_list_clusters_argument
from awscli.customizations.emr.command import override_args_required_option


def emr_initialize(cli):
    """
    The entry point for EMR high level commands.
    """
    cli.register('building-command-table.emr', register_commands)
    cli.register('building-argument-table.emr.add-tags', modify_tags_argument)
    cli.register(
        'building-argument-table.emr.list-clusters',
        modify_list_clusters_argument)
    cli.register('before-building-argument-table-parser.emr.*',
                 override_args_required_option)


def register_commands(command_table, session, **kwargs):
    """
    Called when the EMR command table is being built. Used to inject new
    high level commands into the command list. These high level commands
    must not collide with existing low-level API call names.
    """
    command_table['terminate-clusters'] = TerminateClusters(session)
    command_table['describe-cluster'] = DescribeCluster(session)
    command_table['modify-cluster-attributes'] = ModifyClusterAttr(session)
    command_table['install-applications'] = InstallApplications(session)
    command_table['create-cluster'] = CreateCluster(session)
    command_table['add-steps'] = AddSteps(session)
    command_table['restore-from-hbase-backup'] = \
        hbase.RestoreFromHBaseBackup(session)
    command_table['create-hbase-backup'] = hbase.CreateHBaseBackup(session)
    command_table['schedule-hbase-backup'] = hbase.ScheduleHBaseBackup(session)
    command_table['disable-hbase-backups'] = \
        hbase.DisableHBaseBackups(session)
    command_table['create-default-roles'] = CreateDefaultRoles(session)
    command_table['add-instance-groups'] = AddInstanceGroups(session)
    command_table['ssh'] = ssh.SSH(session)
    command_table['socks'] = ssh.Socks(session)
    command_table['get'] = ssh.Get(session)
    command_table['put'] = ssh.Put(session)
