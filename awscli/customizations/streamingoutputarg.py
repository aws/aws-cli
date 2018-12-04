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
from botocore.model import Shape

from awscli.arguments import BaseCLIArgument


def add_streaming_output_arg(argument_table, operation_model,
                             session, **kwargs):
    # Implementation detail:  hooked up to 'building-argument-table'
    # event.
    if _has_streaming_output(operation_model):
        streaming_argument_name = _get_streaming_argument_name(operation_model)
        argument_table['outfile'] = StreamingOutputArgument(
            response_key=streaming_argument_name,
            operation_model=operation_model,
            session=session, name='outfile')


def _has_streaming_output(model):
    return model.has_streaming_output


def _get_streaming_argument_name(model):
    return model.output_shape.serialization['payload']


class StreamingOutputArgument(BaseCLIArgument):

    BUFFER_SIZE = 32768
    HELP = 'Filename where the content will be saved'

    def __init__(self, response_key, operation_model, name,
                 session, buffer_size=None):
        self._name = name
        self.argument_model = Shape('StreamingOutputArgument',
                                    {'type': 'string'})
        if buffer_size is None:
            buffer_size = self.BUFFER_SIZE
        self._buffer_size = buffer_size
        # This is the key in the response body where we can find the
        # streamed contents.
        self._response_key = response_key
        self._output_file = None
        self._name = name
        self._required = True
        self._operation_model = operation_model
        self._session = session

    @property
    def cli_name(self):
        # Because this is a parameter, not an option, it shouldn't have the
        # '--' prefix. We want to use the self.py_name to indicate that it's an
        # argument.
        return self._name

    @property
    def cli_type_name(self):
        return 'string'

    @property
    def required(self):
        return self._required

    @required.setter
    def required(self, value):
        self._required = value

    @property
    def documentation(self):
        return self.HELP

    def add_to_parser(self, parser):
        parser.add_argument(self._name, metavar=self.py_name,
                            help=self.HELP)

    def add_to_params(self, parameters, value):
        self._output_file = value
        service_name = self._operation_model.service_model.endpoint_prefix
        operation_name = self._operation_model.name
        self._session.register('after-call.%s.%s' % (
            service_name, operation_name), self.save_file)

    def save_file(self, parsed, **kwargs):
        if self._response_key not in parsed:
            # If the response key is not in parsed, then
            # we've received an error message and we'll let the AWS CLI
            # error handler print out an error message.  We have no
            # file to save in this situation.
            return
        body = parsed[self._response_key]
        buffer_size = self._buffer_size
        with open(self._output_file, 'wb') as fp:
            data = body.read(buffer_size)
            while data:
                fp.write(data)
                data = body.read(buffer_size)
        # We don't want to include the streaming param in
        # the returned response.
        del parsed[self._response_key]
