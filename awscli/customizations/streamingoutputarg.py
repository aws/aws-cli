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
from awscli.clidriver import BaseCLIArgument

def add_streaming_output_arg(argument_table, operation, **kwargs):
    stream_param = operation.is_streaming()
    if stream_param:
        argument_table['output-file'] = StreamingOutputArgument(
            stream_param, operation)


class StreamingOutputArgument(BaseCLIArgument):
    
    BUFFER_SIZE = 32768
    HELP = 'Filename where the content will be saved'

    def __init__(self, name, argument_object, buffer_size=None):
        super(StreamingOutputArgument, self).__init__(name, argument_object)
        if buffer_size is None:
            buffer_size = self.BUFFER_SIZE
        self._buffer_size = buffer_size
        self._output_file = None

    @property
    def cli_type_name(self):
        return 'file'
    
    @property
    def required(self):
        return True

    @property
    def documentation(self):
        return self.HELP

    def add_to_parser(self, parser, cli_name=None):
        parser.add_argument(self._name, metavar='output_file',
                            help=self.HELP)

    def add_to_params(self, parameters, value):
        self._output_file = value
        service_name = self.argument_object.service.endpoint_prefix
        operation_name = self.argument_object.name
        self._operation.session.register('after-call.%s.%s' % (
            service_name, operation_name), self.save_file)

    def save_file(self, http_response, parsed, **kwargs):
        body = parsed[self._name]
        buffer_size = self._buffer_size
        with open(self._output_file, 'wb') as fp:
            data = body.read(buffer_size)
            while data:
                fp.write(data)
                data = body.read(buffer_size)
        # We don't want to include the streaming param in
        # the returned response.
        del parsed[self._name]
