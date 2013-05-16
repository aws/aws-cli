# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import sys
import os
import traceback
import json
import six
import botocore.session
from botocore.hooks import first_non_none_response
from botocore.hooks import HierarchicalEmitter
from awscli import EnvironmentVariables, __version__
from .formatter import get_formatter
from .paramfile import get_paramfile
from .plugin import load_plugins
from .argparser import MainArgParser, ServiceArgParser, OperationArgParser


def main():
    emitter = HierarchicalEmitter()
    session = botocore.session.Session(EnvironmentVariables, emitter)
    load_plugins(session.full_config.get('plugins', {}),
                 event_hooks=emitter)
    driver = CLIDriver(session=session)
    return driver.main()


class CLIDriver(object):

    def __init__(self, session=None):
        if session is None:
            self.session = botocore.session.get_session(EnvironmentVariables)
            self.session.user_agent_name = 'aws-cli'
            self.session.user_agent_version = __version__
        else:
            self.session = session
        self.service = None
        self.region = None
        self.endpoint = None
        self.operation = None
        self.main_parser = None
        self.service_parser = None
        self.operation_parser = None

    def create_main_parser(self):
        """
        Create the main parser to handle the global arguments.

        :rtype: ``argparser.ArgumentParser``
        :return: The parser object

        """
        self.main_parser = MainArgParser(self.session)
        self.session.emit('parser-created.main', parser=self.main_parser)

    def create_service_parser(self):
        """
        Create the subparser to handle the Service arguments.
        """
        prog = '%s %s' % (self.main_parser.prog,
                          self.service.cli_name)
        self.service_parser = ServiceArgParser(self.session,
                                               self.service,
                                               prog=prog)
        self.session.emit('parser-created.%s' % self.service.cli_name,
                           parser=self.service_parser)

    def create_operation_parser(self):
        """
        Create the subparser to handle the Operation arguments.
        """
        prog = '%s %s %s' % (self.main_parser.prog,
                             self.service.cli_name,
                             self.operation.cli_name)
        self.operation_parser = OperationArgParser(self.session,
                                                   self.service,
                                                   self.operation,
                                                   prog=prog)
        self.session.emit('parser-created.%s-%s' % (self.service.cli_name,
                                                     self.operation.cli_name))
        return 1

    def _unpack_cli_arg(self, param, s):
        """
        Parses and unpacks the encoded string command line parameter
        and returns native Python data structures that can be passed
        to the Operation.
        """
        if param.type == 'integer':
            return int(s)
        elif param.type == 'float' or param.type == 'double':
            # TODO: losing precision on double types
            return float(s)
        elif param.type == 'structure' or param.type == 'map':
            if s[0] == '{':
                d = json.loads(s)
            else:
                msg = 'Structure option value must be JSON or path to file.'
                raise ValueError(msg)
            return d
        elif param.type == 'list':
            if isinstance(s, six.string_types):
                if s[0] == '[':
                    return json.loads(s)
            elif isinstance(s, list) and len(s) == 1:
                if s[0][0] == '[':
                    return json.loads(s[0])
            return [self._unpack_cli_arg(param.members, v) for v in s]
        elif param.type == 'blob' and param.payload and param.streaming:
            file_path = os.path.expandvars(s)
            file_path = os.path.expanduser(file_path)
            if not os.path.isfile(file_path):
                msg = 'Blob values must be a path to a file.'
                raise ValueError(msg)
            return open(file_path, 'rb')
        else:
            return str(s)

    def _build_call_parameters(self, args, param_dict):
        service_name = self.service.cli_name
        operation_name = self.operation.cli_name
        for param in self.operation.params:
            value = getattr(args, param.py_name)
            if value is not None:
                # Plugins can override the cli -> python conversion
                # process for CLI args.
                responses = self.session.emit('process-cli-arg.%s.%s' % (
                    service_name, operation_name), param=param, value=value,
                    service=self.service, operation=self.operation)
                override = first_non_none_response(responses)
                if override is not None:
                    # A plugin supplied an alternate conversion,
                    # use it instead.
                    param_dict[param.py_name] = override
                    continue
                # Otherwise fall back to our normal built in cli -> python
                # conversion process.
                if param.type == 'boolean' and not param.required and \
                        value is False:
                    # Don't include non-required boolean params whose
                    # values are False
                    continue
                if not hasattr(param, 'no_paramfile'):
                    value = self._handle_param_file(value)
                param_dict[param.py_name] = self._unpack_cli_arg(param, value)

    def _handle_param_file(self, value):
        if isinstance(value, list) and len(value) == 1:
            temp = value[0]
        else:
            temp = value
        temp = get_paramfile(self.session, temp)
        if temp:
            value = temp
        return value

    def display_error_and_exit(self, ex):
        if self.main_parser.args.debug:
            traceback.print_exc()
        elif isinstance(ex, Exception):
            print(ex)
        elif self.main_parser.args.output != 'json':
            print(ex)
        return 1

    def get_error_code_and_message(self, response):
        code = 'Unknown'
        message = 'Unknown'
        if 'Errors' in response:
            if isinstance(response['Errors'], list):
                error = response['Errors'][-1]
                if 'Code' in error:
                    code = error['Code']
                elif 'Type' in error:
                    code = error['Type']
                if 'Message' in error:
                    message = error['Message']
        return (code, message)

    def save_output(self, body_name, response_data, path):
        buffsize = 32768
        with open(path, 'wb') as fp:
            data = response_data[body_name].read(buffsize)
            while data:
                fp.write(data)
                data = response_data[body_name].read(buffsize)
        del response_data[body_name]

    def _call(self, args):
        try:
            params = {}
            self._build_call_parameters(args, params)
            self.endpoint = self.service.get_endpoint(
                self.main_parser.args.region,
                endpoint_url=self.main_parser.args.endpoint_url)
            self.endpoint.verify = not self.main_parser.args.no_verify_ssl
            if self.operation.can_paginate and self.main_parser.args.paginate:
                pages = self.operation.paginate(self.endpoint, **params)
                self._display_response(self.operation, pages)
                # TODO: need to handle http error responses.  I believe
                # this will be addressed with the plugin refactoring,
                # but the other alternative is going to be that we'll need
                # to cache the fully buffered response.
                return 0
            else:
                http_response, response_data = self.operation.call(
                    self.endpoint, **params)
                streaming_param = self.operation.is_streaming()
                if streaming_param:
                    self.save_output(streaming_param, response_data,
                                     args.outfile)
                self._display_response(self.operation, response_data)
                return self._handle_http_response(http_response, response_data)
        except Exception as ex:
            return self.display_error_and_exit(ex)

    def _handle_http_response(self, http_response, response_data):
        if http_response.status_code >= 500:
            msg = self.session.get_data('messages/ServerError')
            code, message = self.get_error_code_and_message(response_data)
            sys.stderr.write(msg.format(error_code=code,
                                        error_message=message))
            sys.stderr.write('\n')
            return http_response.status_code - 399
        if http_response.status_code >= 400:
            msg = self.session.get_data('messages/ClientError')
            code, message = self.get_error_code_and_message(response_data)
            sys.stderr.write(msg.format(error_code=code,
                                        error_message=message))
            sys.stderr.write('\n')
            return http_response.status_code - 399

    def _display_response(self, operation, response_data):
        try:
            self.formatter(operation, response_data)
        finally:
            # flush is needed to avoid the "close failed in file object
            # destructor" in python2.x (see http://bugs.python.org/issue11380).
            sys.stdout.flush()

    def test(self, cmdline):
        """
        Useful for unit tests.  Pass in a command line as you would
        type it on the command line (e.g.):

        ``aws ec2 describe-instances --instance-id i-12345678``

        and this method will return the
        dictionary of parameters that will be passed to the operation.

        :type cmdline: str
        :param cmdline: The command line.
        """
        self.create_main_parser()
        # XXX: Does this still work with complex params that may be
        # space separated?
        status = self._parse_args(cmdline.split()[1:])
        params = {}
        self._build_call_parameters(self.operation_parser.args, params)
        return self.operation.build_parameters(**params)

    def _parse_args(self, args):
        """
        Returns -1 on error, 0 if no further action is warranted,
        and 1 if the request should be made.

        Each time one of the parsers parse() method is called, the
        parser will determine whether the user asked for help or not.
        If they did ask for help for that particular context, it will
        be generated and the process will exit.  Control flow will not
        return here after the generation of the man page.
        """
        self.main_parser.parse(args)
        if self.main_parser.args.debug:
            from six.moves import http_client
            http_client.HTTPConnection.debuglevel = 2
            self.session.set_debug_logger()
        output = self.main_parser.args.output
        if output is None:
            output = self.session.get_variable('output')
        if self.main_parser.args.profile:
            self.session.profile = self.main_parser.args.profile
        self.formatter = get_formatter(output, self.main_parser.args)
        service_name = self.main_parser.args.service_name
        self.service = self.session.get_service(service_name)
        self.create_service_parser()
        self.service_parser.parse(self.main_parser.remaining)
        operation_name = self.service_parser.args.operation
        self.operation = self.service.get_operation(operation_name)
        self.create_operation_parser()
        self.operation_parser.parse(self.service_parser.remaining)
        if self.operation_parser.remaining:
            raise ValueError('Unknown options: %s' %
                             self.operation_parser.remaining)
        return 1

    def main(self, args=None):
        """

        :param args: List of arguments, with the 'aws' removed.  For example,
            the command "aws s3 list-objects --bucket foo" will have an
            args list of ``['s3', 'list-objects', '--bucket', 'foo']``.

        """
        if args is None:
            args = sys.argv[1:]
        self.create_main_parser()
        try:
            status = self._parse_args(args)
        except ValueError as e:
            sys.stderr.write(str(e))
            sys.stderr.write('\n')
            return 255
        return self._call(self.operation_parser.args)
