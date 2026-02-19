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

import json
import logging
import os

from botocore.exceptions import NoCredentialsError

from awscli.clidriver import CLIOperationCaller
from awscli.customizations.emr import constants, exceptions

LOG = logging.getLogger(__name__)


def parse_tags(raw_tags_list):
    tags_dict_list = []
    if raw_tags_list:
        for tag in raw_tags_list:
            if tag.find('=') == -1:
                key, value = tag, ''
            else:
                key, value = tag.split('=', 1)
            tags_dict_list.append({'Key': key, 'Value': value})

    return tags_dict_list


def parse_key_value_string(key_value_string):
    # raw_key_value_string is a list of key value pairs separated by comma.
    # Examples: "k1=v1,k2='v  2',k3,k4"
    key_value_list = []
    if key_value_string is not None:
        raw_key_value_list = key_value_string.split(',')
        for kv in raw_key_value_list:
            if kv.find('=') == -1:
                key, value = kv, ''
            else:
                key, value = kv.split('=', 1)
            key_value_list.append({'Key': key, 'Value': value})
        return key_value_list
    else:
        return None


def apply_boolean_options(
    true_option, true_option_name, false_option, false_option_name
):
    if true_option and false_option:
        error_message = (
            'aws: error: cannot use both '
            + true_option_name
            + ' and '
            + false_option_name
            + ' options together.'
        )
        raise ValueError(error_message)
    elif true_option:
        return True
    else:
        return False


# Deprecate. Rename to apply_dict
def apply(params, key, value):
    if value:
        params[key] = value

    return params


def apply_dict(params, key, value):
    if value:
        params[key] = value

    return params


def apply_params(src_params, src_key, dest_params, dest_key):
    if src_key in src_params.keys() and src_params[src_key]:
        dest_params[dest_key] = src_params[src_key]

    return dest_params


def build_step(
    jar,
    name='Step',
    action_on_failure=constants.DEFAULT_FAILURE_ACTION,
    args=None,
    main_class=None,
    properties=None,
    log_uri=None,
    encryption_key_arn=None,
):
    check_required_field(structure='HadoopJarStep', name='Jar', value=jar)

    step = {}
    apply_dict(step, 'Name', name)
    apply_dict(step, 'ActionOnFailure', action_on_failure)
    jar_config = {}
    jar_config['Jar'] = jar
    apply_dict(jar_config, 'Args', args)
    apply_dict(jar_config, 'MainClass', main_class)
    apply_dict(jar_config, 'Properties', properties)
    step['HadoopJarStep'] = jar_config
    step_monitoring_config = {}
    s3_monitoring_configuration = {}
    apply_dict(s3_monitoring_configuration, 'LogUri', log_uri)
    apply_dict(
        s3_monitoring_configuration, 'EncryptionKeyArn', encryption_key_arn
    )
    if s3_monitoring_configuration:
        step_monitoring_config['S3MonitoringConfiguration'] = (
            s3_monitoring_configuration
        )
        step['StepMonitoringConfiguration'] = step_monitoring_config

    return step


def build_bootstrap_action(path, name='Bootstrap Action', args=None):
    if path is None:
        raise exceptions.MissingParametersError(
            object_name='ScriptBootstrapActionConfig', missing='Path'
        )
    ba_config = {}
    apply_dict(ba_config, 'Name', name)
    script_config = {}
    apply_dict(script_config, 'Args', args)
    script_config['Path'] = path
    apply_dict(ba_config, 'ScriptBootstrapAction', script_config)

    return ba_config


def build_s3_link(relative_path='', region='us-east-1'):
    if region is None:
        region = 'us-east-1'
    return f's3://{region}.elasticmapreduce{relative_path}'


def get_script_runner(region='us-east-1'):
    if region is None:
        region = 'us-east-1'
    return build_s3_link(
        relative_path=constants.SCRIPT_RUNNER_PATH, region=region
    )


def check_required_field(structure, name, value):
    if not value:
        raise exceptions.MissingParametersError(
            object_name=structure, missing=name
        )


def check_empty_string_list(name, value):
    if not value or (len(value) == 1 and value[0].strip() == ""):
        raise exceptions.EmptyListError(param=name)


def call(
    session,
    operation_name,
    parameters,
    region_name=None,
    endpoint_url=None,
    verify=None,
):
    # We could get an error from get_endpoint() about not having
    # a region configured.  Before this happens we want to check
    # for credentials so we can give a good error message.
    if session.get_credentials() is None:
        raise NoCredentialsError()

    client = session.create_client(
        'emr',
        region_name=region_name,
        endpoint_url=endpoint_url,
        verify=verify,
    )
    LOG.debug('Calling ' + str(operation_name))
    return getattr(client, operation_name)(**parameters)


def get_example_file(command):
    return open('awscli/examples/emr/' + command + '.rst')


def dict_to_string(dict, indent=2):
    return json.dumps(dict, indent=indent)


def get_client(session, parsed_globals):
    return session.create_client(
        'emr',
        region_name=get_region(session, parsed_globals),
        endpoint_url=parsed_globals.endpoint_url,
        verify=parsed_globals.verify_ssl,
    )


def get_cluster_state(session, parsed_globals, cluster_id):
    client = get_client(session, parsed_globals)
    data = client.describe_cluster(ClusterId=cluster_id)
    return data['Cluster']['Status']['State']


def find_master_dns(session, parsed_globals, cluster_id):
    """
    Returns the master_instance's 'PublicDnsName'.
    """
    client = get_client(session, parsed_globals)
    data = client.describe_cluster(ClusterId=cluster_id)
    return data['Cluster']['MasterPublicDnsName']


def which(program):
    for path in os.environ["PATH"].split(os.pathsep):
        path = path.strip('"')
        exe_file = os.path.join(path, program)
        if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
            return exe_file

    return None


def call_and_display_response(
    session, operation_name, parameters, parsed_globals
):
    cli_operation_caller = CLIOperationCaller(session)
    cli_operation_caller.invoke(
        'emr', operation_name, parameters, parsed_globals
    )


def display_response(session, operation_name, result, parsed_globals):
    cli_operation_caller = CLIOperationCaller(session)
    # Calling a private method. Should be changed after the functionality
    # is moved outside CliOperationCaller.
    cli_operation_caller._display_response(
        operation_name, result, parsed_globals
    )


def get_region(session, parsed_globals):
    region = parsed_globals.region
    if region is None:
        region = session.get_config_variable('region')
    return region


def join(values, separator=',', lastSeparator='and'):
    """
    Helper method to print a list of values
    [1,2,3] -> '1, 2 and 3'
    """
    values = [str(x) for x in values]
    if len(values) < 1:
        return ""
    elif len(values) == 1:
        return values[0]
    else:
        separator = '%s ' % separator
        return ' '.join(
            [separator.join(values[:-1]), lastSeparator, values[-1]]
        )


def split_to_key_value(string):
    if string.find('=') == -1:
        return string, ''
    else:
        return string.split('=', 1)


def get_cluster(cluster_id, session, region, endpoint_url, verify_ssl):
    describe_cluster_params = {'ClusterId': cluster_id}
    describe_cluster_response = call(
        session,
        'describe_cluster',
        describe_cluster_params,
        region,
        endpoint_url,
        verify_ssl,
    )

    if describe_cluster_response is not None:
        return describe_cluster_response.get('Cluster')


def get_release_label(cluster_id, session, region, endpoint_url, verify_ssl):
    cluster = get_cluster(
        cluster_id, session, region, endpoint_url, verify_ssl
    )
    if cluster is not None:
        return cluster.get('ReleaseLabel')
