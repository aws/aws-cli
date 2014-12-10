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


from awscli.customizations.commands import BasicCommand
from awscli.customizations.emr import constants
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import steputils
from awscli.customizations.emr import hbaseutils
from awscli.customizations.emr import argumentschema
from awscli.customizations.emr import helptext
from awscli.customizations.emr import exceptions
from awscli.customizations.emr import applicationutils
from awscli.customizations.emr import instancegroupsutils
from awscli.customizations.emr.createdefaultroles import EMR_ROLE_NAME
from awscli.customizations.emr.createdefaultroles import EC2_ROLE_NAME
import re


class CreateCluster(BasicCommand):
    NAME = 'create-cluster'
    DESCRIPTION = (
        'Creates and starts running an EMR cluster.\n'
        '\nQuick start:\n'
        '\naws emr create-cluster --ami-version <ami-version> --instance-type'
        ' <instance-type> [--instance-count <instance-count>]\n')
    ARG_TABLE = [
        {'name': 'ami-version',
         'help_text': helptext.AMI_VERSION,
         'required': True},
        {'name': 'instance-groups',
         'schema': argumentschema.INSTANCE_GROUPS_SCHEMA,
         'help_text': helptext.INSTANCE_GROUPS},
        {'name': 'instance-type',
         'help_text': helptext.INSTANCE_TYPE},
        {'name': 'instance-count',
         'help_text': helptext.INSTANCE_COUNT},
        {'name': 'auto-terminate', 'action': 'store_true',
         'group_name': 'auto_terminate',
         'help_text': helptext.AUTO_TERMINATE},
        {'name': 'no-auto-terminate', 'action': 'store_true',
         'group_name': 'auto_terminate'},
        {'name': 'name',
         'default': 'Development Cluster',
         'help_text': helptext.CLUSTER_NAME},
        {'name': 'log-uri',
         'help_text': helptext.LOG_URI},
        {'name': 'service-role',
         'help_text': helptext.SERVICE_ROLE},
        {'name': 'use-default-roles', 'action': 'store_true',
         'help_text': helptext.USE_DEFAULT_ROLES},
        {'name': 'ec2-attributes',
         'help_text': helptext.EC2_ATTRIBUTES,
         'schema': argumentschema.EC2_ATTRIBUTES_SCHEMA},
        {'name': 'termination-protected', 'action': 'store_true',
         'group_name': 'termination_protected',
         'help_text': helptext.TERMINATION_PROTECTED},
        {'name': 'no-termination-protected', 'action': 'store_true',
         'group_name': 'termination_protected'},
        {'name': 'visible-to-all-users', 'action': 'store_true',
         'group_name': 'visibility',
         'help_text': helptext.VISIBILITY},
        {'name': 'no-visible-to-all-users', 'action': 'store_true',
         'group_name': 'visibility'},
        {'name': 'enable-debugging', 'action': 'store_true',
         'group_name': 'debug',
         'help_text': helptext.DEBUGGING},
        {'name': 'no-enable-debugging', 'action': 'store_true',
         'group_name': 'debug'},
        {'name': 'tags', 'nargs': '+',
         'help_text': helptext.TAGS,
         'schema': argumentschema.TAGS_SCHEMA},
        {'name': 'bootstrap-actions',
         'help_text': helptext.BOOTSTRAP_ACTIONS,
         'schema': argumentschema.BOOTSTRAP_ACTIONS_SCHEMA},
        {'name': 'applications',
         'help_text': helptext.APPLICATIONS,
         'schema': argumentschema.APPLICATIONS_SCHEMA},
        {'name': 'emrfs',
         'help_text': helptext.EMR_FS,
         'schema': argumentschema.EMR_FS_SCHEMA},
        {'name': 'steps',
         'schema': argumentschema.STEPS_SCHEMA,
         'help_text': helptext.STEPS},
        {'name': 'additional-info',
         'help_text': helptext.ADDITIONAL_INFO},
        {'name': 'restore-from-hbase-backup',
         'schema': argumentschema.HBASE_RESTORE_FROM_BACKUP_SCHEMA,
         'help_text': helptext.RESTORE_FROM_HBASE}
    ]
    SYNOPSIS = BasicCommand.FROM_FILE('emr', 'create-cluster-synopsis.rst')
    EXAMPLES = BasicCommand.FROM_FILE('emr', 'create-cluster-examples.rst')

    def _run_main(self, parsed_args, parsed_globals):
        emr = self._session.get_service('emr')
        params = {}
        bootstrap_actions = []
        params['Name'] = parsed_args.name

        service_role_validation_message = (
            " Either choose --use-default-roles or use both --service-role "
            "<roleName> and --ec2-attributes InstanceProfile=<profileName>.")

        if parsed_args.use_default_roles is True and \
                parsed_args.service_role is not None:
                raise exceptions.MutualExclusiveOptionError(
                    option1="--use-default-roles",
                    option2="--service-role",
                    message=service_role_validation_message)

        if parsed_args.use_default_roles is True and \
                parsed_args.ec2_attributes is not None and \
                'InstanceProfile' in parsed_args.ec2_attributes:
                raise exceptions.MutualExclusiveOptionError(
                    option1="--use-default-roles",
                    option2="--ec2-attributes InstanceProfile",
                    message=service_role_validation_message)

        instances_config = {}
        instances_config['InstanceGroups'] = \
            instancegroupsutils.validate_and_build_instance_groups(
                instance_groups=parsed_args.instance_groups,
                instance_type=parsed_args.instance_type,
                instance_count=parsed_args.instance_count)

        is_valid_ami_version = re.match('\d?\..*', parsed_args.ami_version)
        if is_valid_ami_version is None:
            raise exceptions.InvalidAmiVersionError(
                ami_version=parsed_args.ami_version)
        params['AmiVersion'] = parsed_args.ami_version
        emrutils.apply_dict(
            params, 'AdditionalInfo', parsed_args.additional_info)
        emrutils.apply_dict(params, 'LogUri', parsed_args.log_uri)

        if parsed_args.use_default_roles is True:
            parsed_args.service_role = EMR_ROLE_NAME
            if parsed_args.ec2_attributes is None:
                parsed_args.ec2_attributes = {}
            parsed_args.ec2_attributes['InstanceProfile'] = EC2_ROLE_NAME

        emrutils.apply_dict(params, 'ServiceRole', parsed_args.service_role)

        if (
                parsed_args.no_auto_terminate is False and
                parsed_args.auto_terminate is False):
            parsed_args.no_auto_terminate = True

        instances_config['KeepJobFlowAliveWhenNoSteps'] = \
            emrutils.apply_boolean_options(
                parsed_args.no_auto_terminate,
                '--no-auto-terminate',
                parsed_args.auto_terminate,
                '--auto-terminate')

        instances_config['TerminationProtected'] = \
            emrutils.apply_boolean_options(
                parsed_args.termination_protected,
                '--termination-protected',
                parsed_args.no_termination_protected,
                '--no-termination-protected')

        if (
                parsed_args.visible_to_all_users is False and
                parsed_args.no_visible_to_all_users is False):
            parsed_args.visible_to_all_users = True

        params['VisibleToAllUsers'] = \
            emrutils.apply_boolean_options(
                parsed_args.visible_to_all_users,
                '--visible-to-all-users',
                parsed_args.no_visible_to_all_users,
                '--no-visible-to-all-users')

        params['Tags'] = emrutils.parse_tags(parsed_args.tags)
        params['Instances'] = instances_config

        if parsed_args.ec2_attributes is not None:
            self._build_ec2_attributes(
                cluster=params, parsed_attrs=parsed_args.ec2_attributes)

        debugging_enabled = emrutils.apply_boolean_options(
            parsed_args.enable_debugging,
            '--enable-debugging',
            parsed_args.no_enable_debugging,
            '--no-enable-debugging')

        if parsed_args.log_uri is None and debugging_enabled is True:
            raise exceptions.LogUriError

        if debugging_enabled is True:
            self._update_cluster_dict(
                cluster=params,
                key='Steps',
                value=[self._build_enable_debugging(parsed_globals)])

        if parsed_args.applications is not None:
            app_list, ba_list, step_list = applicationutils.build_applications(
                session=self._session,
                parsed_applications=parsed_args.applications,
                parsed_globals=parsed_globals,
                ami_version=params['AmiVersion'])
            self._update_cluster_dict(
                params, 'NewSupportedProducts', app_list)
            self._update_cluster_dict(
                params, 'BootstrapActions', ba_list)
            self._update_cluster_dict(
                params, 'Steps', step_list)

        hbase_restore_config = parsed_args.restore_from_hbase_backup
        if hbase_restore_config is not None:
            args = hbaseutils.build_hbase_restore_from_backup_args(
                dir=hbase_restore_config.get('Dir'),
                backup_version=hbase_restore_config.get('BackupVersion'))
            step_config = emrutils.build_step(
                jar=constants.HBASE_JAR_PATH,
                name=constants.HBASE_RESTORE_STEP_NAME,
                action_on_failure=constants.CANCEL_AND_WAIT,
                args=args)
            self._update_cluster_dict(
                params, 'Steps', [step_config])

        if parsed_args.bootstrap_actions is not None:
            self._build_bootstrap_actions(
                cluster=params,
                parsed_boostrap_actions=parsed_args.bootstrap_actions)

        if parsed_args.emrfs is not None:
            emr_fs_ba_args = self._build_emr_fs_args(parsed_args.emrfs)
            emr_fs_ba_config = \
                emrutils.build_bootstrap_action(
                    path=emrutils.build_s3_link(
                        relative_path=constants.CONFIG_HADOOP_PATH,
                        region=parsed_globals.region),
                    name=constants.EMR_FS_BA_NAME,
                    args=emr_fs_ba_args)
            self._update_cluster_dict(
                cluster=params, key='BootstrapActions',
                value=[emr_fs_ba_config])

        if parsed_args.steps is not None:
            steps_list = steputils.build_step_config_list(
                parsed_step_list=parsed_args.steps,
                region=parsed_globals.region)
            self._update_cluster_dict(
                cluster=params, key='Steps', value=steps_list)

        self._validate_required_applications(parsed_args)

        run_job_flow = emr.get_operation('RunJobFlow')
        run_job_flow_response = emrutils.call(
            self._session, run_job_flow, params,
            parsed_globals.region, parsed_globals.endpoint_url,
            parsed_globals.verify_ssl)

        constructed_result = self._construct_result(run_job_flow_response[1])
        emrutils.display_response(self._session, run_job_flow,
                                  constructed_result, parsed_globals)

        return 0

    def _construct_result(self, run_job_flow_result):
        jobFlowId = None
        if run_job_flow_result is not None:
                jobFlowId = run_job_flow_result.get('JobFlowId')

        if jobFlowId is not None:
            return {'ClusterId': jobFlowId}
        else:
            return {}

    def _build_ec2_attributes(self, cluster, parsed_attrs):
        keys = parsed_attrs.keys()
        instances = cluster['Instances']
        if 'AvailabilityZone' in keys and 'SubnetId' in keys:
            raise exceptions.SubnetAndAzValidationError

        emrutils.apply_params(
            src_params=parsed_attrs, src_key='KeyName',
            dest_params=instances, dest_key='Ec2KeyName')
        emrutils.apply_params(
            src_params=parsed_attrs, src_key='SubnetId',
            dest_params=instances, dest_key='Ec2SubnetId')

        if 'AvailabilityZone' in keys:
            instances['Placement'] = dict()
            emrutils.apply_params(
                src_params=parsed_attrs, src_key='AvailabilityZone',
                dest_params=instances['Placement'],
                dest_key='AvailabilityZone')

        emrutils.apply_params(
            src_params=parsed_attrs, src_key='InstanceProfile',
            dest_params=cluster, dest_key='JobFlowRole')

        emrutils.apply_params(
            src_params=parsed_attrs, src_key='EmrManagedMasterSecurityGroup',
            dest_params=instances, dest_key='EmrManagedMasterSecurityGroup')

        emrutils.apply_params(
            src_params=parsed_attrs, src_key='EmrManagedSlaveSecurityGroup',
            dest_params=instances, dest_key='EmrManagedSlaveSecurityGroup')

        emrutils.apply_params(
            src_params=parsed_attrs, src_key='AdditionalMasterSecurityGroups',
            dest_params=instances, dest_key='AdditionalMasterSecurityGroups')

        emrutils.apply_params(
            src_params=parsed_attrs, src_key='AdditionalSlaveSecurityGroups',
            dest_params=instances, dest_key='AdditionalSlaveSecurityGroups')

        emrutils.apply(params=cluster, key='Instances', value=instances)

        return cluster

    def _build_bootstrap_actions(
            self, cluster, parsed_boostrap_actions):
        cluster_ba_list = cluster.get('BootstrapActions')
        if cluster_ba_list is None:
            cluster_ba_list = []

        bootstrap_actions = []
        if len(cluster_ba_list) + len(parsed_boostrap_actions) \
                > constants.MAX_BOOTSTRAP_ACTION_NUMBER:
            raise ValueError('aws: error: maximum number of '
                             'bootstrap actions for a cluster exceeded.')

        for ba in parsed_boostrap_actions:
            ba_config = {}
            if ba.get('Name') is not None:
                ba_config['Name'] = ba.get('Name')
            else:
                ba_config['Name'] = constants.BOOTSTRAP_ACTION_NAME
            script_arg_config = {}
            emrutils.apply_params(
                src_params=ba, src_key='Path',
                dest_params=script_arg_config, dest_key='Path')
            emrutils.apply_params(
                src_params=ba, src_key='Args',
                dest_params=script_arg_config, dest_key='Args')
            emrutils.apply(
                params=ba_config,
                key='ScriptBootstrapAction',
                value=script_arg_config)
            bootstrap_actions.append(ba_config)

        result = cluster_ba_list + bootstrap_actions
        if len(result) > 0:
            cluster['BootstrapActions'] = result

        return cluster

    def _build_enable_debugging(self, parsed_globals):
        return emrutils.build_step(
            name=constants.DEBUGGING_NAME,
            action_on_failure=constants.TERMINATE_CLUSTER,
            jar=emrutils.get_script_runner(parsed_globals.region),
            args=[emrutils.build_s3_link(
                relative_path=constants.DEBUGGING_PATH,
                region=parsed_globals.region)])

    def _update_cluster_dict(self, cluster, key, value):
        if key in cluster.keys():
            cluster[key] += value
        elif value is not None and len(value) > 0:
            cluster[key] = value
        return cluster

    # Checks if the applications required by steps are specified
    # using the --applications option.
    def _validate_required_applications(self, parsed_args):

        specified_apps = set([])
        if parsed_args.applications is not None:
            specified_apps = \
                set([app['Name'].lower() for app in parsed_args.applications])

        missing_apps = self._get_missing_applications_for_steps(specified_apps,
                                                                parsed_args)
        # Check for HBase.
        if parsed_args.restore_from_hbase_backup is not None:
            if constants.HBASE not in specified_apps:
                missing_apps.add(constants.HBASE.title())

        if len(missing_apps) != 0:
            raise exceptions.MissingApplicationsError(
                applications=missing_apps)

    def _get_missing_applications_for_steps(self, specified_apps, parsed_args):
        allowed_app_steps = set([constants.HIVE, constants.PIG,
                                 constants.IMPALA])
        missing_apps = set([])
        if parsed_args.steps is not None:
            for step in parsed_args.steps:
                if len(missing_apps) == len(allowed_app_steps):
                    break
                step_type = step.get('Type')

                if step_type is not None:
                    step_type = step_type.lower()
                    if step_type in allowed_app_steps and \
                            step_type not in specified_apps:
                        missing_apps.add(step['Type'].title())
        return missing_apps

    def _build_emr_fs_args(self, parsed_emr_fs):
        args = []
        if parsed_emr_fs.get('Consistent') is not None:
            args.append(constants.EMR_FS_BA_ARG_KEY)
            args.append(
                constants.EMR_FS_CONSISTENT_KEY +
                '=' + str(parsed_emr_fs.get('Consistent')).lower())

        if parsed_emr_fs.get('SSE') is not None:
            args.append(constants.EMR_FS_BA_ARG_KEY)
            args.append(
                constants.EMR_FS_SSE_KEY + '=' +
                str(parsed_emr_fs.get('SSE')).lower())

        if parsed_emr_fs.get('RetryCount') is not None:
            args.append(constants.EMR_FS_BA_ARG_KEY)
            args.append(
                constants.EMR_FS_RETRY_COUNT_KEY + '=' +
                str(parsed_emr_fs.get('RetryCount')))

        if parsed_emr_fs.get('RetryPeriod') is not None:
            args.append(constants.EMR_FS_BA_ARG_KEY)
            args.append(
                constants.EMR_FS_RETRY_PERIOD_KEY + '=' +
                str(parsed_emr_fs.get('RetryPeriod')))

        if parsed_emr_fs.get('Args') is not None:
            for arg in parsed_emr_fs.get('Args'):
                args.append(constants.EMR_FS_BA_ARG_KEY)
                args.append(arg)

        return args
