import argparse
import sys
from botocore.compat import copy_kwargs
from .help import get_provider_help, get_service_help, get_operation_help


class CLIArgParser(argparse.ArgumentParser):

    Formatter = argparse.RawTextHelpFormatter

    def __init__(self, **kwargs):
        self.args = None
        self.remaining = None
        argparse.ArgumentParser.__init__(self, formatter_class=self.Formatter,
                                         add_help=False,
                                         conflict_handler='resolve',
                                         **kwargs)
        self.build()

    def build(self):
        pass

    def do_help(self):
        pass

    def parse(self, args):
        if len(args) > 0 and args[0] == 'help':
            self.do_help()
        self.args, self.remaining = self.parse_known_args(args)

    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            tup = value, '|'.join(map(repr, action.choices))
            msg = 'invalid choice: %r (choose from %s)' % tup
            raise argparse.ArgumentError(action, msg)

    def print_usage(self, fp):
        fp.write('\nPrint usage here\n')


class MainArgParser(CLIArgParser):

    def __init__(self, session, **kwargs):
        self.session = session
        self.cli_data = self.session.get_data('cli')
        CLIArgParser.__init__(self, description=self.cli_data['description'],
                              **kwargs)

    def _create_choice_help(self, choices):
        help_str = ''
        for choice in sorted(choices):
            help_str += '* %s\n' % choice
        return help_str

    def build(self):
        for option_name in self.cli_data['options']:
            option_data = copy_kwargs(self.cli_data['options'][option_name])
            if 'choices' in option_data:
                choices = option_data['choices']
                if not isinstance(choices, list):
                    provider = self.session.get_variable('provider')
                    choices_path = choices.format(provider=provider)
                    choices = self.session.get_data(choices_path)
                if isinstance(choices, dict):
                    choices = list(choices.keys())
                option_data['help'] = self._create_choice_help(choices)
                option_data['choices'] = choices + ['help']
            self.add_argument(option_name, **option_data)
        self.add_argument('--version', action="version",
                          version=self.session.user_agent())

    def do_help(self):
        """
        This will cause the interactive help to be generated in a
        subprocess.  This also will cause a sys.exit call.
        """
        get_provider_help(self.session)


class ServiceArgParser(CLIArgParser):

    def __init__(self, session, service, **kwargs):
        self.session = session
        self.service = service
        CLIArgParser.__init__(self, **kwargs)

    def do_help(self):
        """
        This will cause the interactive help to be generated in a
        subprocess.  This also will cause a sys.exit call.
        """
        get_service_help(self.session, self.service)

    def build(self):
        """
        Create the subparser to handle the Service arguments.
        """
        operations = [op.cli_name for op in self.service.operations]
        operations.append('help')
        self.add_argument('operation', help='The operation',
                          metavar='operation',
                          choices=operations)


class OperationArgParser(CLIArgParser):

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
        'blob': str}

    def __init__(self, session, service, operation, **kwargs):
        self.session = session
        self.service = service
        self.operation = operation
        CLIArgParser.__init__(self, **kwargs)

    def do_help(self):
        """
        This will cause the interactive help to be generated in a
        subprocess.  This also will cause a sys.exit call.
        """
        get_operation_help(self.session, self.service, self.operation)

    def build(self):
        for param in self.operation.params:
            if param.type == 'list':
                self.add_argument(param.cli_name,
                                  help=param.documentation,
                                  nargs='*',
                                  type=self.type_map[param.type],
                                  required=param.required,
                                  dest=param.py_name)
            elif param.type == 'boolean':
                if param.required:
                    dest = param.cli_name[2:].replace('-', '_')
                    mutex = self.add_mutually_exclusive_group(required=True)
                    mutex.add_argument(param.cli_name,
                                       help=param.documentation,
                                       dest=dest,
                                       action='store_true')
                    false_name = '--no-' + param.cli_name[2:]
                    mutex.add_argument(false_name,
                                       help=param.documentation,
                                       dest=dest,
                                       action='store_false')
                else:
                    self.add_argument(param.cli_name,
                                      help=param.documentation,
                                      action='store_true',
                                      required=param.required,
                                      dest=param.py_name)
            else:
                self.add_argument(param.cli_name,
                                  help=param.documentation,
                                  type=self.type_map[param.type],
                                  required=param.required,
                                  dest=param.py_name)
        if self.operation.is_streaming():
            self.add_argument('outfile', metavar='output_file',
                              help='Where to save the content')
