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

import logging
import json
import os

from awscli.customizations.emr import constants
from awscli.customizations.emr import exceptions
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import WaiterError
from awscli.clidriver import CLIOperationCaller


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
        true_option, true_option_name, false_option, false_option_name):
    if true_option and false_option:
        error_message = \
            'aws: error: cannot use both ' + true_option_name + \
            ' and ' + false_option_name + ' options together.'
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
        jar, name='Step',
        action_on_failure=constants.DEFAULT_FAILURE_ACTION,
        args=None,
        main_class=None,
        properties=None):
    check_required_field(
        structure='HadoopJarStep', name='Jar', value=jar)

    step = {}
    apply_dict(step, 'Name', name)
    apply_dict(step, 'ActionOnFailure', action_on_failure)
    jar_config = {}
    jar_config['Jar'] = jar
    apply_dict(jar_config, 'Args', args)
    apply_dict(jar_config, 'MainClass', main_class)
    apply_dict(jar_config, 'Properties', properties)
    step['HadoopJarStep'] = jar_config

    return step


def build_bootstrap_action(
        path,
        name='Bootstrap Action',
        args=None):
    if path is None:
        raise exceptions.MissingParametersError(
            object_name='ScriptBootstrapActionConfig', missing='Path')
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
    return 's3://{0}.elasticmapreduce{1}'.format(region, relative_path)


def get_script_runner(region='us-east-1'):
    if region is None:
        region = 'us-east-1'
    return build_s3_link(
        relative_path=constants.SCRIPT_RUNNER_PATH, region=region)


def check_required_field(structure, name, value):
    if value is None:
        raise exceptions.MissingParametersError(
            object_name=structure, missing=name)


def call(session, operation_object, parameters, region_name=None,
         endpoint_url=None, verify=None):
        # We could get an error from get_endpoint() about not having
        # a region configured.  Before this happens we want to check
        # for credentials so we can give a good error message.
        if session.get_credentials() is None:
            raise NoCredentialsError()

        endpoint = operation_object.service.get_endpoint(
            region_name=region_name, endpoint_url=endpoint_url,
            verify=verify)
        LOG.debug('Calling ' + str(operation_object) + ' with endpoint: ' +
                  endpoint.host)
        return operation_object.call(endpoint, **parameters)


def get_example_file(command):
    return open('awscli/examples/emr/' + command + '.rst')


def dict_to_string(dict, indent=2):
    return json.dumps(dict, indent=indent)


def get_endpoint(service, parsed_globals):
    return service.get_endpoint(
        region_name=parsed_globals.region,
        endpoint_url=parsed_globals.endpoint_url,
        verify=parsed_globals.verify_ssl)


def _get_creation_date_time(instance):
    return instance['Status']['Timeline']['CreationDateTime']


def _find_most_recently_created(pages):
    """ Find instance which is most recently created. """
    most_recently_created = None
    for page in pages:
        for instance in page[1]['Instances']:
            if (not most_recently_created or
                    _get_creation_date_time(most_recently_created) <
                    _get_creation_date_time(instance)):
                most_recently_created = instance
    return most_recently_created


def get_cluster_state(session, parsed_globals, cluster_id):
    emr = session.get_service('emr')
    endpoint = get_endpoint(emr, parsed_globals)
    describe_cluster_op = emr.get_operation('DescribeCluster')
    http, data = describe_cluster_op.call(endpoint, ClusterId=cluster_id)
    return data['Cluster']['Status']['State']


def _find_master_instance(session, parsed_globals, cluster_id):
    """
    Find the most recently created master instance.
    If the master instance is not available yet,
     the method will return None.
    """
    emr = session.get_service('emr')
    endpoint = get_endpoint(emr, parsed_globals)
    operation_object = emr.get_operation('ListInstances')
    pages = operation_object.paginate(
        endpoint, ClusterId=cluster_id, InstanceGroupTypes=['MASTER'])
    return _find_most_recently_created(pages)


def find_master_public_dns(session, parsed_globals, cluster_id):
    """
    Returns the master_instance's 'PublicDnsName'.
    """
    master_instance = _find_master_instance(
        session, parsed_globals, cluster_id)
    if master_instance is None:
        return ""
    else:
        return master_instance.get('PublicDnsName')


def which(program):
    for path in os.environ["PATH"].split(os.pathsep):
        path = path.strip('"')
        exe_file = os.path.join(path, program)
        if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
            return exe_file

    return None


def call_and_display_response(session, operation_name, parameters,
                              parsed_globals):
        cli_operation_caller = CLIOperationCaller(session)
        cli_operation_caller.invoke(
            session.get_service('emr').get_operation(operation_name),
            parameters, parsed_globals)


def display_response(session, operation, result, parsed_globals):
        cli_operation_caller = CLIOperationCaller(session)
        # Calling a private method. Should be changed after the functionality
        # is moved outside CliOperationCaller.
        cli_operation_caller._display_response(operation, result,
                                               parsed_globals)
