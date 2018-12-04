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

from awscli.customizations.emr import emrutils
from awscli.customizations.emr import constants
from awscli.customizations.emr import exceptions


def build_step_config_list(parsed_step_list, region, release_label):
    step_config_list = []
    for step in parsed_step_list:
        step_type = step.get('Type')
        if step_type is None:
            step_type = constants.CUSTOM_JAR

        step_type = step_type.lower()
        step_config = {}
        if step_type == constants.CUSTOM_JAR:
            step_config = build_custom_jar_step(parsed_step=step)
        elif step_type == constants.STREAMING:
            step_config = build_streaming_step(
                parsed_step=step, release_label=release_label)
        elif step_type == constants.HIVE:
            step_config = build_hive_step(
                parsed_step=step, region=region,
                release_label=release_label)
        elif step_type == constants.PIG:
            step_config = build_pig_step(
                parsed_step=step, region=region,
                release_label=release_label)
        elif step_type == constants.IMPALA:
            step_config = build_impala_step(
                parsed_step=step, region=region,
                release_label=release_label)
        elif step_type == constants.SPARK:
            step_config = build_spark_step(
                parsed_step=step, region=region,
                release_label=release_label)
        else:
            raise exceptions.UnknownStepTypeError(step_type=step_type)

        step_config_list.append(step_config)

    return step_config_list


def build_custom_jar_step(parsed_step):
    name = _apply_default_value(
        arg=parsed_step.get('Name'),
        value=constants.DEFAULT_CUSTOM_JAR_STEP_NAME)
    action_on_failure = _apply_default_value(
        arg=parsed_step.get('ActionOnFailure'),
        value=constants.DEFAULT_FAILURE_ACTION)
    emrutils.check_required_field(
        structure=constants.CUSTOM_JAR_STEP_CONFIG,
        name='Jar',
        value=parsed_step.get('Jar'))
    return emrutils.build_step(
        jar=parsed_step.get('Jar'),
        args=parsed_step.get('Args'),
        name=name,
        action_on_failure=action_on_failure,
        main_class=parsed_step.get('MainClass'),
        properties=emrutils.parse_key_value_string(
            parsed_step.get('Properties')))


def build_streaming_step(parsed_step, release_label):
    name = _apply_default_value(
        arg=parsed_step.get('Name'),
        value=constants.DEFAULT_STREAMING_STEP_NAME)
    action_on_failure = _apply_default_value(
        arg=parsed_step.get('ActionOnFailure'),
        value=constants.DEFAULT_FAILURE_ACTION)

    args = parsed_step.get('Args')
    emrutils.check_required_field(
        structure=constants.STREAMING_STEP_CONFIG,
        name='Args',
        value=args)
    emrutils.check_empty_string_list(name='Args', value=args)
    args_list = []

    if release_label:
        jar = constants.COMMAND_RUNNER
        args_list.append(constants.HADOOP_STREAMING_COMMAND)
    else:
        jar = constants.HADOOP_STREAMING_PATH

    args_list += args

    return emrutils.build_step(
        jar=jar,
        args=args_list,
        name=name,
        action_on_failure=action_on_failure)


def build_hive_step(parsed_step, release_label, region=None):
    args = parsed_step.get('Args')
    emrutils.check_required_field(
        structure=constants.HIVE_STEP_CONFIG, name='Args', value=args)
    emrutils.check_empty_string_list(name='Args', value=args)
    name = _apply_default_value(
        arg=parsed_step.get('Name'),
        value=constants.DEFAULT_HIVE_STEP_NAME)
    action_on_failure = \
        _apply_default_value(
            arg=parsed_step.get('ActionOnFailure'),
            value=constants.DEFAULT_FAILURE_ACTION)

    return emrutils.build_step(
        jar=_get_runner_jar(release_label, region),
        args=_build_hive_args(args, release_label, region),
        name=name,
        action_on_failure=action_on_failure)


def _build_hive_args(args, release_label, region):
    args_list = []
    if release_label:
        args_list.append(constants.HIVE_SCRIPT_COMMAND)
    else:
        args_list.append(emrutils.build_s3_link(
            relative_path=constants.HIVE_SCRIPT_PATH, region=region))

    args_list.append(constants.RUN_HIVE_SCRIPT)

    if not release_label:
        args_list.append(constants.HIVE_VERSIONS)
        args_list.append(constants.LATEST)

    args_list.append(constants.ARGS)
    args_list += args

    return args_list


def build_pig_step(parsed_step, release_label, region=None):
    args = parsed_step.get('Args')
    emrutils.check_required_field(
        structure=constants.PIG_STEP_CONFIG, name='Args', value=args)
    emrutils.check_empty_string_list(name='Args', value=args)
    name = _apply_default_value(
        arg=parsed_step.get('Name'),
        value=constants.DEFAULT_PIG_STEP_NAME)
    action_on_failure = _apply_default_value(
        arg=parsed_step.get('ActionOnFailure'),
        value=constants.DEFAULT_FAILURE_ACTION)

    return emrutils.build_step(
        jar=_get_runner_jar(release_label, region),
        args=_build_pig_args(args, release_label, region),
        name=name,
        action_on_failure=action_on_failure)


def _build_pig_args(args, release_label, region):
    args_list = []
    if release_label:
        args_list.append(constants.PIG_SCRIPT_COMMAND)
    else:
        args_list.append(emrutils.build_s3_link(
            relative_path=constants.PIG_SCRIPT_PATH, region=region))

    args_list.append(constants.RUN_PIG_SCRIPT)

    if not release_label:
        args_list.append(constants.PIG_VERSIONS)
        args_list.append(constants.LATEST)

    args_list.append(constants.ARGS)
    args_list += args

    return args_list


def build_impala_step(parsed_step, release_label, region=None):
    if release_label:
        raise exceptions.UnknownStepTypeError(step_type=constants.IMPALA)
    name = _apply_default_value(
        arg=parsed_step.get('Name'),
        value=constants.DEFAULT_IMPALA_STEP_NAME)
    action_on_failure = _apply_default_value(
        arg=parsed_step.get('ActionOnFailure'),
        value=constants.DEFAULT_FAILURE_ACTION)
    args_list = [
        emrutils.build_s3_link(
            relative_path=constants.IMPALA_INSTALL_PATH, region=region),
        constants.RUN_IMPALA_SCRIPT]
    args = parsed_step.get('Args')
    emrutils.check_required_field(
        structure=constants.IMPALA_STEP_CONFIG, name='Args', value=args)
    args_list += args

    return emrutils.build_step(
        jar=emrutils.get_script_runner(region),
        args=args_list,
        name=name,
        action_on_failure=action_on_failure)


def build_spark_step(parsed_step, release_label, region=None):
    name = _apply_default_value(
        arg=parsed_step.get('Name'),
        value=constants.DEFAULT_SPARK_STEP_NAME)
    action_on_failure = _apply_default_value(
        arg=parsed_step.get('ActionOnFailure'),
        value=constants.DEFAULT_FAILURE_ACTION)
    args = parsed_step.get('Args')
    emrutils.check_required_field(
        structure=constants.SPARK_STEP_CONFIG, name='Args', value=args)

    return emrutils.build_step(
        jar=_get_runner_jar(release_label, region),
        args=_build_spark_args(args, release_label, region),
        name=name,
        action_on_failure=action_on_failure)


def _build_spark_args(args, release_label, region):
    args_list = []
    if release_label:
        args_list.append(constants.SPARK_SUBMIT_COMMAND)
    else:
        args_list.append(constants.SPARK_SUBMIT_PATH)
    args_list += args

    return args_list


def _apply_default_value(arg, value):
    if arg is None:
        arg = value

    return arg


def _get_runner_jar(release_label, region):
    return constants.COMMAND_RUNNER if release_label \
        else emrutils.get_script_runner(region)
