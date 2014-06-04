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


def build_applications(parsed_applications, parsed_globals, ami_version=None):
    app_list = []
    step_list = []
    ba_list = []

    for app_config in parsed_applications:
        app_name = app_config['Name'].lower()

        if app_name in constants.MAPR_NAMES:
            app_list.append(
                build_supported_product(
                    app_config['Name'], app_config['Args']))
        elif app_name == constants.HIVE:
            hive_version = app_config.get('Version')
            if hive_version is None:
                hive_version = constants.LATEST
            step_list.append(
                emrutils.build_hive_install_step(
                    region=parsed_globals.region,
                    version=hive_version))
        elif app_name == constants.PIG:
            pig_version = app_config.get('Version')
            if pig_version is None:
                pig_version = constants.LATEST
            step_list.append(
                emrutils.build_pig_install_step(
                    region=parsed_globals.region,
                    version=pig_version))
        elif app_name == constants.GANGLIA:
            ba_list.append(
                build_ganglia_install_bootstrap_action(
                    region=parsed_globals.region))
        elif app_name == constants.HBASE:
            ba_list.append(
                build_hbase_install_bootstrap_action(
                    region=parsed_globals.region))
            if ami_version >= '3.0':
                step_list.append(
                    build_hbase_install_step(
                        constants.HBASE_PATH_HADOOP2_INSTALL_JAR))
            elif ami_version >= '2.1':
                step_list.append(
                    build_hbase_install_step(
                        constants.HBASE_PATH_HADOOP1_INSTALL_JAR))
            else:
                raise ValueError('aws: error: AMI version ' + ami_version +
                                 'is not compatible with HBase.')
        elif app_name == constants.IMPALA:
            ba_list.append(
                build_impala_install_bootstrap_action(
                    region=parsed_globals.region,
                    args=app_config.get('Args'),
                    version=app_config.get('Version')))
        else:
            raise exceptions.UnknownApplicationError(app_name=app_name)

    return app_list, ba_list, step_list


def build_supported_product(name, args):
    if args is None:
        args = []
    config = {'Name': name.lower(), 'Args': args}
    return config


def build_ganglia_install_bootstrap_action(region):
    return emrutils.build_bootstrap_action(
        name=constants.INSTALL_GANGLIA_NAME,
        path=emrutils.build_s3_link(
            relative_path=constants.GANGLIA_INSTALL_BA_PATH,
            region=region))


def build_hbase_install_bootstrap_action(region):
    return emrutils.build_bootstrap_action(
        name=constants.INSTALL_HBASE_NAME,
        path=emrutils.build_s3_link(
            relative_path=constants.HBASE_INSTALL_BA_PATH,
            region=region))


def build_hbase_install_step(jar):
    return emrutils.build_step(
        jar=jar,
        name=constants.START_HBASE_NAME,
        action_on_failure=constants.TERMINATE_CLUSTER,
        args=constants.HBASE_INSTALL_ARG)


def build_impala_install_bootstrap_action(region, version, args=None):
    if version is None:
        version = 'latest'
    args_list = [
        constants.BASE_PATH_ARG,
        emrutils.build_s3_link(region=region),
        constants.IMPALA_VERSION,
        version]
    if args is not None:
        args_list.append(constants.IMPALA_CONF)
        args_list += args
    return emrutils.build_bootstrap_action(
        name=constants.INSTALL_IMPALA_NAME,
        path=emrutils.build_s3_link(
            relative_path=constants.IMPALA_INSTALL_PATH,
            region=region),
        args=args_list)