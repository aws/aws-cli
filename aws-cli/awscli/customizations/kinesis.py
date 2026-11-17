# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


def register_kinesis_list_streams_pagination_backcompat(event_emitter):
    # The ListStreams previously used the ExclusiveStartStreamName parameter
    # for input tokens to pagination. This operation was then updated to
    # also allow for the typical NextToken input and output parameters. The
    # pagination model was also updated to use the NextToken field instead of
    # the ExclusiveStartStreamName field for input tokens. However, the
    # ExclusiveStartStreamName is still a valid parameter to control pagination
    # of this operation and is incompatible with the NextToken parameter. So,
    # the CLI needs to continue to treat the ExclusiveStartStreamName as if it
    # is a raw input token parameter to the API by disabling auto-pagination if
    # provided. Otherwise, if it was treated as a normal API parameter, errors
    # would be thrown when paginating across multiple pages since the parameter
    # is incompatible with the NextToken parameter.
    event_emitter.register(
        'building-argument-table.kinesis.list-streams',
        undocument_exclusive_start_stream_name,
    )
    event_emitter.register(
        'operation-args-parsed.kinesis.list-streams',
        disable_pagination_when_exclusive_start_stream_name_provided,
    )


def undocument_exclusive_start_stream_name(argument_table, **kwargs):
    argument_table['exclusive-start-stream-name']._UNDOCUMENTED = True


def disable_pagination_when_exclusive_start_stream_name_provided(
    parsed_args, parsed_globals, **kwargs
):
    if parsed_args.exclusive_start_stream_name is not None:
        parsed_globals.paginate = False
