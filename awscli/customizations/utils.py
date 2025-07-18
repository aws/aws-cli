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
import copy
import sys

from botocore.exceptions import ClientError
from awscli.utils import create_nested_client


def rename_argument(argument_table, existing_name, new_name):
    current = argument_table[existing_name]
    argument_table[new_name] = current
    current.name = new_name
    del argument_table[existing_name]


def _copy_argument(argument_table, current_name, copy_name):
    current = argument_table[current_name]
    copy_arg = copy.copy(current)
    copy_arg.name = copy_name
    argument_table[copy_name] = copy_arg
    return copy_arg


def make_hidden_alias(argument_table, existing_name, alias_name):
    """Create a hidden alias for an existing argument.

    This will copy an existing argument object in an arg table,
    and add a new entry to the arg table with a different name.
    The new argument will also be undocumented.

    This is needed if you want to check an existing argument,
    but you still need the other one to work for backwards
    compatibility reasons.

    """
    current = argument_table[existing_name]
    copy_arg = _copy_argument(argument_table, existing_name, alias_name)
    copy_arg._UNDOCUMENTED = True
    if current.required:
        # If the current argument is required, then
        # we'll mark both as not required, but
        # flag _DOCUMENT_AS_REQUIRED so our doc gen
        # knows to still document this argument as required.
        copy_arg.required = False
        current.required = False
        current._DOCUMENT_AS_REQUIRED = True


def rename_command(command_table, existing_name, new_name):
    current = command_table[existing_name]
    command_table[new_name] = current
    current.name = new_name
    del command_table[existing_name]


def alias_command(command_table, existing_name, new_name):
    """Moves an argument to a new name, keeping the old as a hidden alias.

    :type command_table: dict
    :param command_table: The full command table for the CLI or a service.

    :type existing_name: str
    :param existing_name: The current name of the command.

    :type new_name: str
    :param new_name: The new name for the command.
    """
    current = command_table[existing_name]
    _copy_argument(command_table, existing_name, new_name)
    current._UNDOCUMENTED = True


def make_hidden_command_alias(command_table, existing_name, alias_name):
    """Create a hidden alias for an exiting command.

    This will copy an existing command object in a command table and add a new
    entry to the command table with a different name. The new command will
    be undocumented.

    This is needed if you want to change an existing command, but you still
    need the old name to work for backwards compatibility reasons.

    :type command_table: dict
    :param command_table: The full command table for the CLI or a service.

    :type existing_name: str
    :param existing_name: The current name of the command.

    :type alias_name: str
    :param alias_name: The new name for the command.
    """
    new = _copy_argument(command_table, existing_name, alias_name)
    new._UNDOCUMENTED = True


def validate_mutually_exclusive_handler(*groups):
    def _handler(parsed_args, **kwargs):
        return validate_mutually_exclusive(parsed_args, *groups)
    return _handler


def validate_mutually_exclusive(parsed_args, *groups):
    """Validate mutually exclusive groups in the parsed args."""
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
                             '%s' % (key, ', '.join(current_group)))


def _get_group_for_key(key, groups):
    for group in groups:
        if key in group:
            return group


def s3_bucket_exists(s3_client, bucket_name):
    bucket_exists = True
    try:
        # See if the bucket exists by running a head bucket
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        # If a client error is thrown. Check that it was a 404 error.
        # If it was a 404 error, than the bucket does not exist.
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            bucket_exists = False
    return bucket_exists


def create_client_from_parsed_globals(session, service_name, parsed_globals,
                                      overrides=None):
    """Creates a service client, taking parsed_globals into account

    Any values specified in overrides will override the returned dict. Note
    that this override occurs after 'region' from parsed_globals has been
    translated into 'region_name' in the resulting dict.
    """
    client_args = {}
    if 'region' in parsed_globals:
        client_args['region_name'] = parsed_globals.region
    if 'endpoint_url' in parsed_globals:
        client_args['endpoint_url'] = parsed_globals.endpoint_url
    if 'verify_ssl' in parsed_globals:
        client_args['verify'] = parsed_globals.verify_ssl
    if overrides:
        client_args.update(overrides)
    return create_nested_client(session, service_name, **client_args)


def uni_print(statement, out_file=None):
    """
    This function is used to properly write unicode to a file, usually
    stdout or stdderr.  It ensures that the proper encoding is used if the
    statement is not a string type.
    """
    if out_file is None:
        out_file = sys.stdout
    try:
        # Otherwise we assume that out_file is a
        # text writer type that accepts str/unicode instead
        # of bytes.
        out_file.write(statement)
    except UnicodeEncodeError:
        # Some file like objects like cStringIO will
        # try to decode as ascii on python2.
        #
        # This can also fail if our encoding associated
        # with the text writer cannot encode the unicode
        # ``statement`` we've been given.  This commonly
        # happens on windows where we have some S3 key
        # previously encoded with utf-8 that can't be
        # encoded using whatever codepage the user has
        # configured in their console.
        #
        # At this point we've already failed to do what's
        # been requested.  We now try to make a best effort
        # attempt at printing the statement to the outfile.
        # We're using 'ascii' as the default because if the
        # stream doesn't give us any encoding information
        # we want to pick an encoding that has the highest
        # chance of printing successfully.
        new_encoding = getattr(out_file, 'encoding', 'ascii')
        # When the output of the aws command is being piped,
        # ``sys.stdout.encoding`` is ``None``.
        if new_encoding is None:
            new_encoding = 'ascii'
        new_statement = statement.encode(
            new_encoding, 'replace').decode(new_encoding)
        out_file.write(new_statement)
    out_file.flush()


def get_policy_arn_suffix(region):
    """Method to return region value as expected by policy arn"""
    region_string = region.lower()
    if region_string.startswith("cn-"):
        return "aws-cn"
    elif region_string.startswith("us-gov"):
        return "aws-us-gov"
    else:
        return "aws"
