# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/

# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import os
import sys
import botocore.session
import botocore.base
import botocore.operation
import botocore.credentials
from botocore import xform_name
from awscli import awscli_data_path


def return_choices(choices):
    print('\n'.join(choices))
    sys.exit(0)


def return_no_choices():
    sys.exit(0)


def complete_std_option_value(session, option_name, option_data, prefix=''):
    if option_name == '--region':
        regions = session.get_data('aws/_regions')
        l = [rn for rn in regions.keys() if rn.startswith(prefix)]
        return_choices(l)
    elif option_name == '--output':
        return_choices(option_data[option_name]['choices'])
    elif option_name == '--profile':
        return_choices(session.available_profiles())
    else:
        return_no_choices()


def complete_parameter_value(param_name, operation):
    return_no_choices()


def complete(cmdline, point):
    session = botocore.session.get_session()
    session.add_search_path(awscli_data_path)
    operation_map = {}
    service_name = None
    operation_name = None
    words = cmdline[0:point].split()
    current_word = words[-1]
    if len(words) >= 2:
        previous_word = words[-2]
    else:
        previous_word = None
    std_options = session.get_data('cli/options')
    service_names = session.get_data('aws/_services').keys()
    # First find all non-options words in command line
    non_options = [w for w in words if not w.startswith('-')]
    # Look for a service name in the non_options
    for w in non_options:
        if w in service_names:
            service_name = w
            break
    # If we found a service name, look for an operation name
    if service_name:
        data_path = 'aws/%s/operations' % service_name
        all_op_data = session.get_data(data_path)
        for op_data in all_op_data:
            operation_map[xform_name(op_data['name'], '-')] = op_data
        for w in non_options:
            if w in operation_map:
                operation_name = w
    # Are we trying to complete an option or option value?
    if current_word.startswith('-'):
        # Is the current word a completed standard option?
        if current_word in std_options:
            complete_std_option_value(session, current_word, std_options)
        all_options = std_options.keys()
        if operation_name:
            op_data = operation_map[operation_name]
            operation = botocore.operation.Operation(None, op_data)
            param_names = [p.cli_name for p in operation.params]
            # If the complete param name is there, we are trying
            # to complete the parameter value.
            if current_word in param_names:
                complete_parameter_value(current_word, operation)
            all_options.extend(param_names)
        # Perhaps it is a partially completed standard option or param.
        choices = [n for n in all_options if n.startswith(current_word)]
        if choices:
            return_choices(choices)
    if not service_name:
        # If it wasn't an option and we didn't find a service name
        # then we assume we need to try to complete the service name.
        # If the only thing they have typed in is 'aws', provide a
        # list of available service names.
        if current_word == 'aws':
            return_choices(service_names)
        # Otherwise, see if they have entered a partial service name
        l = [n for n in service_names if n.startswith(current_word)]
        if l:
            return_choices(l)
    if not operation_name:
        # If it wasn't an option and we already have a service name
        # specified, we assume they are trying to compete an operation
        # name.  If the current word is the service name, provide
        # a list of available operations.
        if current_word == service_name:
            return_choices(operation_map.keys())
        # Otherwise, see if they have entered a partial operation name
        op_names = operation_map.keys()
        l = [n for n in op_names if n.startswith(current_word)]
        if l:
            return_choices(l)
    if previous_word and previous_word in std_options:
        # Is the previous word a non-boolean standard option?
        opt_data = std_options[previous_word]
        if opt_data.get('action', '') != 'store_true':
            complete_std_option_value(session,
                                      previous_word,
                                      std_options,
                                      current_word)
    if service_name and operation_name:
        # Provide a list of available parameter names
        op_data = operation_map[operation_name]
        operation = botocore.operation.Operation(None, op_data)
        param_names = [p.cli_name for p in operation.params]
        return_choices(param_names)
    return_no_choices()

if __name__ == '__main__':
    if len(sys.argv) == 3:
        complete(sys.argv[1], int(sys.argv[2]))
    else:
        print('usage: %s <cmdline> <point>' % sys.argv[0])
