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
def register_scalar_parser(event_handlers):
    event_handlers.register_first(
        'session-initialized', add_scalar_parsers)


def identity(x):
    return x


def add_scalar_parsers(session, **kwargs):
    factory = session.get_component('response_parser_factory')
    # For backwards compatibility reasons, we replace botocore's timestamp
    # parser (which parsers to a datetime.datetime object) with the identity
    # function which prints the date exactly the same as it comes across the
    # wire.  We will eventually add a config option that allows for a user to
    # have normalized datetime representation, but we can't change the default.
    factory.set_parser_defaults(
        blob_parser=identity,
        timestamp_parser=identity)
