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
from botocore.utils import parse_timestamp


def register_scalar_parser(event_handlers):
    event_handlers.register_first(
        'session-initialized', add_scalar_parsers)


def identity(x):
    return x


def iso_format(value):
    return parse_timestamp(value).isoformat()


def choose_default_parsers(timestamp_format):
    parsers = dict(blob_parser=identity)
    if timestamp_format == 'none':
        # For backwards compatibility reasons, we replace botocore's timestamp
        # parser (which parses to a datetime.datetime object) with the
        # identity function which prints the date exactly the same as it comes
        # across the wire.
        parsers['timestamp_parser'] = identity
    elif timestamp_format == 'iso8601':
        parsers['timestamp_parser'] = iso_format
    else:
        raise ValueError('Unknown cli_timestamp_format value: %s, valid values'
                         ' are "none" or "iso8601"' % timestamp_format)
    return parsers


def add_scalar_parsers(session, **kwargs):
    factory = session.get_component('response_parser_factory')
    timestamp_format = session.get_scoped_config().get('cli_timestamp_format',
                                                       'none')
    parser_defaults = choose_default_parsers(timestamp_format)
    factory.set_parser_defaults(**parser_defaults)
