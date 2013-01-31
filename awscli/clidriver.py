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
import argparse
import sys
import os
import traceback
import json
import copy
import base64
import botocore.session
from awscli import EnvironmentVariables, __version__
from .help import get_help
from .formatter import get_formatter


def split_list(s):
    l = []
    depth = 0
    item = ''
    for c in s:
        if c == '[':
            depth += 1
            if depth > 1:
                item += c
        elif c == ']':
            if depth > 1:
                item += c
            depth -= 1
        elif c == ',':
            if depth == 1:
                l.append(item)
                item = ''
            elif depth > 1:
                item += c
        else:
            item += c
    l.append(item)
    return l


class CLIDriver(object):

    Formatter = argparse.RawTextHelpFormatter

    type_map = {
        'structure': str,
        'map': str,
        'timestamp': str,
        'list': str,
        'string': str,
        'float': float,
        'integer': str,
        'long': int,
        'boolean': bool,
        'double': float,
        'jsondoc': str,
        'file': str}

    def __init__(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.session.user_agent_name = 'aws-cli'
        self.session.user_agent_version = __version__
        self.args = None
        self.service = None
        self.region = None
        self.endpoint = None
        self.operation = None

    def create_choice_help(self, choices):
        help_str = ''
        for choice in sorted(choices):
            help_str += '* %s\n' % choice
        return help_str

    def create_main_parser(self):
        """
        Create the main parser to handle the global arguments.
        """
        self.cli_data = self.session.get_data('cli')
        description = self.cli_data['description']
        self.parser = argparse.ArgumentParser(formatter_class=self.Formatter,
                                              description=description,
                                              add_help=False,
                                              conflict_handler='resolve')
        for option_name in self.cli_data['options']:
            option_data = copy.copy(self.cli_data['options'][option_name])
            if 'choices' in option_data:
                choices = option_data['choices']
                if not isinstance(choices, list):
                    provider = self.session.get_variable('provider')
                    choices_path = choices.format(provider=provider)
                    choices = self.session.get_data(choices_path)
                if isinstance(choices, dict):
                    choices = list(choices.keys())
                option_data['help'] = self.create_choice_help(choices)
                option_data['choices'] = choices + ['help']
            self.parser.add_argument(option_name, **option_data)
        self.parser.add_argument('--version', action="version",
                                 version=self.session.user_agent())

    def create_service_parser(self, remaining):
        """
        Create the subparser to handle the Service arguments.

        :type remaining: list
        :param remaining: The list of command line parameters that were
            not recognized by upstream parsers.
        """
        if self.args.profile:
            self.session.profile = self.args.profile
        prog = '%s %s' % (self.parser.prog,
                          self.service.cli_name)
        parser = argparse.ArgumentParser(formatter_class=self.Formatter,
                                         add_help=False, prog=prog)
        operations = [op.cli_name for op in self.service.operations]
        operations.append('help')
        parser.add_argument('operation', help='The operation',
                            metavar='operation',
                            choices=operations)
        args, remaining = parser.parse_known_args(remaining)
        if args.operation == 'help':
            get_help(self.session, service=self.service, style='cli')
            sys.exit(0)
        self.operation = self.service.get_operation(args.operation)
        return self.create_operation_parser(remaining)

    def create_operation_parser(self, remaining):
        """
        Create the subparser to handle the Operation arguments.

        :type remaining: list
        :param remaining: The list of command line parameters that were
            not recognized by upstream parsers.
        """
        prog = '%s %s %s' % (self.parser.prog,
                             self.service.cli_name,
                             self.operation.cli_name)
        parser = argparse.ArgumentParser(formatter_class=self.Formatter,
                                         add_help=False, prog=prog)
        for param in self.operation.params:
            if param.type == 'list':
                parser.add_argument(param.cli_name,
                                    help=param.documentation,
                                    nargs='*',
                                    type=self.type_map[param.type],
                                    required=param.required)
            elif param.type == 'boolean':
                parser.add_argument(param.cli_name,
                                    help=param.documentation,
                                    action='store_true',
                                    required=param.required)
            else:
                parser.add_argument(param.cli_name,
                                    help=param.documentation,
                                    nargs=1,
                                    type=self.type_map[param.type],
                                    required=param.required)
        if 'help' in remaining:
            get_help(self.session, operation=self.operation, style='cli')
            sys.exit(0)
        args, remaining = parser.parse_known_args(remaining)
        if remaining:
            print('Something is wrong.  We have leftover options')
            print(remaining)
            sys.exit(-1)
        return args

    def unpack_cli_arg(self, param, s):
        """
        Parses and unpacks the encoded string command line parameter
        and returns native Python data structures that can be passed
        to the Operation.
        """
        if param.type == 'integer':
            if isinstance(s, list):
                s = s[0]
            return int(s)
        elif param.type == 'float' or param.type == 'double':
            # TODO: losing precision on double types
            if isinstance(s, list):
                s = s[0]
            return float(s)
        elif param.type == 'jsondoc':
            if isinstance(s, list) and len(s) == 1:
                s = s[0]
            if s[0] != '{':
                s = os.path.expanduser(s)
                s = os.path.expandvars(s)
                if os.path.isfile(s):
                    fp = open(s)
                    s = fp.read()
                    fp.close()
                else:
                    msg = 'JSON Document value must be JSON or path to file.'
                    raise ValueError(msg)
            return s
        elif param.type == 'file':
            if isinstance(s, list) and len(s) == 1:
                s = s[0]
            s = os.path.expanduser(s)
            s = os.path.expandvars(s)
            if os.path.isfile(s):
                fp = open(s)
                s = fp.read()
                fp.close()
            else:
                msg = 'File value must be path to file.'
                raise ValueError(msg)
            if hasattr(param, 'encoding'):
                if param.encoding == 'base64':
                    s = base64.b64encode(s)
            return s
        elif param.type == 'structure' or param.type == 'map':
            if isinstance(s, list) and len(s) == 1:
                s = s[0]
            if s[0] == '{':
                d = json.loads(s)
            elif '=' in s:
                d = dict(v.split('=', 1) for v in s.split(':'))
                for member in param.members:
                    if member.py_name in d:
                        d[member.py_name] = self.unpack_cli_arg(member,
                                                           d[member.py_name])
            else:
                s = os.path.expanduser(s)
                s = os.path.expandvars(s)
                if os.path.isfile(s):
                    fp = open(s)
                    d = json.load(fp)
                    fp.close()
                else:
                    msg = 'Structure option value must be JSON or path to file.'
                    raise ValueError(msg)
            return d
        elif param.type == 'list':
            if not isinstance(s, list):
                s = split_list(s)
            return [self.unpack_cli_arg(param.members, v) for v in s]
        else:
            if isinstance(s, list):
                s = s[0]
            return str(s)

    def build_call_parameters(self, args, param_dict):
        for param in self.operation.params:
            if hasattr(args, param.py_name):
                value = getattr(args, param.py_name)
            else:
                value = getattr(args, param.cli_name)
            if value:
                param_dict[param.py_name] = self.unpack_cli_arg(param, value)

    def display_error_and_exit(self, ex):
        if self.args.debug:
            traceback.print_exc()
        elif isinstance(ex, Exception):
            print(ex)
        elif self.args.output != 'json':
            print(ex)
        sys.exit(1)

    def get_error_code_and_message(self, response):
        code = 'Unknown'
        message = 'Unknown'
        if 'Response' in response:
            if 'Errors' in response['Response']:
                if 'Error' in response['Response']['Errors']:
                    if 'Message' in response['Response']['Errors']['Error']:
                        message = response['Response']['Errors']['Error']['Message']
                    if 'Code' in response['Response']['Errors']['Error']:
                        code = response['Response']['Errors']['Error']['Code']
        return (code, message)

    def call(self, args):
        try:
            params = {}
            self.build_call_parameters(args, params)
            self.endpoint = self.service.get_endpoint(self.args.region,
                                                      endpoint_url=self.args.endpoint_url)
            self.endpoint.verify = not self.args.no_verify_ssl
            http_response, response_data = self.operation.call(self.endpoint,
                                                               **params)
            self.formatter(self.operation, response_data)
            if http_response.status_code >= 500:
                msg = self.session.get_data('messages/ServerError')
                code, message = self.get_error_code_and_message(response_data)
                print(msg.format(error_code=code,
                                 error_message=message))
                sys.exit(http_response.status_code - 399)
            if http_response.status_code >= 400:
                msg = self.session.get_data('messages/ClientError')
                code, message = self.get_error_code_and_message(response_data)
                print(msg.format(error_code=code,
                                 error_message=message))
                sys.exit(http_response.status_code - 399)
        except Exception as ex:
            self.display_error_and_exit(ex)

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
        self.args, remaining = self.parser.parse_known_args(cmdline.split()[1:])
        self.service = self.session.get_service(self.args.service_name)
        self.formatter = get_formatter(self.args.output)
        args = self.create_service_parser(remaining)
        params = {}
        self.build_call_parameters(args, params)
        return self.operation.build_parameters(**params)

    def main(self):
        self.create_main_parser()
        self.args, remaining = self.parser.parse_known_args()
        if self.args.service_name == 'help':
            provider = self.session.get_variable('provider')
            get_help(self.session, provider=provider, style='cli')
            sys.exit(0)
        else:
            if self.args.debug:
                import httplib
                httplib.HTTPConnection.debuglevel = 2
                self.session.set_debug_logger()
            self.formatter = get_formatter(self.args.output)
            self.service = self.session.get_service(self.args.service_name)
            args = self.create_service_parser(remaining)
            self.call(args)
