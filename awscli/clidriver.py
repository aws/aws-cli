# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import botocore.base
import botocore.service
from botocore.logger import set_debug_logger
from botocore import xform_name
from .help import CLIHelp
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
        'timestamp': str,
        'list': str,
        'string': str,
        'float': float,
        'integer': int,
        'long': int,
        'boolean': bool,
        'double': float}

    def __init__(self, provider_name='aws'):
        self.provider_name = provider_name
        self.help = CLIHelp()
        self.args = None
        self.region = None
        self.service = None
        self.endpoint = None
        self.operation = None
        self.op_map = {}

    def create_op_map(self):
        if self.service:
            for op_data in self.service.operations:
                op_name = op_data['name']
                self.op_map[xform_name(op_name, '-')] = op_name

    def create_choice_help(self, choices):
        help_str = ''
        for choice in sorted(choices):
            help_str += '* %s\n' % choice
        return help_str

    def create_main_parser(self):
        """
        Create the main parser to handle the global arguments.
        """
        self.cli_data = botocore.base.get_data('cli')
        description = self.cli_data['description']
        self.parser = argparse.ArgumentParser(formatter_class=self.Formatter,
                                              description=description,
                                              add_help=False)
        for option_name in self.cli_data['options']:
            option_data = self.cli_data['options'][option_name]
            if 'choices' in option_data:
                choices = option_data['choices']
                if not isinstance(choices, list):
                    choices = botocore.base.get_data(option_data['choices'])
                if isinstance(choices, dict):
                    choices = list(choices.keys())
                option_data['help'] = self.create_choice_help(choices)
                option_data['choices'] = choices + ['help']
            self.parser.add_argument(option_name, **option_data)

    def create_service_parser(self, remaining):
        """
        Create the subparser to handle the Service arguments.

        :type remaining: list
        :param remaining: The list of command line parameters that were
            not recognized by upstream parsers.
        """
        self.endpoint = self.service.get_endpoint(self.args.region,
                                                  profile=self.args.profile,
                                                  endpoint_url=self.args.endpoint_url)
        prog = '%s %s' % (self.parser.prog,
                          self.service.short_name)
        parser = argparse.ArgumentParser(formatter_class=self.Formatter,
                                         add_help=False, prog=prog)
        operations = [op.cli_name for op in self.endpoint.operations]
        operations.append('help')
        parser.add_argument('operation', help='The operation',
                            metavar='operation',
                            choices=operations)
        args, remaining = parser.parse_known_args(remaining)
        if args.operation == 'help':
            self.help(self.endpoint)
            sys.exit(0)
        self.operation = self.endpoint.get_operation(args.operation)
        self.create_operation_parser(remaining)

    def create_operation_parser(self, remaining):
        """
        Create the subparser to handle the Operation arguments.

        :type remaining: list
        :param remaining: The list of command line parameters that were
            not recognized by upstream parsers.
        """
        prog = '%s %s %s' % (self.parser.prog,
                             self.service.short_name,
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
            print(parser.format_usage())
            self.help(self.operation)
            sys.exit(0)
        args, remaining = parser.parse_known_args(remaining)
        if remaining:
            print('Something is wrong.  We have leftover options')
            print(remaining)
            sys.exit(-1)
        else:
            self.call(args)

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
        elif param.type == 'float':
            if isinstance(s, list):
                s = s[0]
            return float(s)
        elif param.type == 'structure':
            d = dict(v.split('=', 1) for v in s.split(':'))
            for member in param.members:
                if member.py_name in d:
                    d[member.py_name] = self.unpack_cli_arg(member,
                                                       d[member.py_name])
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
        if self.args.output != 'json':
            print(ex)
        sys.exit(1)

    def call(self, args):
        try:
            params = {}
            self.build_call_parameters(args, params)
            http_response, response_data = self.operation(**params)
            self.formatter(self.operation, response_data)
            if http_response.status_code >= 500:
                raise ServiceException(None, err_code=r.error_code,
                                       err_msg=r.error_message)
            if http_response.status_code >= 400:
                raise ClientException(None, err_code=r.error_code,
                                      err_msg=r.error_message)
        except Exception, ex:
            self.display_error_and_exit(ex)

    def main(self):
        self.create_main_parser()
        self.args, remaining = self.parser.parse_known_args()
        if self.args.service_name == 'help':
            self.parser.print_help()
            sys.exit(0)
        else:
            if self.args.debug:
                set_debug_logger()
            self.formatter = get_formatter(self.args.output)
            self.service = botocore.service.get_service(self.args.service_name)
            self.create_op_map()
            self.create_service_parser(remaining)
