# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""
Utility functions to make it easier to work with customizations.

"""
def rename_argument(argument_table, existing_name, new_name):
    current = argument_table[existing_name]
    argument_table[new_name] = current
    current.name = new_name
    del argument_table[existing_name]


def rename_command(command_table, existing_name, new_name):
    current = command_table[existing_name]
    command_table[new_name] = current
    current.name = new_name
    del command_table[existing_name]


def validate_mutually_exclusive_handler(*groups):
    def _handler(parsed_args, **kwargs):
        return validate_mutually_exclusive(parsed_args, *groups)
    return _handler


def validate_mutually_exclusive(parsed_args, *groups):
    """Validate mututally exclusive groups in the parsed args."""
    args_dict = vars(parsed_args)
    all_args = set(arg for group in groups for arg in group)
    if not any(k in all_args for k in args_dict if args_dict[k] is not None):
        # If none of the specified args are in a mutually exclusive group
        # there is nothing left to validate.
        return
    current_group = None
    for key in [k for k in args_dict if args_dict[k] is not None]:
        key_group = _get_group_for_key(key, groups)
        if key_group is None:
            # If they key is not part of a mutex group, we can move on.
            continue
        if current_group is None:
            current_group = key_group
        elif not key_group == current_group:
            raise ValueError('The key "%s" cannot be specified when one '
                             'of the following keys are also specified: '
                             '%s' % (key, current_group))


def _get_group_for_key(key, groups):
    for group in groups:
        if key in group:
            return group
