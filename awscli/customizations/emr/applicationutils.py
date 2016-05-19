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
from awscli.customizations.emr import exceptions


def build_applications(region,
                       parsed_applications, ami_version=None):
    app_list = []
    step_list = []
    ba_list = []

    for app_config in parsed_applications:
        app_name = app_config['Name'].lower()

        if app_name == constants.HIVE:
            hive_version = constants.LATEST
            step_list.append(
                _build_install_hive_step(region=region))
            args = app_config.get('Args')
            if args is not None:
                hive_site_path = _find_matching_arg(
                    key=constants.HIVE_SITE_KEY, args_list=args)
                if hive_site_path is not None:
                    step_list.append(
                        _build_install_hive_site_step(
                            region=region,
                            hive_site_path=hive_site_path))
        elif app_name == constants.PIG:
            pig_version = constants.LATEST
            step_list.append(
                _build_pig_install_step(
                    region=region))
        elif app_name == constants.GANGLIA:
            ba_list.append(
                _build_ganglia_install_bootstrap_action(
                    region=region))
        elif app_name == constants.HBASE:
            ba_list.append(
                _build_hbase_install_bootstrap_action(
                    region=region))
            if ami_version >= '3.0':
                step_list.append(
                    _build_hbase_install_step(
                        constants.HBASE_PATH_HADOOP2_INSTALL_JAR))
            elif ami_version >= '2.1':
                step_list.append(
                    _build_hbase_install_step(
                        constants.HBASE_PATH_HADOOP1_INSTALL_JAR))
            else:
                raise ValueError('aws: error: AMI version ' + ami_version +
                                 'is not compatible with HBase.')
        elif app_name == constants.IMPALA:
            ba_list.append(
                _build_impala_install_bootstrap_action(
                    region=region,
                    args=app_config.get('Args')))
        else:
            app_list.append(
                _build_supported_product(
                    app_config['Name'], app_config.get('Args')))

    return app_list, ba_list, step_list


def _build_supported_product(name, args):
    if args is None:
        args = []
    config = {'Name': name.lower(), 'Args': args}
    return config


def _build_ganglia_install_bootstrap_action(region):
    return emrutils.build_bootstrap_action(
        name=constants.INSTALL_GANGLIA_NAME,
        path=emrutils.build_s3_link(
            relative_path=constants.GANGLIA_INSTALL_BA_PATH,
            region=region))


def _build_hbase_install_bootstrap_action(region):
    return emrutils.build_bootstrap_action(
        name=constants.INSTALL_HBASE_NAME,
        path=emrutils.build_s3_link(
            relative_path=constants.HBASE_INSTALL_BA_PATH,
            region=region))


def _build_hbase_install_step(jar):
    return emrutils.build_step(
        jar=jar,
        name=constants.START_HBASE_NAME,
        action_on_failure=constants.TERMINATE_CLUSTER,
        args=constants.HBASE_INSTALL_ARG)


def _build_impala_install_bootstrap_action(region, args=None):
    args_list = [
        constants.BASE_PATH_ARG,
        emrutils.build_s3_link(region=region),
        constants.IMPALA_VERSION,
        constants.LATEST]
    if args is not None:
        args_list.append(constants.IMPALA_CONF)
        args_list.append(','.join(args))
    return emrutils.build_bootstrap_action(
        name=constants.INSTALL_IMPALA_NAME,
        path=emrutils.build_s3_link(
            relative_path=constants.IMPALA_INSTALL_PATH,
            region=region),
        args=args_list)


def _build_install_hive_step(region,
                             action_on_failure=constants.TERMINATE_CLUSTER):
    step_args = [
        emrutils.build_s3_link(constants.HIVE_SCRIPT_PATH, region),
        constants.INSTALL_HIVE_ARG,
        constants.BASE_PATH_ARG,
        emrutils.build_s3_link(constants.HIVE_BASE_PATH, region),
        constants.HIVE_VERSIONS,
        constants.LATEST]
    step = emrutils.build_step(
        name=constants.INSTALL_HIVE_NAME,
        action_on_failure=action_on_failure,
        jar=emrutils.build_s3_link(constants.SCRIPT_RUNNER_PATH, region),
        args=step_args)
    return step


def _build_install_hive_site_step(region, hive_site_path,
                                  action_on_failure=constants.CANCEL_AND_WAIT):
    step_args = [
        emrutils.build_s3_link(constants.HIVE_SCRIPT_PATH, region),
        constants.BASE_PATH_ARG,
        emrutils.build_s3_link(constants.HIVE_BASE_PATH),
        constants.INSTALL_HIVE_SITE_ARG,
        hive_site_path,
        constants.HIVE_VERSIONS,
        constants.LATEST]
    step = emrutils.build_step(
        name=constants.INSTALL_HIVE_SITE_NAME,
        action_on_failure=action_on_failure,
        jar=emrutils.build_s3_link(constants.SCRIPT_RUNNER_PATH, region),
        args=step_args)
    return step


def _build_pig_install_step(region,
                            action_on_failure=constants.TERMINATE_CLUSTER):
    step_args = [
        emrutils.build_s3_link(constants.PIG_SCRIPT_PATH, region),
        constants.INSTALL_PIG_ARG,
        constants.BASE_PATH_ARG,
        emrutils.build_s3_link(constants.PIG_BASE_PATH, region),
        constants.PIG_VERSIONS,
        constants.LATEST]
    step = emrutils.build_step(
        name=constants.INSTALL_PIG_NAME,
        action_on_failure=action_on_failure,
        jar=emrutils.build_s3_link(constants.SCRIPT_RUNNER_PATH, region),
        args=step_args)
    return step


def _find_matching_arg(key, args_list):
    for arg in args_list:
        if key in arg:
            return arg

    return None
