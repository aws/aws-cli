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
"""Change the scalar response parsing behavior for the AWS CLI.

The underlying library used by botocore has some response parsing
behavior that we'd like to modify in the AWS CLI.  There are two:

    * Parsing binary content.
    * Parsing timestamps (dates)

For the first option we can't print binary content to the terminal,
so this customization leaves the binary content base64 encoded.  If the
user wants the binary content, they can then base64 decode the appropriate
fields as needed.

There's nothing currently done for timestamps, but this will change
in the future.

"""
import sys

from botocore.utils import parse_timestamp
from botocore.exceptions import ProfileNotFound

from awscli.customizations.utils import uni_print
from awscli.utils import resolve_v2_debug_mode


def register_scalar_parser(event_handlers):
    event_handlers.register_first(
        'session-initialized', add_scalar_parsers)


def identity(x):
    return x


def iso_format(value):
    return parse_timestamp(value).isoformat()


def add_timestamp_parser(session, v2_debug=False):
    factory = session.get_component('response_parser_factory')
    print_v2_debug_warnings = v2_debug
    try:
        timestamp_format = session.get_scoped_config().get(
            'cli_timestamp_format',
            None)
        if timestamp_format is not None:
            # We do not want to print v2 debug warnings if the user explicitly
            # configured the cli_timestamp_format, they would not be
            # broken in that case.
            print_v2_debug_warnings = False
        else:
            timestamp_format = 'wire'
    except ProfileNotFound:
        # If a --profile is provided that does not exist, loading
        # a value from get_scoped_config will crash the CLI.
        # This function can be called as the first handler for
        # the session-initialized event, which happens before a
        # profile can be created, even if the command would have
        # successfully created a profile. Instead of crashing here
        # on a ProfileNotFound the CLI should just use 'wire'.
        timestamp_format = 'wire'
    # We also support 'none' for backwards compatibility reasons, though we
    # document 'wire' instead.
    if timestamp_format == 'wire' or timestamp_format == 'none':
        # For backwards compatibility reasons, we replace botocore's timestamp
        # parser (which parses to a datetime.datetime object) with the
        # identity function which prints the date exactly the same as it comes
        # across the wire.
        encountered_timestamp = False
        def identity_with_warning(x):
            # To prevent printing the same warning for each timestamp in the
            # response, we utilize a reference to a nonlocal variable to track
            # if we have already printed the warning.
            nonlocal encountered_timestamp
            if not encountered_timestamp:
                encountered_timestamp = True
                uni_print(
                    '\nAWS CLI v2 UPGRADE WARNING: In AWS CLI v2, all '
                    'timestamp response values are returned in the ISO 8601 '
                    'format. This is different from v1 behavior, where the '
                    'timestamps are returned as they appear in the service '
                    'API response. To retain AWS CLI v1 behavior in AWS CLI '
                    'v2, set the configuration variable '
                    '`cli_timestamp_format` to `wire`. See '
                    'https://docs.aws.amazon.com/cli/latest/userguide/'
                    'cliv2-migration-changes.html'
                    '#cliv2-migration-timestamp.\n',
                    out_file=sys.stderr
                )
            return identity(x)

        timestamp_parser = identity_with_warning \
            if print_v2_debug_warnings else identity
    elif timestamp_format == 'iso8601':
        timestamp_parser = iso_format
    else:
        raise ValueError('Unknown cli_timestamp_format value: %s, valid values'
                         ' are "none", "wire" or "iso8601"' % timestamp_format)
    factory.set_parser_defaults(timestamp_parser=timestamp_parser)


def add_scalar_parsers(session, parsed_args=None, **kwargs):
    factory = session.get_component('response_parser_factory')
    factory.set_parser_defaults(blob_parser=identity)
    add_timestamp_parser(session, resolve_v2_debug_mode(parsed_args))
