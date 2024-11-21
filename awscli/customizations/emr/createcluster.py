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

import re
from awscli.customizations.commands import BasicCommand
from awscli.customizations.emr import applicationutils
from awscli.customizations.emr import argumentschema
from awscli.customizations.emr import constants
from awscli.customizations.emr import emrfsutils
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import exceptions
from awscli.customizations.emr import hbaseutils
from awscli.customizations.emr import helptext
from awscli.customizations.emr import instancegroupsutils
from awscli.customizations.emr import instancefleetsutils
from awscli.customizations.emr import steputils
from awscli.customizations.emr.command import Command
from awscli.customizations.emr.constants import EC2_ROLE_NAME
from awscli.customizations.emr.constants import EMR_ROLE_NAME
from botocore.compat import json


class CreateCluster(Command):
    NAME = 'create-cluster'
    DESCRIPTION = helptext.CREATE_CLUSTER_DESCRIPTION
    ARG_TABLE = [
        {'name': 'release-label',
         'help_text': helptext.RELEASE_LABEL},
        {'name': 'os-release-label',
         'help_text': helptext.OS_RELEASE_LABEL},
        {'name': 'ami-version',
         'help_text': helptext.AMI_VERSION},
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
        {'name': 'instance-fleets',
         'schema': argumentschema.INSTANCE_FLEETS_SCHEMA,
         'help_text': helptext.INSTANCE_FLEETS},
        {'name': 'name',
         'default': 'Development Cluster',
         'help_text': helptext.CLUSTER_NAME},
        {'name': 'log-uri',
         'help_text': helptext.LOG_URI},
        {'name': 'log-encryption-kms-key-id',
         'help_text': helptext.LOG_ENCRYPTION_KMS_KEY_ID},
        {'name': 'service-role',
         'help_text': helptext.SERVICE_ROLE},
        {'name': 'auto-scaling-role',
         'help_text': helptext.AUTOSCALING_ROLE},
        {'name': 'use-default-roles', 'action': 'store_true',
         'help_text': helptext.USE_DEFAULT_ROLES},
        {'name': 'configurations',
         'help_text': helptext.CONFIGURATIONS},
        {'name': 'ec2-attributes',
         'help_text': helptext.EC2_ATTRIBUTES,
         'schema': argumentschema.EC2_ATTRIBUTES_SCHEMA},
        {'name': 'termination-protected', 'action': 'store_true',
         'group_name': 'termination_protected',
         'help_text': helptext.TERMINATION_PROTECTED},
        {'name': 'no-termination-protected', 'action': 'store_true',
         'group_name': 'termination_protected'},
        {'name': 'unhealthy-node-replacement', 'action': 'store_true',
        'group_name': 'unhealthy_node_replacement',
        'help_text': helptext.UNHEALTHY_NODE_REPLACEMENT},
        {'name': 'no-unhealthy-node-replacement', 'action': 'store_true',
        'group_name': 'unhealthy_node_replacement'},
        {'name': 'scale-down-behavior',
         'help_text': helptext.SCALE_DOWN_BEHAVIOR},
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
         'help_text': helptext.RESTORE_FROM_HBASE},
        {'name': 'security-configuration',
         'help_text': helptext.SECURITY_CONFIG},
        {'name': 'custom-ami-id',
         'help_text' : helptext.CUSTOM_AMI_ID},
        {'name': 'ebs-root-volume-size',
         'help_text' : helptext.EBS_ROOT_VOLUME_SIZE},
        {'name': 'ebs-root-volume-iops',
         'help_text' : helptext.EBS_ROOT_VOLUME_IOPS},
        {'name': 'ebs-root-volume-throughput',
         'help_text' : helptext.EBS_ROOT_VOLUME_THROUGHPUT},
        {'name': 'repo-upgrade-on-boot',
         'help_text' : helptext.REPO_UPGRADE_ON_BOOT},
        {'name': 'kerberos-attributes',
         'schema': argumentschema.KERBEROS_ATTRIBUTES_SCHEMA,
         'help_text': helptext.KERBEROS_ATTRIBUTES},
        {'name': 'step-concurrency-level',
         'cli_type_name': 'integer',
         'help_text': helptext.STEP_CONCURRENCY_LEVEL},
        {'name': 'managed-scaling-policy',
         'schema': argumentschema.MANAGED_SCALING_POLICY_SCHEMA,
         'help_text': helptext.MANAGED_SCALING_POLICY},
        {'name': 'placement-group-configs',
         'schema': argumentschema.PLACEMENT_GROUP_CONFIGS_SCHEMA,
         'help_text': helptext.PLACEMENT_GROUP_CONFIGS},
        {'name': 'auto-termination-policy',
         'schema': argumentschema.AUTO_TERMINATION_POLICY_SCHEMA,
         'help_text': helptext.AUTO_TERMINATION_POLICY}
    ]
    SYNOPSIS = BasicCommand.FROM_FILE('emr', 'create-cluster-synopsis.txt')
    EXAMPLES = BasicCommand.FROM_FILE('emr', 'create-cluster-examples.rst')

    def _run_main_command(self, parsed_args, parsed_globals):
        params = {}
        params['Name'] = parsed_args.name

        self._validate_release_label_ami_version(parsed_args)

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

        if parsed_args.instance_groups is not None and \
                parsed_args.instance_fleets is not None:
            raise exceptions.MutualExclusiveOptionError(
                option1="--instance-groups",
                option2="--instance-fleets")

        instances_config = {}
        if parsed_args.instance_fleets is not None:
            instances_config['InstanceFleets'] = \
                instancefleetsutils.validate_and_build_instance_fleets(
                    parsed_args.instance_fleets)
        else:
            instances_config['InstanceGroups'] = \
                instancegroupsutils.validate_and_build_instance_groups(
                    instance_groups=parsed_args.instance_groups,
                    instance_type=parsed_args.instance_type,
                    instance_count=parsed_args.instance_count)

        if parsed_args.release_label is not None:
            params["ReleaseLabel"] = parsed_args.release_label
            if parsed_args.configurations is not None:
                try:
                    params["Configurations"] = json.loads(
                        parsed_args.configurations)
                except ValueError:
                    raise ValueError('aws: error: invalid json argument for '
                                     'option --configurations')

        if (
            parsed_args.release_label is None
            and parsed_args.ami_version is not None
        ):
            is_valid_ami_version = re.match(r'\d?\..*', parsed_args.ami_version)
            if is_valid_ami_version is None:
                raise exceptions.InvalidAmiVersionError(
                    ami_version=parsed_args.ami_version)
            params['AmiVersion'] = parsed_args.ami_version
        emrutils.apply_dict(
            params, 'AdditionalInfo', parsed_args.additional_info)
        emrutils.apply_dict(params, 'LogUri', parsed_args.log_uri)

        if parsed_args.os_release_label is not None:
            emrutils.apply_dict(params, 'OSReleaseLabel',
                parsed_args.os_release_label)

        if parsed_args.log_encryption_kms_key_id is not None:
            emrutils.apply_dict(params, 'LogEncryptionKmsKeyId',
                parsed_args.log_encryption_kms_key_id)

        if parsed_args.use_default_roles is True:
            parsed_args.service_role = EMR_ROLE_NAME
            if parsed_args.ec2_attributes is None:
                parsed_args.ec2_attributes = {}
            parsed_args.ec2_attributes['InstanceProfile'] = EC2_ROLE_NAME

        emrutils.apply_dict(params, 'ServiceRole', parsed_args.service_role)

        if parsed_args.instance_groups is not None:
            for instance_group in instances_config['InstanceGroups']:
                if 'AutoScalingPolicy' in instance_group.keys():
                    if parsed_args.auto_scaling_role is None:
                        raise exceptions.MissingAutoScalingRoleError()

        emrutils.apply_dict(params, 'AutoScalingRole', parsed_args.auto_scaling_role)

        if parsed_args.scale_down_behavior is not None:
            emrutils.apply_dict(params, 'ScaleDownBehavior', parsed_args.scale_down_behavior)

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
        
        if (parsed_args.unhealthy_node_replacement or parsed_args.no_unhealthy_node_replacement):
            instances_config['UnhealthyNodeReplacement'] = \
            emrutils.apply_boolean_options(
                parsed_args.unhealthy_node_replacement,
                '--unhealthy-node-replacement',
                parsed_args.no_unhealthy_node_replacement,
                '--no-unhealthy-node-replacement')

        if (parsed_args.visible_to_all_users is False and
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
                value=[
                    self._build_enable_debugging(parsed_args, parsed_globals)])

        if parsed_args.applications is not None:
            if parsed_args.release_label is None:
                app_list, ba_list, step_list = \
                    applicationutils.build_applications(
                        region=self.region,
                        parsed_applications=parsed_args.applications,
                        ami_version=params['AmiVersion'])
                self._update_cluster_dict(
                    params, 'NewSupportedProducts', app_list)
                self._update_cluster_dict(
                    params, 'BootstrapActions', ba_list)
                self._update_cluster_dict(
                    params, 'Steps', step_list)
            else:
                params["Applications"] = []
                for application in parsed_args.applications:
                    params["Applications"].append(application)

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
            self._handle_emrfs_parameters(
                cluster=params,
                emrfs_args=parsed_args.emrfs,
                release_label=parsed_args.release_label)

        if parsed_args.steps is not None:
            steps_list = steputils.build_step_config_list(
                parsed_step_list=parsed_args.steps,
                region=self.region,
                release_label=parsed_args.release_label)
            self._update_cluster_dict(
                cluster=params, key='Steps', value=steps_list)

        if parsed_args.security_configuration is not None:
            emrutils.apply_dict(
                params, 'SecurityConfiguration', parsed_args.security_configuration)

        if parsed_args.custom_ami_id is not None:
            emrutils.apply_dict(
                params, 'CustomAmiId', parsed_args.custom_ami_id
            )
        if parsed_args.ebs_root_volume_size is not None:
            emrutils.apply_dict(
                params, 'EbsRootVolumeSize', int(parsed_args.ebs_root_volume_size)
            )
        if parsed_args.ebs_root_volume_iops is not None:
            emrutils.apply_dict(
                params, 'EbsRootVolumeIops', int(parsed_args.ebs_root_volume_iops)
            )
        if parsed_args.ebs_root_volume_throughput is not None:
            emrutils.apply_dict(
                params, 'EbsRootVolumeThroughput', int(parsed_args.ebs_root_volume_throughput)
            )

        if parsed_args.repo_upgrade_on_boot is not None:
            emrutils.apply_dict(
                params, 'RepoUpgradeOnBoot', parsed_args.repo_upgrade_on_boot
            )

        if parsed_args.kerberos_attributes is not None:
            emrutils.apply_dict(
                params, 'KerberosAttributes', parsed_args.kerberos_attributes)

        if parsed_args.step_concurrency_level is not None:
            params['StepConcurrencyLevel'] = parsed_args.step_concurrency_level

        if parsed_args.managed_scaling_policy is not None:
            emrutils.apply_dict(
                params, 'ManagedScalingPolicy', parsed_args.managed_scaling_policy)

        if parsed_args.placement_group_configs is not None:
            emrutils.apply_dict(
                params, 'PlacementGroupConfigs',
                parsed_args.placement_group_configs)

        if parsed_args.auto_termination_policy is not None:
            emrutils.apply_dict(
                params, 'AutoTerminationPolicy',
                parsed_args.auto_termination_policy)

        self._validate_required_applications(parsed_args)

        run_job_flow_response = emrutils.call(
            self._session, 'run_job_flow', params, self.region,
            parsed_globals.endpoint_url, parsed_globals.verify_ssl)

        constructed_result = self._construct_result(run_job_flow_response)
        emrutils.display_response(self._session, 'run_job_flow',
                                  constructed_result, parsed_globals)

        return 0

    def _construct_result(self, run_job_flow_result):
        jobFlowId = None
        clusterArn = None
        if run_job_flow_result is not None:
            jobFlowId = run_job_flow_result.get('JobFlowId')
            clusterArn = run_job_flow_result.get('ClusterArn')

        if jobFlowId is not None:
            return {'ClusterId': jobFlowId,
                    'ClusterArn': clusterArn }
        else:
            return {}

    def _build_ec2_attributes(self, cluster, parsed_attrs):
        keys = parsed_attrs.keys()
        instances = cluster['Instances']

        if ('SubnetId' in keys and 'SubnetIds' in keys):
            raise exceptions.MutualExclusiveOptionError(
                option1="SubnetId",
                option2="SubnetIds")

        if ('AvailabilityZone' in keys and 'AvailabilityZones' in keys):
            raise exceptions.MutualExclusiveOptionError(
                option1="AvailabilityZone",
                option2="AvailabilityZones")

        if ('SubnetId' in keys or 'SubnetIds' in keys) \
                and ('AvailabilityZone' in keys or 'AvailabilityZones' in keys):
            raise exceptions.SubnetAndAzValidationError

        emrutils.apply_params(
            src_params=parsed_attrs, src_key='KeyName',
            dest_params=instances, dest_key='Ec2KeyName')
        emrutils.apply_params(
            src_params=parsed_attrs, src_key='SubnetId',
            dest_params=instances, dest_key='Ec2SubnetId')
        emrutils.apply_params(
            src_params=parsed_attrs, src_key='SubnetIds',
            dest_params=instances, dest_key='Ec2SubnetIds')

        if 'AvailabilityZone' in keys:
            instances['Placement'] = dict()
            emrutils.apply_params(
                src_params=parsed_attrs, src_key='AvailabilityZone',
                dest_params=instances['Placement'],
                dest_key='AvailabilityZone')

        if 'AvailabilityZones' in keys:
            instances['Placement'] = dict()
            emrutils.apply_params(
                src_params=parsed_attrs, src_key='AvailabilityZones',
                dest_params=instances['Placement'],
                dest_key='AvailabilityZones')

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
            src_params=parsed_attrs, src_key='ServiceAccessSecurityGroup',
            dest_params=instances, dest_key='ServiceAccessSecurityGroup')

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
        if result:
            cluster['BootstrapActions'] = result

        return cluster

    def _build_enable_debugging(self, parsed_args, parsed_globals):
        if parsed_args.release_label:
            jar = constants.COMMAND_RUNNER
            args = [constants.DEBUGGING_COMMAND]
        else:
            jar = emrutils.get_script_runner(self.region)
            args = [emrutils.build_s3_link(
                relative_path=constants.DEBUGGING_PATH,
                region=self.region)]

        return emrutils.build_step(
            name=constants.DEBUGGING_NAME,
            action_on_failure=constants.TERMINATE_CLUSTER,
            jar=jar,
            args=args)

    def _update_cluster_dict(self, cluster, key, value):
        if key in cluster:
            cluster[key] += value
        elif value:
            cluster[key] = value
        return cluster

    def _validate_release_label_ami_version(self, parsed_args):
        if parsed_args.ami_version is not None and \
                parsed_args.release_label is not None:
            raise exceptions.MutualExclusiveOptionError(
                option1="--ami-version",
                option2="--release-label")

        if parsed_args.ami_version is None and \
                parsed_args.release_label is None:
            raise exceptions.RequiredOptionsError(
                option1="--ami-version",
                option2="--release-label")

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

        if missing_apps:
            raise exceptions.MissingApplicationsError(
                applications=missing_apps)

    def _get_missing_applications_for_steps(self, specified_apps, parsed_args):
        allowed_app_steps = set([constants.HIVE, constants.PIG,
                                 constants.IMPALA])
        missing_apps = set()
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

    def _filter_configurations_in_special_cases(self, configurations,
                                                parsed_args, parsed_configs):
        if parsed_args.use_default_roles:
            configurations = [x for x in configurations
                              if x.name != 'service_role' and
                              x.name != 'instance_profile']
        return configurations

    def _handle_emrfs_parameters(self, cluster, emrfs_args, release_label):
        if release_label:
            self.validate_no_emrfs_configuration(cluster)
            emrfs_configuration = emrfsutils.build_emrfs_confiuration(
                emrfs_args)

            self._update_cluster_dict(
                cluster=cluster, key='Configurations',
                value=[emrfs_configuration])
        else:
            emrfs_ba_config_list = emrfsutils.build_bootstrap_action_configs(
                self.region, emrfs_args)
            self._update_cluster_dict(
                cluster=cluster, key='BootstrapActions',
                value=emrfs_ba_config_list)

    def validate_no_emrfs_configuration(self, cluster):
        if 'Configurations' in cluster:
            for config in cluster['Configurations']:
                if config is not None and \
                        config.get('Classification') == constants.EMRFS_SITE:
                    raise exceptions.DuplicateEmrFsConfigurationError
